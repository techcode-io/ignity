"""Tests for boot stage installation."""

from conftest import READ_ONLY, env_args, run_in_container

IMAGE_KIND = "boot"


def test_execlineb_installed(image):
    assert run_in_container(image, "command -v execlineb").returncode == 0


def test_fix_perms_installed(image):
    assert run_in_container(image, "command -v fix-perms").returncode == 0


def test_load_envfile_installed(image):
    assert run_in_container(image, "command -v load-envfile").returncode == 0


def test_with_env_installed(image):
    assert run_in_container(image, "command -v with-env").returncode == 0


def test_with_retries_installed(image):
    assert run_in_container(image, "command -v with-retries").returncode == 0


def test_cmd_runs_as_root_by_default(image):
    result = run_in_container(image, "echo UID=$(id -u) GID=$(id -g)")
    assert "UID=0 GID=0" in result.stdout


def test_cmd_drops_privileges_to_usermap(image):
    result = run_in_container(
        image,
        "echo UID=$(id -u) GID=$(id -g) GROUPS=$(id -G)",
        extra_args=env_args(USERMAP_UID=1000, USERMAP_GID=1000),
    )
    assert result.returncode == 0
    assert "UID=1000 GID=1000 GROUPS=1000" in result.stdout


def test_cmd_dropped_cannot_read_pid1_environ(image):
    result = run_in_container(
        image,
        "cat /proc/1/environ >/dev/null 2>&1; echo RC=$?",
        extra_args=[
            "-e", "USERMAP_UID=1000", "-e", "USERMAP_GID=1000", "-e", "MYSECRET=x",
        ],
    )
    assert "RC=0" not in result.stdout
    assert "RC=" in result.stdout


def test_cmd_exit_code_kept_when_dropping_privileges(image):
    result = run_in_container(
        image,
        "exit 7",
        extra_args=env_args(USERMAP_UID=1000, USERMAP_GID=1000),
    )
    assert result.returncode == 7


_ACCOUNT = env_args(USER="exploit", USERMAP_UID=1000, USERMAP_GID=1000)


def test_accounts_written_instead_of_creating_user_on_read_only_root(image):
    result = run_in_container(
        image,
        "cat /accounts/passwd /accounts/group; echo IN_ETC=$(grep -c exploit /etc/passwd)",
        [*READ_ONLY, "--tmpfs=/accounts", "-e", "IGNITY_ACCOUNTS_DIR=/accounts", *_ACCOUNT],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "exploit:x:1000:1000::/home/exploit:/bin/false" in result.stdout
    assert "\nexploit:x:1000:\n" in result.stdout
    # The existing accounts are kept and /etc itself is untouched
    assert "root:x:0:0:" in result.stdout
    assert "IN_ETC=0" in result.stdout


def test_accounts_of_init_container_mounted_in_main_container(image, tmp_path):
    accounts = ["-v", f"{tmp_path}:/accounts"]
    init = run_in_container(
        image,
        "true",
        [
            *READ_ONLY, *accounts, "-e", "IGNITY_MODE=init",
            "-e", "IGNITY_ACCOUNTS_DIR=/accounts", *_ACCOUNT,
        ],
    )
    assert init.returncode == 0, init.stdout + init.stderr
    assert (tmp_path / "passwd").is_file()
    assert (tmp_path / "group").is_file()

    # The main container has a read-only root and nothing creates the user there
    main = run_in_container(
        image,
        "echo NAME=$(id -un) GROUP=$(id -gn) UID=$(id -u)",
        [
            *READ_ONLY,
            "-v", f"{tmp_path}/passwd:/etc/passwd:ro",
            "-v", f"{tmp_path}/group:/etc/group:ro",
            *_ACCOUNT,
        ],
    )
    assert main.returncode == 0, main.stdout + main.stderr
    assert "NAME=exploit GROUP=exploit UID=1000" in main.stdout


def test_accounts_reject_invalid_user_name(image):
    result = run_in_container(
        image,
        "true",
        [
            *READ_ONLY, "--tmpfs=/accounts", "-e", "IGNITY_ACCOUNTS_DIR=/accounts",
            "-e", "USER=bad:0:0::/:/bin/sh", "-e", "USERMAP_UID=1000", "-e", "USERMAP_GID=1000",
        ],
    )
    assert result.returncode != 0
    assert "Invalid USER" in result.stdout + result.stderr


def test_accounts_reject_name_with_newline(image):
    result = run_in_container(
        image,
        "true",
        [
            *READ_ONLY, "--tmpfs=/accounts", "-e", "IGNITY_ACCOUNTS_DIR=/accounts",
            "-e", "USER=ok\nroot2:x:0:0::/:/bin/sh",
            "-e", "USERMAP_UID=1000", "-e", "USERMAP_GID=1000",
        ],
    )
    assert result.returncode != 0
    assert "Invalid USER" in result.stdout + result.stderr


def test_accounts_reject_non_numeric_ids(image):
    result = run_in_container(
        image,
        "true",
        [
            *READ_ONLY, "--tmpfs=/accounts", "-e", "IGNITY_ACCOUNTS_DIR=/accounts",
            "-e", "USER=exploit", "-e", "USERMAP_UID=1000:0", "-e", "USERMAP_GID=1000",
        ],
    )
    assert result.returncode != 0


def test_accounts_never_duplicate_an_existing_id(image):
    result = run_in_container(
        image,
        "echo OTHER=$(grep -c '^other:' /accounts/passwd /accounts/group | tr '\\n' ' ')",
        [
            *READ_ONLY, "--tmpfs=/accounts", "-e", "IGNITY_ACCOUNTS_DIR=/accounts",
            "-e", "USER=other", "-e", "USERMAP_UID=0", "-e", "USERMAP_GID=0",
        ],
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "/accounts/passwd:0" in result.stdout
    assert "/accounts/group:0" in result.stdout
