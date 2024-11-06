from dataclasses import dataclass
from functools import cached_property
from pathlib import Path


@dataclass
class GitPackageInfo:
    name: str
    version: str
    path: Path
    tag_ref: str
    tag_sha1: str

    @cached_property
    def sdist_file_name(self) -> str:
        return f"{self.name.replace('-', '_')}-{self.version}.tar.gz"

    @cached_property
    def project_name(self) -> str:
        return self.name

    @cached_property
    def unique_key(self) -> str:
        return f"{self.name}:{self.tag_sha1}"
