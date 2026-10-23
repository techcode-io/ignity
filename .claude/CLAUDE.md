# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Ignity** is a dead-simple process supervision system for containers based on s6 (skarnet supervision suite). It provides lightweight container initialization, supervision, and graceful shutdown with three-stage lifecycle management.

The codebase is shell/execlineb-based (no Python runtime), deployed as a tarball into container images. Development uses Python tooling (uv, pytest, pre-commit) but the runtime itself is shell.

## Commands

**Setup & Development:**
```bash
uv run poe env:configure    # Install pre-commit hooks
```

**Testing:**
```bash
uv run poe test             # Run full pytest suite (builds 9 container images)
uv run poe test tests/test_boot.py::test_execlineb_installed  # Single test
```

**Building:**
```bash
uv run poe package          # Create dist/ignity.tar.gz tarball from src/
uv run poe build            # Static (musl) execline/s6/s6-portable-utils + src/ into dist/ignity, in a container
uv run poe package:deb      # Also package:rpm, package:apk (Linux only): nfpm, dist/ignity-{core,utils}-<version>-linux-<arch>.<format>
IGNITY_INSTALL=package DOCKER_BASE_IMAGE=alpine:3 uv run poe test  # Suite against the package in dist/
```

**Releasing** (GitHub Actions, workflow_dispatch, same flow as techcode-io/terranova):
`Pre release` (version) opens a bump PR (`release:pre`) -> `Release` (next `x.y.z-dev`) reuses CI, tags `x.y.z` (no `v`), attaches the packages (`release`) and opens the next iteration PR (`release:post`). The version lives in `pyproject.toml` only (passed to nfpm as `VERSION`, with `ARCH`).

All commands require:
- uv (modern Python package manager)
- podman (container runtime for tests)
- bash with standard Unix tools

## Architecture: Three-Stage Boot System

Ignity supervises container processes through three discrete stages:

**Stage 1 (`/etc/s6/boot/stage1`):** Setup (PID 1)
- Runs preboot (user/permission setup) if needed
- Validates `IGNITY_MODE` (`full` | `init` | `services`), fails fast otherwise
- Initializes `/run/ignity/{init,finalize,services,services-state}`
- `stage1-envs`: Builds non-secret defaults in `/run/ignity/envs-defaults` from `/etc/ignity/envs/*` (in order, container env wins, container env is never written to disk). They are applied with `s6-envdir` before `s6-svscan`, so every process inherits them
- Forks stage 2, then runs `s6-svscan` on `/run/ignity/services-state`

**Stage 2 (`/etc/s6/boot/stage2`):** Service & CMD Execution (depends on `IGNITY_MODE`)
- `stage2-copy`: Copies `/etc/ignity/{init,finalize,services}` to `/run/ignity`, only what the mode needs
- `stage2-init`: Executes the `/run/ignity/init/*` copies of `/etc/ignity/init/*` in order (skipped in `services` mode)
- `stage2-cmd`: Runs the CMD as PID 1 (root) by default. With `IGNITY_CMD_DROP_PRIVILEGES=1`, drops to `USERMAP_UID:USERMAP_GID` via `s6-applyuidgid` only if PID 1 is root and the mapping isn't 0:0 (supplementary groups set to the gid)
- `stage2-services`: Copies `/run/ignity/services/*` into the live scandir `/run/ignity/services-state` and starts them under s6 (skipped in `init` mode)
- Optionally runs CMD after services healthy (configurable delay via `IGNITY_CMD_WAIT_FOR_SERVICES`); skipped in `init` mode
- Writes the exit status to `/run/ignity/stage2-exited` for stage 3; a failure (or `init` mode completing) stops the supervision tree

| `IGNITY_MODE` | Runs | Use |
|---|---|---|
| `full` (default) | init -> services -> CMD | Docker, Swarm, single container |
| `init` | init only, then exit (non-zero if a script failed) | Kubernetes init container |
| `services` | services -> CMD (+ finalize) | Kubernetes main container |

Containers of a pod share files through a user-mounted volume. No env is handed over between them, so secrets given to the init container stay there.

**Stage 3 (`/etc/s6/boot/stage3`):** Shutdown
- Brings down all services gracefully
- Runs the `/run/ignity/finalize/*` copies of `/etc/ignity/finalize/*` in parallel
- Kills remaining processes, exits with the code stored in `/run/ignity/stage2-exited` (default 0)

