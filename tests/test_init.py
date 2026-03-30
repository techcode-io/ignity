"""Tests for init scripts execution."""

import subprocess

import pytest

from conftest import build_image, run_in_container


@pytest.fixture(scope="module")
def image():
    name = build_image("init")
    yield name
    subprocess.run(["podman", "rmi", "-f", name], check=False)


def test_init_scripts_ran(image):
    assert run_in_container(image, "ls -alh /tmp/init-tests").returncode == 0


def test_init_scripts_ran_in_order(image):
    assert run_in_container(image, 'cat /tmp/init-tests | grep "foobar"').returncode == 0
