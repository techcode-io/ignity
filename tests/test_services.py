"""Tests for s6 services management."""

import subprocess

import pytest

from conftest import build_image, run_in_container


@pytest.fixture(scope="module")
def image():
    name = build_image("services")
    yield name
    subprocess.run(["podman", "rmi", "-f", name], check=False)


def test_default_service_ran(image):
    result = run_in_container(image, "test -d /etc/ignity")
    assert "default service" in result.stdout


def test_no_start_service_did_not_run(image):
    result = run_in_container(image, "test -d /etc/ignity")
    assert "no-start service" not in result.stdout


def test_no_start_at_build_time_can_be_started(image):
    cmd = "rm -f /run/ignity/services-state/no-start-at-build-time/down && s6-svc -u /run/ignity/services-state/no-start-at-build-time"
    result = run_in_container(image, cmd)
    assert "no-start service at build time" in result.stdout


def test_no_start_at_runtime_can_be_started(image):
    cmd = "rm -f /run/ignity/services-state/no-start-at-runtime/down && s6-svc -u /run/ignity/services-state/no-start-at-runtime"
    result = run_in_container(image, cmd)
    assert "no-start service at runtime" in result.stdout
