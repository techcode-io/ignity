import secrets
import shutil
from pathlib import Path
from typing import Final

from scripts.binds.container import Container

ROOT_DIR: Final[Path] = Path(__file__).parent.parent.parent
DIST_DIR: Final[Path] = ROOT_DIR / "dist"
CONTAINERFILE_PATH: Final[Path] = ROOT_DIR / "distributions/build/Containerfile"


def run() -> None:
    """Build the ignity bundle for the current architecture into dist/ignity."""
    # The bundle is built in a container, then copied out of its image (see the Containerfile)
    container = Container()
    image = f"ignity-bundle-{secrets.token_hex(8)}"
    container.build(image, CONTAINERFILE_PATH, ROOT_DIR)
    try:
        container_id = container.create(image)
        try:
            bundle_dir = DIST_DIR / "ignity"
            shutil.rmtree(bundle_dir, ignore_errors=True)
            DIST_DIR.mkdir(parents=True, exist_ok=True)
            container.cp(f"{container_id}:/ignity", bundle_dir.as_posix())
        finally:
            container.rm(container_id)
    finally:
        container.rmi(image)
