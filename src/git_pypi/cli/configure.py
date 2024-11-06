import argparse
from dataclasses import dataclass
from pathlib import Path

import cattrs

from git_pypi.config import DEFAULT_CONFIG_PATH, write_example_config


@dataclass
class Args:
    config: Path
    force: bool


def parse_args(argv: list[str] | None = None) -> Args:
    parser = argparse.ArgumentParser(
        description="Generate a default git-pypi configuration file."
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        help="Config file path.",
        default=DEFAULT_CONFIG_PATH,
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite existing file.",
    )
    args = parser.parse_args(argv)
    return cattrs.structure(vars(args), Args)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.config.exists() and not args.force:
        print(f"Config file already exists at {args.config}, aborting")  # noqa: T201
        return 1

    args.config.parent.mkdir(exist_ok=True, parents=True)
    with args.config.open("w") as f:
        write_example_config(f)

    print(f"Config file written to {args.config}")  # noqa: T201
    return 0
