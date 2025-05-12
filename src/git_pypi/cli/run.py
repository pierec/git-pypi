import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

import cattrs

import git_pypi.__about__
from git_pypi.builder import LocalFSPackageCache
from git_pypi.config import Config
from git_pypi.web.app import create_app
from git_pypi.web.server import Server

logger = logging.getLogger("git_pypi")


@dataclass
class Args:
    git_repo: Path | None
    config: Path | None
    debug: bool
    clear_cache: bool
    host: str | None
    port: int | None
    version: bool


def parse_args(argv: list[str] | None = None) -> Args:
    parser = argparse.ArgumentParser(description="Run the git-pypi server.")
    parser.add_argument(
        "--git-repo",
        "-r",
        type=Path,
        help="Git repository path.",
    )
    parser.add_argument(
        "--host",
        "-H",
        help="Server host",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        help="Server port",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        help="Config file path.",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear the package cache prior to starting.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and exit.",
    )
    args = parser.parse_args(argv)
    return cattrs.structure(vars(args), Args)


def read_config(args: Args):
    if args.config:
        config = Config.from_file(args.config)
    else:
        config = Config.default()

    if args.host:
        config.server.host = args.host

    if args.port:
        config.server.port = args.port

    if args.git_repo:
        config.repo_dir_path = args.git_repo

    return config


def setup_logging(args: Args):
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
        datefmt="[%Y-%m-%d %H:%M:%S %z]",
    )


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if args.version:
        print(git_pypi.__about__.__version__)  # noqa: T201
        return

    config = read_config(args)
    setup_logging(args)

    server = Server(
        create_app(config),
        {
            "bind": config.server.addr,
            "workers": 1,
            "threads": config.server.threads,
            "timeout": config.server.timeout,
            "accesslog": "-",
        },
    )

    if args.clear_cache:
        logger.info("Clearing cache...")
        LocalFSPackageCache.from_config(config).clear()

    logger.info(
        "Running server... use http://%s/simple as the index URL.",
        config.server.addr,
    )

    server.run()
