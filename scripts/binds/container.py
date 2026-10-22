from collections.abc import Mapping
from pathlib import Path
from typing import override

from scripts.binds import Bind, CommandNotFound
from scripts.utils import fatal


class Container(Bind):
    """Represents a bind to a container backend, either docker or podman."""

    def __init__(self) -> None:
        """Init container bind."""
        backend: str | None = None
        for candidate in ("docker", "podman"):
            try:
                super().__init__(candidate)
                backend = candidate
                break
            except CommandNotFound:
                continue

        if backend is None:
            fatal(
                "detect container backend",
                CommandNotFound("docker or podman"),
            )

        self.__backend: str = backend

    @override
    def _env(self) -> Mapping[str, str]:
        env = dict(super()._env())
        if self.__backend == "podman":
            env["BUILDAH_FORMAT"] = "docker"
        return env

    def build(self, tag: str, containerfile: Path, context: Path) -> None:
        """Build an image from a containerfile."""
        self._exec("build", "-t", tag, "-f", containerfile.as_posix(), context.as_posix())

    def create(self, image: str) -> str:
        """Create a container from an image without starting it, and return its id."""
        # The command is never run, it is only required for images without one
        return self._exec("create", image, "noop", capture=True)

    def cp(self, src: str, dst: str) -> None:
        """Copy files between a container and the host."""
        self._exec("cp", src, dst)

    def rm(self, container: str) -> None:
        """Remove a container."""
        self._exec("rm", "-f", container, capture=True)

    def rmi(self, image: str) -> None:
        """Remove an image."""
        self._exec("rmi", "-f", image, capture=True)
