"""Shared helpers for ignity pytest tests."""

import os
import secrets
import subprocess
import tempfile
from pathlib import Path
from typing import Final

ROOT: Final[Path] = Path(__file__).parent.parent.resolve()

BASE_DOCKER_ARGS: tuple[str, ...] = (
    "-e", "IGNITY_KILL_GRACETIME=0",
    "-e", "IGNITY_KILL_FINALIZE_MAXTIME=0",
    "-e", "IGNITY_SERVICES_GRACETIME=0",
    "-e", "IGNITY_CMD_WAIT_FOR_SERVICES_MAXTIME=0",
)


def build_image(kind: str) -> str:
    """Build a container image for a test suite kind."""
    tag = secrets.token_hex(16)
    image_name = f"ignity-test-{kind}-{tag}"
    dockerfile_tpl = ROOT / "tests" / "fixtures" / kind / "Dockerfile.tpl"
    base_image = os.environ.get("DOCKER_BASE_IMAGE", "debian:bookworm-slim")
    rendered = dockerfile_tpl.read_text().replace(
        "{{DOCKER_BASE_IMAGE}}", base_image
    )
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, suffix=".Dockerfile"
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
    image: str, command: str, extra_args: list[str] | None = None
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
    return subprocess.run(args, input=command, capture_output=True, text=True)
