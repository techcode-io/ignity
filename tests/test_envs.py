"""Tests for environment variable loading."""

import subprocess

import pytest

from conftest import build_image, run_in_container


@pytest.fixture(scope="module")
def image():
    name = build_image("envs")
    yield name
    subprocess.run(["podman", "rmi", "-f", name], check=False)


def test_envfile_var_present(image):
    assert (
        run_in_container(image, 'with-env env | grep "FOOBAR=test"').returncode == 0
    )


def test_envfile_var_overridable(image):
    assert (
        run_in_container(
            image,
            'with-env env | grep "FOOBAR=override"',
            extra_args=["-e", "FOOBAR=override"],
        ).returncode
        == 0
    )


def test_envfile_var_inherit_order(image):
    assert (
        run_in_container(image, 'with-env env | grep "INHERIT=foobar"').returncode
        == 0
    )
