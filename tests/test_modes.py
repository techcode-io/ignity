"""Tests for IGNITY_MODE (init container / services container split)."""

import secrets
import subprocess

import pytest

from conftest import env_args, run_in_container

IMAGE_KIND = "split"

INIT = env_args(IGNITY_MODE="init")
SERVICES = env_args(IGNITY_MODE="services")


@pytest.fixture
def shared():
    """A named volume shared between the init and the services containers."""
    name = f"ignity-shared-{secrets.token_hex(8)}"
    subprocess.run(["podman", "volume", "create", name], check=True, capture_output=True)
    yield ("-v", f"{name}:/shared")
    subprocess.run(["podman", "volume", "rm", "-f", name], check=False, capture_output=True)


def test_init_results_shared_with_services(image, shared):
    assert run_in_container(image, "true", [*INIT, *shared]).returncode == 0
    result = run_in_container(image, "cat /shared/marker", [*SERVICES, *shared])
    assert result.returncode == 0
    assert "from-init" in result.stdout


def test_services_mode_skips_init_scripts(image, shared):
    run_in_container(image, "true", [*INIT, *shared])
    result = run_in_container(
        image, 'echo "RUNS=$(wc -l < /shared/runs | tr -d " ")"', [*SERVICES, *shared]
    )
    assert "RUNS=1" in result.stdout


def test_init_mode_does_not_start_services_nor_finalize(image, shared):
    result = run_in_container(image, "true", [*INIT, *shared])
    assert result.returncode == 0
    assert "split service started" not in result.stdout
    assert "split finalize ran" not in result.stdout


def test_services_mode_runs_services_and_finalize(image, shared):
    result = run_in_container(image, "true", [*SERVICES, *shared])
    assert result.returncode == 0
    assert "split finalize ran" in result.stdout


def test_init_failure_fails_the_container(image, shared):
    result = run_in_container(image, "true", [*INIT, *shared, "-e", "INIT_FAIL=1"])
    assert result.returncode != 0


def test_secret_of_init_container_not_in_services_container(image, shared):
    run_in_container(image, "true", [*INIT, *shared, "-e", "SECRET=topsecret"])
    result = run_in_container(
        image, "env; grep -r topsecret /run/ignity /shared", [*SERVICES, *shared]
    )
    assert "topsecret" not in result.stdout


def test_full_mode_unchanged(image):
    result = run_in_container(image, "cat /shared/marker")
    assert result.returncode == 0
    assert "from-init" in result.stdout
    assert "split finalize ran" in result.stdout


def test_invalid_mode_fails(image):
    result = run_in_container(image, "true", ["-e", "IGNITY_MODE=bogus"])
    assert result.returncode != 0
    assert "Invalid IGNITY_MODE" in result.stdout + result.stderr
