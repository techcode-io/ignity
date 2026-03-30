"""Tests for boot stage installation."""

import subprocess

import pytest

from conftest import build_image, run_in_container


@pytest.fixture(scope="module")
def image():
    name = build_image("boot")
    yield name
    subprocess.run(["podman", "rmi", "-f", name], check=False)


def test_execlineb_installed(image):
    assert run_in_container(image, "command -v execlineb").returncode == 0


def test_fix_perms_installed(image):
    assert run_in_container(image, "command -v fix-perms").returncode == 0


def test_load_envfile_installed(image):
    assert run_in_container(image, "command -v load-envfile").returncode == 0


def test_with_env_installed(image):
    assert run_in_container(image, "command -v with-env").returncode == 0


def test_with_retries_installed(image):
    assert run_in_container(image, "command -v with-retries").returncode == 0
