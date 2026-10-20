"""Tests for init scripts execution."""

from conftest import run_in_container

IMAGE_KIND = "init"


def test_init_scripts_ran(image):
    assert run_in_container(image, "ls -alh /tmp/init-tests").returncode == 0


def test_init_scripts_ran_in_order(image):
    assert run_in_container(image, 'cat /tmp/init-tests | grep "foobar"').returncode == 0
