import typing as t
from pathlib import Path

ProjectName: t.TypeAlias = str
FileName: t.TypeAlias = str


class PackageIndex(t.Protocol):
    def list_projects(self) -> list[ProjectName]: ...

    def list_packages(self, project_name: ProjectName) -> list[FileName]: ...

    def get_package_by_file_name(self, file_name: FileName) -> Path: ...
