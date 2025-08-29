import logging
import pathlib
import subprocess

from git_pypi.exc import CmdError

logger = logging.getLogger(__name__)


class Cmd:
    def __init__(self, *args: str) -> None:
        self._args: tuple[str, ...] = args

    def __str__(self) -> str:
        return f"{self.__class__.__name__}{self._args}"

    def __repr__(self) -> str:
        return str(self)

    def run(
        self,
        *args: str,
        expected_returncode: set[int] | None = None,
        cwd: pathlib.Path | None = None,
    ) -> subprocess.CompletedProcess:
        expected_returncode = expected_returncode or {0}
        args = (*self._args, *args)

        if not args:
            raise CmdError("Empty argument list.")

        logger.debug("Running %r", args)

        cp = subprocess.run(  # noqa: S603
            args,
            capture_output=True,
            check=False,
            cwd=cwd,
        )

        if cp.returncode not in expected_returncode:
            logger.error("Error calling %r, code=%r", cp.args, cp.returncode)
            for ln in cp.stdout.splitlines():
                logger.error(" OUT> %s", ln.decode())

            for ln in cp.stderr.splitlines():
                logger.error(" ERR> %s", ln.decode())

            raise CmdError(f"Error calling {cp.args!r}, code={cp.returncode}")

        for ln in cp.stdout.splitlines():
            logger.debug(" OUT> %s", ln.decode())

        for ln in cp.stderr.splitlines():
            logger.debug(" ERR> %s", ln.decode())

        return cp
