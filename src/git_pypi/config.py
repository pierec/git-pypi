import typing as t
from dataclasses import dataclass, field
from pathlib import Path

import cattrs
import tomli
import typing_extensions as tt

DEFAULT_CONFIG_PATH = Path("~/.git-pypi/config.toml").expanduser()
_CONVERTER = cattrs.Converter(forbid_extra_keys=True)


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 60100
    threads: int = 4
    timeout: int = 300

    @property
    def addr(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass
class Config:
    repo_dir_path: Path = field(default_factory=Path.cwd)
    package_artifacts_dir_path: Path = Path("dist")
    cached_artifacts_dir_path: Path = Path("~/.git-pypi/cache/artifacts")
    build_command: tuple[str, ...] = ("make", "build")
    extra_checkout_paths: tuple[Path, ...] = ()
    fallback_index_url: str = "https://pypi.python.org/simple"
    server: ServerConfig = field(default_factory=ServerConfig)

    def __post_init__(self):
        self.repo_dir_path = self.repo_dir_path.expanduser()
        self.cached_artifacts_dir_path = self.cached_artifacts_dir_path.expanduser()
        if self.fallback_index_url:
            self.fallback_index_url = self.fallback_index_url.rstrip("/")

    @classmethod
    def default(cls) -> tt.Self:
        return cls()

    @classmethod
    def from_file(cls, file_path: Path) -> tt.Self:
        with file_path.open("rb") as f:
            data = tomli.load(f)
        return _CONVERTER.structure(
            {k.replace("-", "_"): v for k, v in data.items()},
            cls,
        )


DEFAULT_CONFIG = Config.default()


EXAMPLE_CONFIG = """
package-artifacts-dir-path = "dist"
cached-artifacts-dir-path = "~/.git-pypi/cache/artifacts"
build-command = ["make", "build"]
fallback-index-url = "https://pypi.python.org/simple"

[server]
host = "127.0.0.1"
port = 60100
threads = 4
timeout = 300
"""


def write_example_config(fd: t.TextIO) -> None:
    fd.write(EXAMPLE_CONFIG.strip())
