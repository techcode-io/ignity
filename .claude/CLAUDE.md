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
uv run poe test             # Run full pytest suite (builds 7 container images, 23 tests)
uv run poe test tests/test_boot.py::test_execlineb_installed  # Single test
```

**Building:**
```bash
uv run poe package          # Create dist/ignity.tar.gz tarball from src/
```

All commands require:
- uv (modern Python package manager)
- podman (container runtime for tests)
- bash with standard Unix tools

## Architecture: Three-Stage Boot System

Ignity supervises container processes through three discrete stages:

**Stage 1 (`/etc/s6/boot/stage1`):** Setup
- Creates s6 supervision tree directories
- Initializes `/run/ignity/{envs,init,finalize,services,services-state}`
- Runs preboot (user/permission setup) if needed
- Delegates to stage 2

**Stage 2 (`/etc/s6/boot/stage2`):** Service & CMD Execution
- `stage2-envs`: Loads `/etc/ignity/envs/*` files in order (inheritance pattern)
- `stage2-init`: Executes `/etc/ignity/init/*` scripts in order
- `stage2-services`: Starts s6-supervised services from `/etc/ignity/services/`
- Optionally runs CMD after services healthy (configurable delay via `IGNITY_CMD_WAIT_FOR_SERVICES`)

**Stage 3 (`/etc/s6/boot/stage3`):** Shutdown
- Brings down all services gracefully
- Runs `/etc/ignity/finalize/*` scripts in parallel
- Kills remaining processes, exits

## Key Components

**Boot Stages:**
- `/init` — Entry point (execlineb wrapper calling stage1)
- `/etc/s6/boot/stage{1,2,3}` — Core boot logic
- `/etc/s6/boot/stage2-{envs,init,services}` — Stage 2 sub-scripts
- `/etc/s6/services/.s6-svscan/{crash,finish}` — s6 supervision control

**Utilities:**
- `/usr/bin/preboot` — Non-root user setup (UID/GID mapping)
- `/usr/bin/fix-perms` — Apply permission fixes from spec files
- `/usr/bin/load-envfile` — Load environment variables from files
- `/usr/bin/with-env` — Inject environment variables into command execution
- `/usr/bin/with-retries` — Retry command execution with backoff

**Installation:**
- `/usr/src/install-ignity.sh` — Compiles and installs s6, execline, skalibs from source

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
- 7 test modules in `/tests/`: `test_boot.py`, `test_init.py`, `test_envs.py`, `test_perms.py`, `test_services.py`, `test_preboot.py`, `test_finalize.py`
- Each module builds its own container image dynamically from `tests/fixtures/<kind>/Dockerfile.tpl`
- Test fixtures include rootfs overlays with pre-configured services/scripts
- conftest.py provides `build_image(kind)` and `run_in_container(image, cmd)` helpers

**Test Flow:**
1. `build_image()` renders Dockerfile.tpl (substitutes `{{DOCKER_BASE_IMAGE}}`), builds with random tag via podman
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
- `tests/conftest.py` — Pytest helpers, immutable tuples, type annotations
- `tests/fixtures/` — Dockerfile templates and rootfs overlays (not actual test code)
- `.github/workflows/ci.yml` — Runs `uv run poe test` on PR/push

**Environment Variables (Runtime):**
- `IGNITY_CMD_WAIT_FOR_SERVICES` — Wait for services before CMD (0/1)
- `IGNITY_CMD_WAIT_FOR_SERVICES_MAXTIME` — Wait timeout in milliseconds (default 5000)
- `IGNITY_KILL_GRACETIME` — Shutdown grace period in ms (default 3000)
- `IGNITY_KILL_FINALIZE_MAXTIME` — Max time for finalize scripts in ms (default 5000)
- `IGNITY_SERVICES_GRACETIME` — Service shutdown grace period in ms (default 5000)
- `IGNITY_SKIP_PERMS` — Skip permission fixing (0/1)
- `USER`, `USERMAP_UID`, `USERMAP_GID` — Non-root user mapping

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