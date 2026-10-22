"""Tests for s6 services management."""

from conftest import run_in_container

IMAGE_KIND = "services"


def test_default_service_ran(image):
    result = run_in_container(image, "test -d /etc/ignity")
    assert "default service" in result.stdout


def test_no_start_service_did_not_run(image):
    result = run_in_container(image, "test -d /etc/ignity")
    assert "no-start service" not in result.stdout


def test_no_start_at_build_time_can_be_started(image):
    # The CMD waits for the service to print: it exits right away, and the service is killed with it
    cmd = "rm -f /run/ignity/services-state/no-start-at-build-time/down && s6-svc -u /run/ignity/services-state/no-start-at-build-time && sleep 1"
    result = run_in_container(image, cmd)
    assert "no-start service at build time" in result.stdout


def test_no_start_at_runtime_can_be_started(image):
    cmd = "rm -f /run/ignity/services-state/no-start-at-runtime/down && s6-svc -u /run/ignity/services-state/no-start-at-runtime && sleep 1"
    result = run_in_container(image, cmd)
    assert "no-start service at runtime" in result.stdout


def test_shutdown_waits_for_services(image):
    result = run_in_container(image, "true")
    assert result.returncode == 0
    assert "s6-svwait" not in result.stderr
