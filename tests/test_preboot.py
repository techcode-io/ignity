"""Tests for preboot stage non-root user setup."""

import subprocess

import pytest

from conftest import build_image, run_in_container


@pytest.fixture(scope="module")
def image():
    name = build_image("preboot")
    yield name
    subprocess.run(["podman", "rmi", "-f", name], check=False)


def test_preboot_allows_non_root_user(image):
    assert run_in_container(image, "test -d /etc/ignity").returncode == 0
