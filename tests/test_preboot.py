"""Tests for preboot stage non-root user setup."""

from conftest import run_in_container

IMAGE_KIND = "preboot"


def test_preboot_allows_non_root_user(image):
    assert run_in_container(image, "test -d /etc/ignity").returncode == 0


def test_cmd_keeps_uid_when_pid1_is_not_root(image):
    result = run_in_container(image, "echo UID=$(id -u) GID=$(id -g)")
    assert result.returncode == 0
    assert "UID=1000 GID=1000" in result.stdout
