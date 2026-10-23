from collections.abc import Mapping

from scripts.binds.container import Container


class Nfpm(Container):
    """Represents a bind to the `goreleaser/nfpm` packaging container."""

    def package(
        self, config: str, target: str, packager: str, env: Mapping[str, str]
    ) -> None:
        """Package a build bundle into an OS package using nfpm."""
        # Expanded by nfpm in the config
        env_args = [arg for key, value in env.items() for arg in ("-e", f"{key}={value}")]
        self._exec(
            "run",
            "--rm",
            "-v",
            ".:/tmp",
            "-w",
            "/tmp",
            *env_args,
            "goreleaser/nfpm",
            "package",
            "--config",
            config,
            "--target",
            target,
            "--packager",
            packager,
        )
