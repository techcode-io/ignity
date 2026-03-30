"""Tests for permission and ownership handling."""

import subprocess

import pytest

from conftest import build_image, run_in_container

_USERMAP_ARGS = [
    "-e",
    "USERMAP_UID=1000",
    "-e",
    "USERMAP_GID=1000",
    "-e",
    "USER=exploit",
]


@pytest.fixture(scope="module")
def image():
    name = build_image("perms")
    yield name
    subprocess.run(["podman", "rmi", "-f", name], check=False)


def test_static_uid_gid_permissions(image):
    assert (
        run_in_container(
            image, 'ls -alh /var/www/static-uid-gid | grep -- "-rw------"'
        ).returncode
        == 0
    )


def test_multi_uid_gid_permissions(image):
    assert (
        run_in_container(
            image, 'ls -alh /var/www/multi-uid-gid-01 | grep -- "-rw-r--r--"'
        ).returncode
        == 0
    )


def test_dynamic_uid_gid_default_owner(image):
    assert (
        run_in_container(
            image, 'ls -alh /var/www/dynamic-uid-gid | grep -- "root root"'
        ).returncode
        == 0
    )


def test_dynamic_uid_gid_custom_owner(image):
    assert (
        run_in_container(
            image,
            'ls -alh /var/www/dynamic-uid-gid | grep -- "exploit exploit"',
            extra_args=_USERMAP_ARGS,
        ).returncode
        == 0
    )


def test_dynamic_uid_gid_custom_permissions(image):
    assert (
        run_in_container(
            image,
            'ls -alh /var/www/dynamic-uid-gid | grep -- "-rw-------"',
            extra_args=_USERMAP_ARGS,
        ).returncode
        == 0
    )


def test_skip_perms_stage(image):
    result = run_in_container(
        image, "test -d /etc/ignity", extra_args=["-e", "IGNITY_SKIP_PERMS=1"]
    )
    assert "Applying ownership & permissions fixes" not in result.stdout


def test_execution_perms_stage(image):
    result = run_in_container(
        image, "test -d /etc/ignity", extra_args=["-e", "IGNITY_SKIP_PERMS=0"]
    )
    assert "Applying ownership & permissions fixes" in result.stdout
