import os
import re
import sys
import tomllib
from pathlib import Path
from typing import Final

from scripts.binds import ErrorReturnCode
from scripts.binds.gh import Gh
from scripts.binds.git import Git

PYPROJECT_PATH: Final[Path] = Path("pyproject.toml")
DISTRIBUTIONS_NFPM_AMD64_PATH: Final[Path] = Path(
    "distributions/packages/nfpm.amd64.yaml"
)
DISTRIBUTIONS_NFPM_ARM64_PATH: Final[Path] = Path(
    "distributions/packages/nfpm.arm64.yaml"
)
# Packages built for the release: deb, rpm and apk
RELEASE_ASSETS_PATTERNS: Final[tuple[str, ...]] = (
    "ignity*.deb",
    "ignity*.rpm",
    "ignity*.apk",
)


def __update_file_version(file_path: Path, pattern: str, replacement: str) -> None:
    """Substitute the version in a file matching a regex pattern."""
    try:
        data = file_path.read_text()
    except Exception:
        print(
            f"The `{file_path.as_posix()}` can't be read",
            file=sys.stderr,
        )
        raise

    data = re.sub(pattern, replacement, data, count=1)
    try:
        file_path.write_text(data)
    except Exception:
        print(
            f"The `{file_path.as_posix()}` file can't be written",
            file=sys.stderr,
        )
        raise


def __set_version(version: str) -> None:
    """Update version in pyproject.toml and the nfpm package configs."""
    # Update project version
    __update_file_version(
        PYPROJECT_PATH, r"version = \"(.+)\"", f'version = "{version}"'
    )

    # Update nfpm package versions
    __update_file_version(
        DISTRIBUTIONS_NFPM_AMD64_PATH, r"version: \"(.+)\"", f'version: "{version}"'
    )
    __update_file_version(
        DISTRIBUTIONS_NFPM_ARM64_PATH, r"version: \"(.+)\"", f'version: "{version}"'
    )


def __project_version() -> str:
    """Return the project version from pyproject.toml."""
    with PYPROJECT_PATH.open("rb") as file:
        return tomllib.load(file)["project"]["version"]


def pre() -> None:
    """Create a release branch and PR to prepare for release."""
    # Ensure we have inputs
    release_version = os.getenv("RELEASE_VERSION")
    if not release_version:
        return print(
            "You must define `RELEASE_VERSION` environment variable.", file=sys.stderr
        )
    if not re.fullmatch(r"(\d){1,2}\.(\d){1,2}\.(\d){1,2}", release_version):
        return print(
            "The `RELEASE_VERSION` should match semver format.", file=sys.stderr
        )

    # Create a new branch
    branch_name = f"feat/pre-release-v{release_version}"
    git = Git()
    git.checkout_new_branch(branch_name)

    # Update all files
    __set_version(release_version)

    # Push release branch
    git.add_all()
    git.commit(f"chore: release ignity v{release_version}", no_verify=True)
    git.push("origin", branch_name)

    # Create a PR
    Gh().pr_create(base="main", head=branch_name)


def run() -> None:
    """Create a release tag and GitHub release with the built packages."""
    # Read project version
    release_version = __project_version()
    if release_version.endswith("-dev"):
        return print(
            f"The `{release_version}` development version can't be released.",
            file=sys.stderr,
        )

    # Create the release tag
    try:
        git = Git()
        git.tag(release_version)
        git.push("origin", release_version)
    except ErrorReturnCode:
        return print(
            f"The release `v{release_version}` already exists.", file=sys.stderr
        )

    # Create the release
    assets = sorted(
        file.absolute().as_posix()
        for pattern in RELEASE_ASSETS_PATTERNS
        for file in Path("dist").glob(pattern)
        if file.is_file()
    )
    Gh().release_create(release_version, f"ignity v{release_version}", assets)


def post() -> None:
    """Prepare for the next development iteration after release."""
    # Ensure we have inputs
    next_version = os.getenv("NEXT_VERSION")
    if not next_version:
        return print(
            "You must define `NEXT_VERSION` environment variable", file=sys.stderr
        )
    if not re.fullmatch(r"(\d){1,2}\.(\d){1,2}\.(\d){1,2}-dev", next_version):
        return print("The `NEXT_VERSION` should match semver format.", file=sys.stderr)

    # Create a new branch
    branch_name = f"feat/post-release-v{next_version}"
    git = Git()
    git.checkout_new_branch(branch_name)

    # Update all files
    __set_version(next_version)

    # Push changes
    git.add_all()
    git.commit("chore: prepare for next iteration", no_verify=True)
    git.push("origin", branch_name)

    # Create a PR
    Gh().pr_create(base="main", head=branch_name)