## Key Components

**Boot Stages:**
- `/init` — Entry point (execlineb wrapper calling stage1, with `/usr/lib/ignity/bin` first in PATH)
- `/etc/s6/boot/stage{1,2,3}` — Core boot logic
- `/etc/s6/boot/stage1-envs`, `/etc/s6/boot/stage2-{copy,init,services,cmd}` — Boot sub-scripts
- `/etc/s6/services/.s6-svscan/{crash,finish}` — s6 supervision control

**Utilities:**
- `/usr/bin/preboot` — Non-root user setup (UID/GID mapping)
- `/usr/bin/gen-accounts` — With `IGNITY_ACCOUNTS_DIR` set (called by preboot): writes passwd/group copies completed with USER there instead of useradd, for read-only roots; the main container mounts them over /etc/passwd and /etc/group (subPath)
- `/usr/bin/fix-perms` — Apply permission fixes from spec files (never follows symlinks: `chown -h`, symlinks skipped for `chmod`, top-level path resolved once)
- `/usr/bin/load-envfile` — Load environment variables from files
- `/usr/bin/with-env` — POSIX sh. Passthrough by default; `-k <patterns>` narrows the inherited env (PATH always kept), `-d <dir>` loads an envdir (repeatable, applied after `-k`, in order) for that process only (scoped secrets)
- `/usr/bin/with-retries` — Retry command execution with backoff

**Installation:**
- `/usr/src/install-ignity.sh` — Compiles and installs s6, execline, skalibs from source (Debian/Ubuntu). Its `readonly *_VERSION`/`*_URL` are the single source of truth for the skarnet versions, also read by `distributions/build/build-ignity.sh` and bumped by `poe project:upgrade`
- execline, s6 and s6-portable-utils live in `/usr/lib/ignity/{bin,libexec}` (both installs, built with `--enable-absolute-paths`), never in `/bin`. `/init` puts `/usr/lib/ignity/bin` first in PATH via `/usr/lib/ignity/libexec/with-ignity-path`; entry points that can run outside /init (`preboot`, `fix-perms`, `gen-accounts`, `load-envfile`, `with-retries`) start with it and find the other tools through the caller's PATH. Ignity's own scripts use `#!/usr/lib/ignity/bin/execlineb`; `/bin/execlineb` is only a compat link for user scripts, created when absent
- Linux packages (deb/rpm/apk, amd64/arm64): `distributions/build/` builds the bundle (static binaries), `distributions/packages/nfpm.{core,utils}.yaml` package it in two: `ignity-core` (all but fix-perms, depends on the virtual `ignity-utils-impl`) and `ignity-utils` (execline `fix-perms`, provides `ignity-utils-impl`; techcode-io/ignity-utils-rs is the Rust alternative providing it too). Both conflict with/replace the `ignity` package of <= 0.1.0. `postinstall.sh`/`preremove.sh` manage the `/bin/execlineb` link (also rpm posttrans, as the obsoleted `ignity` preun runs after `%post`). No Conflicts/Provides with the distribution's execline/s6

## Container Configuration (User-Provided)

Users mount these directories into container to customize behavior:

| Directory | Purpose | Pattern |
|-----------|---------|---------|
| `/etc/ignity/envs/` | Environment variables | Files loaded in order (00-, 01-, etc.) |
| `/etc/ignity/init/` | Initialization scripts | Executed before services start |
| `/etc/ignity/services/` | s6 service definitions | Standard s6 servicedir (run, finish, down files) |
| `/etc/ignity/perms/` | Ownership/permission specs | Applied to filesystem paths |
| `/etc/ignity/finalize/` | Shutdown scripts | Executed when container exits |

Scripts use numbered prefixes (00-, 01-, etc.) for deterministic ordering. Convention reserves 10 numbers per Docker layer for extension.

## Testing

**Framework:** pytest + Podman integration tests

