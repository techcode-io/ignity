"""Tests for finalize scripts execution."""

from conftest import run_in_container

IMAGE_KIND = "finalize"


def test_finalize_scripts_ran(image):
    result = run_in_container(image, "test -d /etc/ignity")
    assert "We are in finalize stage" in result.stdout
