from scripts.binds import Bind, CommandNotFound
from scripts.utils import fatal


class Gh(Bind):
    """Represents a bind to gh command."""

    def __init__(self) -> None:
        """Init gh bind."""
        try:
            super().__init__("gh")
        except CommandNotFound as err:
            fatal("detect gh binary", err)

    def pr_create(self, base: str, head: str) -> None:
        """Create a pull request, filling title/body from commits."""
        self._exec("pr", "create", "--fill", f"--base={base}", f"--head={head}")

    def release_create(self, version: str, title: str, assets: list[str]) -> None:
        """Create a release with generated notes and attached assets."""
        self._exec(
            "release",
            "create",
            "--generate-notes",
            "--latest",
            f"--title={title}",
            version,
            *assets,
        )