**Structure:**
- 9 test modules in `/tests/`: `test_boot.py`, `test_init.py`, `test_envs.py`, `test_perms.py`, `test_services.py`, `test_preboot.py`, `test_finalize.py`, `test_modes.py`, `test_least_privilege.py`
- Each module sets `IMAGE_KIND`; the shared `image` fixture (conftest) builds it from `tests/fixtures/<kind>/`: its own `Containerfile.tpl` if present, else ignity + `rootfs/` (see `DEFAULT_CONTAINERFILE`). Extra images can still be built with `build_image()`
- Test fixtures include rootfs overlays with pre-configured services/scripts
- conftest.py provides the `image` fixture, `build_image(kind)`, `run_in_container(image, cmd, extra_args)`, `env_args(**env)` (`-e` arguments) and `READ_ONLY` (read-only root arguments)
- Containerfile templates install ignity with `{{IGNITY_INSTALL}}`: from source by default, from the dist/ package matching `DOCKER_BASE_IMAGE` (debian/ubuntu/fedora/alpine) with `IGNITY_INSTALL=package`

**Test Flow:**
1. `build_image()` renders Containerfile.tpl (substitutes `{{DOCKER_BASE_IMAGE}}` and `{{IGNITY_INSTALL}}`), builds with random tag via podman
2. `run_in_container()` executes shell command inside container with `/init` entrypoint
3. Tests assert on exit codes and stdout content

All timeouts set to 0 for fast test iterations.

## Development Notes

**Commit Messages:**
Follow conventional commits: `type: description` (types: build, ci, docs, feat, fix, perf, refactor, test, chore). Max 80 chars. Enforced by gitlint hook.

**Build System:**
- Pre-uv migration: used Taskfile
- Current: uv + poethepoet (poe) for task management
- pyproject.toml defines tasks, dependencies, pytest config
- Python 3.13+ required (for `|` union syntax, f-string features in conftest)

**Key Files:**
- `pyproject.toml` — Project manifest, poe tasks, uv config
- `scripts/binds/` — Thin wrappers around container (docker/podman), nfpm, git, gh; `scripts/tasks/` — poe task implementations (build, package, release, project)
- `tests/conftest.py` — Pytest helpers, immutable tuples, type annotations
- `tests/fixtures/` — Containerfile templates and rootfs overlays (not actual test code)
- `.github/workflows/ci.yml` — On PR/push (and reused by release): `poe test` (source), `package` per arch (native runners), `sanitize` runs the suite from the packages on debian/ubuntu/alpine/fedora

**Environment Variables (Runtime):**
- `IGNITY_CMD_DROP_PRIVILEGES` — Run the CMD as `USERMAP_UID:USERMAP_GID` instead of root (0/1, default 0)
- `IGNITY_CMD_WAIT_FOR_SERVICES` — Wait for services before CMD (0/1)
- `IGNITY_CMD_WAIT_FOR_SERVICES_MAXTIME` — Wait timeout in milliseconds (default 5000)
- `IGNITY_KILL_GRACETIME` — Shutdown grace period in ms (default 3000)
- `IGNITY_KILL_FINALIZE_MAXTIME` — Max time for finalize scripts in ms (default 5000)
- `IGNITY_SERVICES_GRACETIME` — Service shutdown grace period in ms (default 16000)
- `IGNITY_SKIP_PERMS` — Skip permission fixing (0/1)
- `IGNITY_ACCOUNTS_DIR` — Write account files there instead of creating USER in /etc (read-only root filesystem, see `gen-accounts`)
- `IGNITY_MODE` — `full` (default) | `init` (init scripts only, then exit) | `services` (skip init scripts); for Kubernetes init containers. No env is handed between containers, share files through a volume
- `USER`, `USERMAP_UID`, `USERMAP_GID` — Non-root user mapping; also the uid/gid the CMD drops to (`stage2-cmd`) with `IGNITY_CMD_DROP_PRIVILEGES=1`, when PID 1 is root and the mapping isn't 0:0

## Language & Implementation Details

**Execlineb** (s6's native language):
- Used for boot stages for determinism, speed, direct s6 integration
- No variables, no loops — functional composition via chains
- Scripts in `/etc/s6/boot/`

**POSIX Shell:**
- Utilities and helper scripts (`/usr/bin/`, init/finalize user scripts)
- No bash-isms (portability across Alpine, Debian, Ubuntu)

**No Python Runtime:**
This is a shell/execlineb project. Python is only for build/test/dev tooling.

## Further Exploration

For detailed feature documentation, see README.md sections:
- "How to execute initialization and/or finalization tasks"
- "How to set container environment variables"
- "How to fix permissions at build time"
- "How to run a container in read-only mode"

For implementation details on s6 (process supervision, service directory structure), see skarnet.org documentation.