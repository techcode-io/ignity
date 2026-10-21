import os
import shutil
import subprocess
from collections.abc import Mapping

# A command exited with a non-zero code
ErrorReturnCode = subprocess.CalledProcessError


class CommandNotFound(Exception):
    """Raised when a command can't be found in PATH."""

    def __init__(self, name: str) -> None:
        super().__init__(f"The `{name}` command can't be found in PATH")


class Bind:
    """Represents a bind to a command found in PATH."""

    def __init__(self, name: str) -> None:
        """Init bind, raising CommandNotFound when the command isn't in PATH."""
        path = shutil.which(name)
        if path is None:
            raise CommandNotFound(name)
        self._path: str = path

    def _env(self) -> Mapping[str, str]:
        """Environment the command runs with."""
        return os.environ

    def _exec(self, *args: str, capture: bool = False) -> str:
        """
        Run the command with arguments, inheriting stderr and, unless captured, stdout.

        Raises:
            ErrorReturnCode: if the command exits with a non-zero code.
        """
        result = subprocess.run(
            [self._path, *args],
            check=True,
            env=self._env(),
            stdout=subprocess.PIPE if capture else None,
            text=True,
        )
        return (result.stdout or "").strip()
