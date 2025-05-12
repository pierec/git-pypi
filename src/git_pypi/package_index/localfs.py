import typing as t
from collections import defaultdict
from pathlib import Path

import typing_extensions as tt

from git_pypi.config import DEFAULT_CONFIG, Config
from git_pypi.exc import PackageNotFoundError

from .base import FileName, PackageIndex, ProjectName


class LocalFSPackageIndex(PackageIndex):
    def __init__(self, dir_path: Path) -> None:
        self._dir_path = dir_path
        self._ignore_prefixes = (".", "_")

    @classmethod
    def from_config(
        cls,
        config: Config = DEFAULT_CONFIG,
    ) -> tt.Self:
        if not config.local_packages_dir_path:
            raise ValueError(
                f"local_packages_dir_path: invalid value"
                f" ({config.local_packages_dir_path!r})"
            )

        return cls(config.local_packages_dir_path)

    def list_projects(self) -> list[ProjectName]:
        return sorted(self._list_package_paths_by_project().keys())

    def list_packages(self, project_name: ProjectName) -> list[FileName]:
        return sorted(
            FileName(p.name)
            for p in self._list_package_paths_by_project().get(project_name, [])
        )

    def get_package_by_file_name(self, file_name: FileName) -> Path:
        for path in self._list_package_paths():
            if FileName(path.name) == file_name:
                return path

        raise PackageNotFoundError(file_name)

    def _list_package_paths_by_project(self) -> t.Mapping[ProjectName, list[Path]]:
        def _extract_project_name(path: Path) -> str:
            return path.name.split("-", maxsplit=1)[0].replace("_", "-")

        packages_by_project: dict[ProjectName, list[Path]] = defaultdict(list)

        for path in self._list_package_paths():
            packages_by_project[_extract_project_name(path)].append(path)

        return dict(packages_by_project)

    def _list_package_paths(self) -> t.Iterator[Path]:
        if not self._dir_path.exists():
            return iter([])

        return (
            path
            for path in self._dir_path.iterdir()
            if not path.name.startswith(self._ignore_prefixes)
        )
