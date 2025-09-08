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


class GitCmd:
    def __init__(self, dir_path: Path | str) -> None:
        self.dir_path = Path(dir_path)
        self._git_cmd = Cmd("git")

    def clone_bare(self, remote_uri: str) -> None:
        try:
            self._git_cmd.run(
                "clone",
                "--bare",
                remote_uri,
                str(self.dir_path),
            )
        except CmdError as e:
            raise GitError(str(e)) from e

    def fetch(self, timeout: float | None = None) -> None:
        try:
            self._git_cmd.run(
                *self._path_args(),
                "fetch",
                "--tags",
                timeout=timeout,
            )
        except CmdError as e:
            raise GitError(str(e)) from e

    def get_remote_uri(self, name: str = "origin") -> str | None:
        try:
            cp = self._git_cmd.run(
                *self._path_args(),
                "remote",
                "get-url",
                name,
            )
        except CmdError as e:
            raise GitError(str(e)) from e

        uri = cp.stdout.splitlines()[0].strip()
        return uri.decode()

    def list_tags(self) -> list[TagReference]:
        try:
            cp = self._git_cmd.run(
                *self._path_args(),
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
                *self._path_args(),
                "worktree",
                "add",
                "-f",
                str(path),
                ref,
            )
            self._git_cmd.run(
                "-C",
                str(path),
                "submodule",
                "update",
                "--init",
                "--recursive",
            )
        except CmdError as e:
            raise GitError(str(e)) from e

    def worktree_rm(self, path: Path) -> None:
        try:
            self._git_cmd.run(
                *self._path_args(),
                "worktree",
                "remove",
                "-f",
                str(path),
            )
        except CmdError as e:
            raise GitError(str(e)) from e

    def _path_args(self) -> tuple[str, ...]:
        return ("-C", str(self.dir_path))


class GitRepository:
    def __init__(
        self,
        dir_path: Path | str,
        parse_tag: TagParser = default_tag_parser,
        fetch_fresh_period: float = 60,
    ) -> None:
        self._parse_tag = parse_tag
        self._cmd = GitCmd(dir_path)

        self._fetch_fresh_period = fetch_fresh_period
        self._last_fetch_ts: float = 0
        self._fetch_lock = threading.Lock()

    @classmethod
    def from_local_dir(cls, dir_path: Path | str) -> tt.Self:
        return cls(dir_path)

    @classmethod
    def from_remote(cls, dir_path: Path | str, remote_uri: str) -> tt.Self:
        dir_path = Path(dir_path)

        if dir_path.exists():
            try:
                cmd = GitCmd(dir_path)
                if cmd.get_remote_uri() == remote_uri:
                    return cls(dir_path)
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
                "Path exists with a different remote URI. Changed git clone path: '%s' -> '%s'",
                old_dir_path,
                dir_path,
            )

        logger.info("Cloning '%s' -> '%s'", remote_uri, dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        cmd = GitCmd(dir_path)
        cmd.clone_bare(remote_uri)

        return cls(dir_path)

    @staticmethod
    def _get_suffixed_path(path: Path) -> Path:
        for i in range(1000):
            suffixed_path = path.with_suffix(f".{i:04}")
            if not suffixed_path.exists():
                return suffixed_path

        raise GitPackageIndexError(f"Failed to find and alternative path for '{path}'.")

    def list_packages(self) -> t.Iterator[GitPackageInfo]:
        tags = self._cmd.list_tags()

        for tag in tags:
            if package_info := self._parse_tag(tag):
                yield package_info

    def fetch(self, timeout: float | None = None) -> None:
        with self._fetch_lock:
            if time.monotonic() - self._last_fetch_ts > self._fetch_fresh_period:
                try:
                    self._cmd.fetch(timeout=timeout)
                finally:
                    self._last_fetch_ts = time.monotonic()

    @contextlib.contextmanager
    def checkout(
        self,
        package: GitPackageInfo,
        dst_dir: Path | str,
    ) -> t.Generator[None, None, None]:
        logger.info("Checking out package=%r to dst_dir=%r", package, dst_dir)

        dst_dir = Path(dst_dir)
        self._cmd.worktree_add(ref=package.tag_sha1, path=dst_dir)

        yield

        self._cmd.worktree_rm(path=dst_dir)
