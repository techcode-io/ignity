"""Tests for permission and ownership handling."""

from conftest import env_args, run_in_container

IMAGE_KIND = "perms"

_USERMAP_ARGS = env_args(USERMAP_UID=1000, USERMAP_GID=1000, USER="exploit")


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


def test_symlink_below_path_is_not_followed(image):
    # The symlink itself is fixed, what it points to (outside of the path) must be left alone
    result = run_in_container(
        image,
        "echo LINK=$(stat -c '%u:%g' /var/www/symlink-dir/escape); "
        "echo TARGET=$(stat -c '%u:%g:%a' /var/www/outside-file); "
        "echo REGULAR=$(stat -c '%u:%g:%a' /var/www/symlink-dir/regular)",
    )
    assert "LINK=1234:1234" in result.stdout
    assert "TARGET=0:0:644" in result.stdout
    assert "REGULAR=1234:1234:600" in result.stdout


def test_symlinked_path_is_resolved(image):
    result = run_in_container(
        image,
        "echo INNER=$(stat -c '%a' /var/www/real-dir/inner); "
        "echo DIR=$(stat -c '%a' /var/www/real-dir)",
    )
    assert "INNER=600" in result.stdout
    assert "DIR=700" in result.stdout
