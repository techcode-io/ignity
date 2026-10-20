"""Tests for environment variable loading."""

from conftest import run_in_container

IMAGE_KIND = "envs"


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


def test_env_file_var_inherited_without_with_env(image):
    assert run_in_container(image, 'env | grep "FOOBAR=test"').returncode == 0


def test_container_env_wins_without_with_env(image):
    assert (
        run_in_container(
            image, 'env | grep "FOOBAR=override"', extra_args=["-e", "FOOBAR=override"]
        ).returncode
        == 0
    )


def test_container_env_not_written_to_disk(image):
    result = run_in_container(
        image,
        "! grep -rq topsecret /run/ignity",
        extra_args=["-e", "MYSECRET=topsecret"],
    )
    assert result.returncode == 0


def test_with_env_dir_scopes_variables_to_one_process(image):
    command = (
        "mkdir -p /tmp/sec && printf scoped > /tmp/sec/SCOPED_VAR && "
        'with-env -d /tmp/sec env | grep -q "SCOPED_VAR=scoped" && '
        "! env | grep -q SCOPED_VAR"
    )
    assert run_in_container(image, command).returncode == 0


def test_with_env_keep_narrows_inherited_variables(image):
    result = run_in_container(
        image,
        "with-env -k 'KEEP_*,HOME' env",
        extra_args=["-e", "KEEP_A=1", "-e", "DROP_A=2"],
    )
    assert result.returncode == 0
    assert "KEEP_A=1" in result.stdout
    assert "DROP_A" not in result.stdout
    assert "PATH=" in result.stdout


def test_with_env_empty_keep_list_keeps_only_path(image):
    result = run_in_container(
        image, "with-env -k '' env", extra_args=["-e", "DROP_A=2"]
    )
    assert result.returncode == 0
    assert "DROP_A" not in result.stdout
    assert "PATH=" in result.stdout


def test_with_env_dir_overrides_inherited_variable(image):
    command = (
        "mkdir -p /tmp/sec && printf scoped > /tmp/sec/MYVAR && "
        'with-env -d /tmp/sec env | grep -q "MYVAR=scoped"'
    )
    assert (
        run_in_container(image, command, extra_args=["-e", "MYVAR=inherited"]).returncode
        == 0
    )


def test_with_env_keep_then_dir_merges_secrets_with_narrowed_env(image):
    command = (
        "mkdir -p /tmp/sec && printf s3cr3t > /tmp/sec/DB_PASSWORD && "
        "with-env -k 'KEEP_*' -d /tmp/sec env"
    )
    result = run_in_container(
        image, command, extra_args=["-e", "KEEP_A=1", "-e", "DROP_A=2"]
    )
    assert result.returncode == 0
    assert "KEEP_A=1" in result.stdout
    assert "DB_PASSWORD=s3cr3t" in result.stdout
    assert "DROP_A" not in result.stdout


def test_with_env_multiple_dirs_applied_in_order(image):
    command = (
        "mkdir -p /tmp/a /tmp/b && printf one > /tmp/a/V && printf two > /tmp/b/V && "
        'with-env -d /tmp/a -d /tmp/b env | grep -q "^V=two$" && '
        'with-env -d /tmp/b -d /tmp/a env | grep -q "^V=one$"'
    )
    assert run_in_container(image, command).returncode == 0


def test_with_env_empty_file_unsets_variable(image):
    command = (
        "mkdir -p /tmp/sec && : > /tmp/sec/MYVAR && "
        "! with-env -d /tmp/sec env | grep -q '^MYVAR='"
    )
    assert (
        run_in_container(image, command, extra_args=["-e", "MYVAR=inherited"]).returncode
        == 0
    )


def test_with_env_usage_errors(image):
    result = run_in_container(
        image, "with-env -z env; echo RC=$?; with-env -k X; echo RC=$?"
    )
    assert result.stdout.count("RC=64") == 2


def test_unprivileged_process_cannot_read_pid1_environ(image):
    command = (
        'cat /proc/1/environ | tr "\\0" "\\n" | grep -q MYSECRET && echo ROOT_SEES; '
        's6-setuidgid nobody cat /proc/1/environ >/dev/null 2>&1; echo NOBODY_RC=$?'
    )
    result = run_in_container(image, command, extra_args=["-e", "MYSECRET=topsecret"])
    assert "ROOT_SEES" in result.stdout
    assert "NOBODY_RC=0" not in result.stdout
    assert "NOBODY_RC=" in result.stdout
