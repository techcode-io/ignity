"""Tests that ignity works with the least privileges: few capabilities and a read-only root."""

import subprocess

import pytest

from conftest import READ_ONLY, env_args, image_fixture, run_in_container

IMAGE_KIND = "split"

# What ignity needs when PID 1 is root:
#  - CHOWN, FOWNER, DAC_OVERRIDE: fix-perms (chown, chmod, then traverse what it just handed over)
#  - SETUID, SETGID: dropping privileges (CMD with IGNITY_CMD_DROP_PRIVILEGES, services)
#  - KILL: signalling processes running as another uid (stop services, shutdown)
MINIMAL = (
    "--cap-drop=ALL",
    "--cap-add=CHOWN",
    "--cap-add=FOWNER",
    "--cap-add=DAC_OVERRIDE",
    "--cap-add=SETUID",
    "--cap-add=SETGID",
    "--cap-add=KILL",
    "--security-opt=no-new-privileges",
    *READ_ONLY,
    # Written by the init script of the fixture
    "--tmpfs=/shared",
    *env_args(
        USERMAP_UID=1000, USERMAP_GID=1000, IGNITY_CMD_DROP_PRIVILEGES=1, IGNITY_SERVICES_GRACETIME=3000,
    ),
)


@pytest.fixture(scope="module")
def result(image):
    # Let the services start and install their traps before the CMD exits
    return run_in_container(
        image,
        "sleep 2; echo UID=$(id -u); grep -E '^Cap(Eff|Prm)' /proc/self/status",
        MINIMAL,
    )


def test_boots_with_minimal_capabilities_and_read_only_root(result):
    assert result.returncode == 0, result.stdout + result.stderr
    assert "split service started" in result.stdout
    assert "split finalize ran" in result.stdout


def test_cmd_dropped_has_no_capabilities(result):
    assert "UID=1000" in result.stdout
    assert result.stdout.count("0000000000000000") == 2


def test_service_dropping_privileges_works(result):
    assert "dropped service started" in result.stdout


def test_services_of_another_uid_are_stopped_gracefully(result):
    assert "dropped service got TERM" in result.stdout


# --- Each capability is really needed ----------------------------------------------------------
#
# Remove one capability from the minimal set and check that what depends on it breaks. If one of
# these tests starts failing, the capability isn't needed anymore (or the scenario no longer
# exercises it) and the list in the README has to be revisited.

CAPABILITIES = ("CHOWN", "FOWNER", "DAC_OVERRIDE", "SETUID", "SETGID", "KILL")

# /data is handed over to 1234:1234 by fix-perms, and the CMD runs as that uid to look at it
COMMAND = (
    "sleep 2; echo UID=$(id -u); "
    "echo FILE=$(stat -c '%u:%a' /data/file); "
    "echo INNER=$(stat -c '%u:%a' /data/sub/inner)"
)


def _args(without: str | None = None) -> tuple[str, ...]:
    caps = tuple(f"--cap-add={cap}" for cap in CAPABILITIES if cap != without)
    return (
        "--cap-drop=ALL",
        *caps,
        "--security-opt=no-new-privileges",
        # Not read-only: /data is part of the image and has to be fixed by fix-perms
        *env_args(
            USERMAP_UID=1234, USERMAP_GID=1234, IGNITY_CMD_DROP_PRIVILEGES=1, IGNITY_SERVICES_GRACETIME=3000,
        ),
    )


caps_image = image_fixture("capabilities", name="caps_image")


def test_control_everything_works_with_the_minimal_set(caps_image):
    result = run_in_container(caps_image, COMMAND, _args())
    assert result.returncode == 0, result.stdout + result.stderr
    assert "UID=1234" in result.stdout
    assert "FILE=1234:600" in result.stdout
    assert "INNER=1234:600" in result.stdout
    assert "dropped service got TERM" in result.stdout


@pytest.mark.parametrize("missing", ["CHOWN", "FOWNER"])
def test_perms_fail_without(caps_image, missing):
    # fix-perms fails, which aborts the boot
    result = run_in_container(caps_image, COMMAND, _args(missing))
    assert result.returncode != 0, result.stdout + result.stderr
    assert "UID=" not in result.stdout


def test_perms_cant_enter_directories_of_other_uids_without_dac_override(caps_image):
    result = run_in_container(caps_image, COMMAND, _args("DAC_OVERRIDE"))
    assert result.returncode == 0, result.stdout + result.stderr
    # What is directly in /data is fixed, what is in /data/sub can't be reached
    assert "FILE=1234:600" in result.stdout
    assert "INNER=1234:644" in result.stdout


@pytest.mark.parametrize("missing", ["SETUID", "SETGID"])
def test_dropping_privileges_fails_without(caps_image, missing):
    result = run_in_container(caps_image, COMMAND, _args(missing))
    assert result.returncode != 0
    assert "UID=1234" not in result.stdout


def test_shutdown_is_stuck_without_kill(caps_image):
    # Nothing can signal the service of another uid, so PID 1 waits for it for ever
    # (the container is left running when the client gives up, remove it)
    with pytest.raises(subprocess.TimeoutExpired):
        run_in_container(caps_image, COMMAND, _args("KILL"), timeout=30)
    stuck = subprocess.run(
        ["podman", "ps", "-aq", "--filter", f"ancestor={caps_image}"],
        capture_output=True, text=True,
    ).stdout.split()
    subprocess.run(["podman", "rm", "-f", *stuck], check=False, capture_output=True)
