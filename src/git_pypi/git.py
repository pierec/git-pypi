import logging
import typing as t
from pathlib import Path

import git
import typing_extensions as tt

from .exc import GitError, GitPackageIndexError
from .types import GitPackageInfo

logger = logging.getLogger(__name__)


class TagParser(t.Protocol):
    def __call__(self, tag: git.refs.tag.TagReference) -> GitPackageInfo | None: ...


def default_tag_parser(tag: git.refs.tag.TagReference) -> GitPackageInfo | None:
    name, _, version = tag.path.removeprefix("refs/tags/").partition("/v")

    if not name or not version:
        return None

    return GitPackageInfo(
        name=name,
        version=version,
        path=Path(name),
        tag_ref=tag.path,
        tag_sha1=str(tag.commit),
    )


class GitRepository:
    def __init__(
        self,
        repo: git.Repo,
        parse_tag: TagParser = default_tag_parser,
    ) -> None:
        self._parse_tag = parse_tag
        self._repo = repo

    @classmethod
    def from_local_dir(cls, dir_path: Path | str) -> tt.Self:
        repo = git.Repo(dir_path)
        return cls(repo)

    @classmethod
    def from_remote(cls, dir_path: Path | str, remote: str) -> tt.Self:
        dir_path = Path(dir_path)

        if dir_path.exists():
            try:
                repo = git.Repo(dir_path)
                if repo.remote().url == remote:
                    return cls(repo)
            except git.exc.GitError as e:
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
        repo = git.Repo.clone_from(remote, to_path=str(dir_path))
        return cls(repo)

    @staticmethod
    def _get_suffixed_path(path: Path) -> Path:
        for i in range(1000):
            suffixed_path = path.with_suffix(f".{i:04}")
            if not suffixed_path.exists():
                return suffixed_path

        raise GitPackageIndexError(f"Failed to find and alternative path for '{path}.")

    def list_packages(self) -> t.Iterator[GitPackageInfo]:
        try:
            tags = git.refs.tag.TagReference.iter_items(self._repo)
        except git.exc.GitError as e:
            raise GitError(str(e)) from e

        for tag in tags:
            if package_info := self._parse_tag(tag):
                yield package_info

    def checkout(
        self,
        package: GitPackageInfo,
        dst_dir: Path | str,
        extra_checkout_paths: t.Sequence[Path | str] | None = None,
    ) -> None:
        logger.info("Checking out package=%r to dst_dir=%r", package, dst_dir)

        dst_dir = Path(dst_dir)

        try:
            commit = self._repo.commit(package.tag_sha1)
            package_trees = [commit.tree / str(package.path)]
            if extra_checkout_paths:
                package_trees.extend(commit.tree / str(p) for p in extra_checkout_paths)
        except (git.exc.GitError, KeyError) as e:
            raise GitError(str(e)) from e

        for package_tree in package_trees:
            for obj in package_tree.traverse():
                if not isinstance(obj, git.objects.blob.Blob):
                    continue

                obj_path = dst_dir / obj.path
                obj_path.parent.mkdir(exist_ok=True, parents=True)

                logger.debug("Checking out: %r -> %r", obj, obj_path)

                with obj_path.open("wb") as f:
                    obj.stream_data(f)

                obj_path.chmod(obj.mode)
