import typing as t
from dataclasses import dataclass, field
from pathlib import Path

import cattrs
import tomli
import typing_extensions as tt

from git_pypi.exc import ConfigError

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


@dataclass(kw_only=True)
class GitRepositoryConfig:
    type: t.Literal["git"] = "git"

    dir_path: Path
    remote_uri: str | None = None

    package_artifacts_dir_path: Path = Path("dist")
    build_command: tuple[str, ...] = ("make", "build")

    def __post_init__(self):
        self.dir_path = self.dir_path.expanduser()

        if not self.build_command:
            raise ConfigError("`build-command` cannot be empty")


@dataclass(kw_only=True)
class PackageDirRepositoryConfig:
    type: t.Literal["package-dir"] = "package-dir"

    dir_path: Path

    def __post_init__(self):
        self.dir_path = self.dir_path.expanduser()


@dataclass
class Config:
    MIN_SUPPORTED_VERSION: t.ClassVar[int] = 1

    version: int = 0
    cached_artifacts_dir_path: Path = Path("~/.git-pypi/cache/artifacts")
    fallback_index_url: str | None = "https://pypi.python.org/simple"
    server: ServerConfig = field(default_factory=ServerConfig)
    repositories: dict[
        str,
        GitRepositoryConfig | PackageDirRepositoryConfig,
    ] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.cached_artifacts_dir_path = self.cached_artifacts_dir_path.expanduser()

        if self.fallback_index_url is not None:
            self.fallback_index_url = self.fallback_index_url.rstrip("/")

    @classmethod
    def from_file(cls, file_path: Path) -> tt.Self:
        try:
            with file_path.open("rb") as f:
                config_dict = tomli.load(f)
            config = cls.from_dict(config_dict)
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"Error loading '{file_path}': {e!r}") from e

        return config

    @classmethod
    def from_dict(cls, config_dict: t.Mapping[str, t.Any]) -> tt.Self:
        try:
            config_dict = cls._unkebab(config_dict)
            config = _CONVERTER.structure(config_dict, cls)
        except Exception as e:
            if config_dict.get("version", 0) < cls.MIN_SUPPORTED_VERSION:
                raise ConfigError(
                    f"Minimum supported config file version is {cls.MIN_SUPPORTED_VERSION}."
                    f" Please update your config."
                ) from e
            raise

        return config

    @classmethod
    def _unkebab(cls, obj: t.Any) -> t.Any:
        if isinstance(obj, dict):
            obj = {k.replace("-", "_"): v for k, v in obj.items()}
            for k, v in obj.items():
                obj[k] = cls._unkebab(v)

        elif isinstance(obj, list):
            obj = [cls._unkebab(o) for o in obj]

        return obj


EXAMPLE_CONFIG = """
version = 1

fallback-index-url = "https://pypi.python.org/simple"
cached-artifacts-dir-path = "~/.git-pypi/cache/artifacts"

[server]
host = "127.0.0.1"
port = 60100
threads = 4
timeout = 300

# Example of a local git repository. It is expected that the repository is
# already cloned to `dir-path`.
# [repositories.local]
# type = "git"
# dir-path = "~/.git-pypi/repositories/foo"
# build-command = ["make", "build"]

# Example of a remote git repository. This repository will be cloned on server
# start if not present in `dir-path`.
# [repositories.remote]
# type = "git"
# remote-uri = "git@github.com:pierec/bar.git"
# dir-path = "~/.git-pypi/repositories/bar"
# build-command = ["make", "build"]

# Example of a repository that's a flat directory containing Python packages:
# [repositories.vendored]
# type = "package-dir"
# dir-path = "~/.git-pypi/repositories/vendored"
"""


def write_example_config(fd: t.TextIO) -> None:
    fd.write(EXAMPLE_CONFIG.strip())
