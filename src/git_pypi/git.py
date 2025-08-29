import contextlib
import logging
import threading
import time
import typing as t
from pathlib import Path

import typing_extensions as tt

from git_pypi.cmd import Cmd
from git_pypi.exc import CmdError, GitError, GitPackageIndexError
from git_pypi.types import GitPackageInfo

logger = logging.getLogger(__name__)


class TagReference(t.NamedTuple):
    sha1: str
    name: str


class TagParser(t.Protocol):
    def __call__(self, tag: TagReference) -> GitPackageInfo | None: ...


def default_tag_parser(tag: TagReference) -> GitPackageInfo | None:
    name, _, version = tag.name.removeprefix("refs/tags/").partition("/v")

    if not name or not version:
        return None

    return GitPackageInfo(
        name=name,
        version=version,
        path=Path(name),
        tag_ref=tag.name,
        tag_sha1=tag.sha1,
    )


class GitRepo:
    def __init__(self, git_dir_path: Path | str) -> None:
        self.git_dir_path = Path(git_dir_path)
        self._git_cmd = Cmd("git")

    def clone(self, remote_uri: str) -> None:
        try:
            self._git_cmd.run("clone", "--bare", remote_uri, f"{self.git_dir_path}")
        except CmdError as e:
            raise GitError(str(e)) from e

    def fetch(self) -> None:
        try:
            self._git_cmd.run("--git-dir", f"{self.git_dir_path}", "fetch", "--tags")
        except CmdError as e:
            raise GitError(str(e)) from e

    def remote_uri(self, name: str = "origin") -> str | None:
        try:
            cp = self._git_cmd.run(
                "--git-dir", f"{self.git_dir_path}", "remote", "get-url", name
            )
        except CmdError as e:
            raise GitError(str(e)) from e

        uri = cp.stdout.splitlines()[0].strip()
        return uri.decode()

    def list_tags(self) -> list[TagReference]:
        try:
            cp = self._git_cmd.run(
                "--git-dir",
                f"{self.git_dir_path}",
                "show-ref",
                "--tag",
                expected_returncode={0, 1},
            )
        except CmdError as e:
            raise GitError(str(e)) from e

        tags: list[TagReference] = []
        for ln in cp.stdout.splitlines():
            sha1, name, *_ = ln.strip().decode().split()
            tags.append(TagReference(sha1, name))

        return tags

    def worktree_add(self, ref: str, path: Path) -> None:
        try:
            self._git_cmd.run(
                "--git-dir",
                f"{self.git_dir_path}",
                "worktree",
                "add",
                "-f",
                f"{path}",
                ref,
            )
            self._git_cmd.run(
                "submodule",
                "update",
                "--init",
                "--recursive",
                cwd=path,
            )
        except CmdError as e:
            raise GitError(str(e)) from e

    def worktree_rm(self, path: Path) -> None:
        try:
            self._git_cmd.run(
                "--git-dir",
                f"{self.git_dir_path}",
                "worktree",
                "remove",
                "-f",
                f"{path}",
            )
        except CmdError as e:
            raise GitError(str(e)) from e


class GitRepository:
    def __init__(
        self,
        repo: GitRepo,
        parse_tag: TagParser = default_tag_parser,
        fetch_fresh_period: float = 60,
    ) -> None:
        self._parse_tag = parse_tag
        self._repo = repo

        self._fetch_fresh_period = fetch_fresh_period
        self._last_fetch_ts: float = 0
        self._fetch_lock = threading.Lock()

    @classmethod
    def from_local_dir(cls, dir_path: Path | str) -> tt.Self:
        repo = GitRepo(Path(dir_path) / ".git")
        return cls(repo)

    @classmethod
    def from_remote(cls, dir_path: Path | str, remote_uri: str) -> tt.Self:
        dir_path = Path(dir_path)

        if dir_path.exists():
            try:
                repo = GitRepo(dir_path)
                if repo.remote_uri() == remote_uri:
                    return cls(repo)
            except GitError as e:
                logger.warning(
                    "Error when checking for existing repo at '%s': %r",
                    dir_path,
                    e,
                    exc_info=True,
                )

            old_dir_path = dir_path
            dir_path = cls._get_suffixed_path(dir_path)
            logger.warning(
                f"Changed git clone path: '{old_dir_path}' -> '{dir_path}'",
            )

        dir_path.mkdir(parents=True, exist_ok=True)
        repo = GitRepo(dir_path)
        repo.clone(remote_uri)
        return cls(repo)

    @staticmethod
    def _get_suffixed_path(path: Path) -> Path:
        for i in range(1000):
            suffixed_path = path.with_suffix(f".{i:04}")
            if not suffixed_path.exists():
                return suffixed_path

        raise GitPackageIndexError(f"Failed to find and alternative path for '{path}.")

    def list_packages(self) -> t.Iterator[GitPackageInfo]:
        tags = self._repo.list_tags()

        for tag in tags:
            if package_info := self._parse_tag(tag):
                yield package_info

    def fetch(self) -> None:
        with self._fetch_lock:
            if time.monotonic() - self._last_fetch_ts > self._fetch_fresh_period:
                self._repo.fetch()
                self._last_fetch_ts = time.monotonic()

    @contextlib.contextmanager
    def checkout(
        self,
        package: GitPackageInfo,
        dst_dir: Path | str,
    ) -> t.Generator[None, None, None]:
        logger.info("Checking out package=%r to dst_dir=%r", package, dst_dir)

        dst_dir = Path(dst_dir)
        self._repo.worktree_add(ref=package.tag_sha1, path=dst_dir)

        yield

        self._repo.worktree_rm(path=dst_dir)
