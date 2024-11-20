import logging
import typing as t
from pathlib import Path

import git
import typing_extensions as tt

from .config import DEFAULT_CONFIG, Config
from .exc import GitError
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
        dir_path: Path | str,
        parse_tag: TagParser = default_tag_parser,
    ) -> None:
        self._parse_tag = parse_tag
        self._repo = git.Repo(dir_path)

    @classmethod
    def from_config(cls, config: Config = DEFAULT_CONFIG) -> tt.Self:
        return cls(dir_path=config.repo_dir_path)

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
