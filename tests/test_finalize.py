"""Tests for finalize scripts execution."""

import subprocess

import pytest

from conftest import build_image, run_in_container


@pytest.fixture(scope="module")
def image():
    name = build_image("finalize")
    yield name
    subprocess.run(["podman", "rmi", "-f", name], check=False)


def test_finalize_scripts_ran(image):
    result = run_in_container(image, "test -d /etc/ignity")
    assert "We are in finalize stage" in result.stdout
