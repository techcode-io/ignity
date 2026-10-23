import platform
import tomllib
from pathlib import Path

from scripts.binds.nfpm import Nfpm

DISTRIBUTIONS_PACKAGES_PATH = "distributions/packages"
# ignity-core, and ignity-utils providing ignity-utils-impl (like ignity-utils-rs)
PACKAGES = ("core", "utils")
PYPROJECT_PATH = Path("pyproject.toml")


def __build_package(packager: str) -> None:
    """Package the current architecture bundle with nfpm, one package per PACKAGES."""
    arch = platform.machine().lower()
    arch = "amd64" if arch == "x86_64" else arch
    arch = "arm64" if arch == "aarch64" else arch

    # Same name for every format, so that a Dockerfile can pick one from TARGETARCH
    with PYPROJECT_PATH.open("rb") as file:
        version = tomllib.load(file)["project"]["version"]

    nfpm = Nfpm()
    for package in PACKAGES:
        nfpm.package(
            config=f"{DISTRIBUTIONS_PACKAGES_PATH}/nfpm.{package}.yaml",
            target=f"/tmp/dist/ignity-{package}-{version}-linux-{arch}.{packager}",
            packager=packager,
            env={"ARCH": arch, "VERSION": version},
        )


def deb() -> None:
    """Build a debian package."""
    __build_package("deb")


def rpm() -> None:
    """Build an rpm package."""
    __build_package("rpm")


def apk() -> None:
    """Build an alpine package."""
    __build_package("apk")
