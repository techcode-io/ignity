from scripts.binds.container import Container


class Nfpm(Container):
    """Represents a bind to the `goreleaser/nfpm` packaging container."""

    def package(self, config: str, target: str, packager: str) -> None:
        """Package a build bundle into an OS package using nfpm."""
        self._exec(
            "run",
            "--rm",
            "-v",
            ".:/tmp",
            "-w",
            "/tmp",
            "goreleaser/nfpm",
            "package",
            "--config",
            config,
            "--target",
            target,
            "--packager",
            packager,
        )
