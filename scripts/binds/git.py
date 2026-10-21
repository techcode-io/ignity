from scripts.binds import Bind, CommandNotFound
from scripts.utils import fatal


class Git(Bind):
    """Represents a bind to git command."""

    def __init__(self) -> None:
        """Init git bind."""
        try:
            super().__init__("git")
        except CommandNotFound as err:
            fatal("detect git binary", err)

    def checkout_new_branch(self, name: str) -> None:
        """Create and switch to a new branch."""
        self._exec("checkout", "-b", name)

    def add_all(self) -> None:
        """Stage all changes."""
        self._exec("add", "--all")

    def commit(self, message: str, no_verify: bool = False) -> None:
        """Commit staged changes."""
        args = ["commit", "-m", message]
        if no_verify:
            args.append("--no-verify")
        self._exec(*args)

    def push(self, remote: str, ref: str) -> None:
        """Push a ref to a remote."""
        self._exec("push", remote, ref)

    def tag(self, name: str) -> None:
        """
        Create a tag.

        Raises:
            ErrorReturnCode: if the tag already exists.
        """
        self._exec("tag", name)
