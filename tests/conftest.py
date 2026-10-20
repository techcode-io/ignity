"""Shared helpers for ignity pytest tests."""

import os
import secrets
import subprocess
import tempfile
from pathlib import Path
from collections.abc import Sequence
from typing import Final

import pytest

ROOT: Final[Path] = Path(__file__).parent.parent.resolve()

BASE_DOCKER_ARGS: tuple[str, ...] = (
    "-e", "IGNITY_KILL_GRACETIME=0",
    "-e", "IGNITY_KILL_FINALIZE_MAXTIME=0",
    "-e", "IGNITY_SERVICES_GRACETIME=0",
    "-e", "IGNITY_CMD_WAIT_FOR_SERVICES_MAXTIME=0",
)

# Read-only root filesystem: /run/ignity is the only place ignity writes to (scripts run from it)
READ_ONLY: tuple[str, ...] = ("--read-only", "--tmpfs=/run/ignity:exec")

# Used when tests/fixtures/<kind>/ has no Containerfile.tpl of its own: ignity plus the kind's rootfs
DEFAULT_CONTAINERFILE: Final[str] = """\
FROM {{DOCKER_BASE_IMAGE}}
COPY src/ /
RUN bash /usr/src/install-ignity.sh
"""


def env_args(**env: str | int) -> tuple[str, ...]:
    """Turn keyword arguments into `-e NAME=value` container arguments."""
    return tuple(arg for name, value in env.items() for arg in ("-e", f"{name}={value}"))


def build_image(kind: str) -> str:
    """Build a container image for a test suite kind."""
    tag = secrets.token_hex(16)
    image_name = f"ignity-test-{kind}-{tag}"
    fixture_dir = ROOT / "tests" / "fixtures" / kind
    containerfile_tpl = fixture_dir / "Containerfile.tpl"
    if containerfile_tpl.exists():
        template = containerfile_tpl.read_text()
    else:
        template = DEFAULT_CONTAINERFILE
        if (fixture_dir / "rootfs").is_dir():
            template += f"COPY tests/fixtures/{kind}/rootfs/ /\n"
    base_image = os.environ.get("DOCKER_BASE_IMAGE", "debian:bookworm-slim")
    rendered = template.replace("{{DOCKER_BASE_IMAGE}}", base_image)
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".Containerfile"
    ) as f:
        f.write(rendered)
        tmp_path = f.name
    try:
        subprocess.run(
            ["podman", "build", "-t", image_name, "-f", tmp_path, str(ROOT)],
            check=True,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return image_name


def run_in_container(
    image: str,
    command: str,
    extra_args: Sequence[str] | None = None,
    timeout: float = 120,
) -> subprocess.CompletedProcess:
    """Run a command in a container and return the result."""
    args = [
        "podman",
        "run",
        "--name",
        f"ignity-{secrets.token_hex(8)}",
        "--entrypoint",
        "/init",
        "--rm",
        "-i",
        *BASE_DOCKER_ARGS,
        *(extra_args or []),
        image,
        "bash",
    ]
    # A container stuck in its shutdown must fail the test, not hang the suite
    return subprocess.run(
        args, input=command, capture_output=True, text=True, timeout=timeout
    )


def image_fixture(kind: str | None = None, name: str = "image"):
    """Module-scoped fixture named `name` giving an image built from tests/fixtures/<kind>/.

    Without kind, the kind is the IMAGE_KIND of the test module.
    """

    @pytest.fixture(scope="module", name=name)
    def fixture(request):
        image_name = build_image(kind or request.module.IMAGE_KIND)
        yield image_name
        subprocess.run(["podman", "rmi", "-f", image_name], check=False)

    return fixture


# Image of the test module, from its IMAGE_KIND
image = image_fixture()
