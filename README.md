<h1 align="center">Ignity</h1>

<p align="center">
  <i align="center">Dead simple process supervision for containers based on s6.</i>
  <br>
  <i align="center">Inspired by s6-overlay</i>
</p>

<h4 align="center">
  <a href="[https://github.com/techcode-io/ignity/actions/workflows/ci.yml](https://github.com/techcode-io/ignity/actions/workflows/ci.yml)">
    <img src="https://img.shields.io/github/actions/workflow/status/techcode-io/ignity/ci.yml?branch=main&label=ci&style=flat-square" alt="continuous integration" style="height: 20px;">
  </a>
  <a href="https://github.com/techcode-io/ignity/graphs/contributors">
    <img src="https://img.shields.io/github/contributors-anon/techcode-io/ignity?color=yellow&style=flat-square" alt="contributors" style="height: 20px;">
  </a>
  <a href="https://opensource.org/licenses/Apache-2.0">
    <img src="https://img.shields.io/badge/apache%202.0-blue.svg?style=flat-square&label=license" alt="license" style="height: 20px;">
  </a>
  <br>
</h4>

- [Source](https://github.com/techcode-io/ignity)
- [Issues](https://github.com/techcode-io/ignity/issues)
- [Contact](mailto:adrien.mannocci@gmail.com)
- [Maintained by techcode.io](https://techcode.io)

## :package: Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) for development.
- [Podman](https://podman.io/docs/installation) for development.

## :sparkles: Features

- Low memory overhead
- Simple lifecycle management
- Fast startup
- Reliable supervision
- Allow high inheritance

## :dart: Motivation

- We needed a way manage multiples processes within a single container.
- The solution should be memory efficient.
- The solution should be reliable and allow fast startup.

## :hammer: Workflow

### Setup

The following steps will ensure your project is cloned properly.

1. `git clone https://github.com/techcode-io/ignity`
2. `cd ignity && uv run poe env:configure`

### Test

- To test you have to use the workflow script.

```bash
uv run poe test
```

- It will test project code with the current environment.

### Package

- To package you have to use the workflow script.

```bash
uv run poe package
```

- It will create a tar archive containing ignity.

## 📖 Usage

### How it works

- We use `s6` as supervision suite.
- `ignity` is a wrapper around `s6`.
- There are three different stage.
- The first stage is responsible of set up container environment.
- It will create `ignity` runtime directories.
- Load & merge defined variables.
- The second stage will then run `perms` & `init` scripts.
- If everything is alright then it will start all services.
- If a command is defined, it will run after a defined delay and then exit.
- If a command isn't defined, it will run forever until a explicit signal or a crash.
- The third stage is responsible to bringing down the container.
- It will stop services and in parallel will run `finalize` scripts.
- It will then kill everything and exit.

### Available configuration parameters

| Parameter                              | Description                                                                                                           | Value (Current) |
|----------------------------------------|-----------------------------------------------------------------------------------------------------------------------|-----------------|
| `IGNITY_CMD_WAIT_FOR_SERVICES_MAXTIME` | The maximum time (in milliseconds) the services could take to bring up before proceding to CMD executing              | 5000            |
| `IGNITY_CMD_WAIT_FOR_SERVICES`         | In order to proceed executing CMD overlay will wait until services are up                                             | 0               |
| `IGNITY_KILL_FINALIZE_MAXTIME`         | The maximum time (in milliseconds) a script in `/etc/ignity/finalize` could take before sending a `KILL` signal to it | 5000            |
| `IGNITY_KILL_GRACETIME`                | How long (in milliseconds) `ignity` should wait to reap zombies before sending a `KILL` signal                        | 3000            |
| `IGNITY_MODE`                          | Which phases the container runs: `full`, `init` or `services` (see Kubernetes init containers)                        | full            |
| `IGNITY_ACCOUNTS_DIR`                  | Where to write passwd/group files completed with `USER`, instead of creating it in `/etc` (read-only root filesystem) |                 |
| `IGNITY_SERVICES_GRACETIME`            | How long (in milliseconds) `ignity` should wait services down before sending a down signal                            | 16000           |
| `IGNITY_SYNC_DISKS`                    | Call `s6-sync` before and after sending the termination signals (0/1)                                                 | 1               |
| `USER`                                 | User name to map with uid and gid                                                                                     | root            |
| `USERMAP_GID`                          | User gid to map on files, and group of the `CMD` (see "How to run the CMD as a non root user")                        | 0               |
| `USERMAP_UID`                          | User uid to map on files, and user of the `CMD` (see "How to run the CMD as a non root user")                         | 0               |

### How to integrate ignity in your project from source

- You can simply `git clone` the project in the scope of the dockerfile.
- And then build your image as usual.

```Dockerfile
# Install ignity from source
COPY ignity/src /
RUN bash /usr/src/install-ignity.sh \
```

### How to use ignity as `ENTRYPOINT`

- By default, `ignity` isn't set as entrypoint.
- If you want to use it to handle services and all specifics stuff you have to explicitly define it as entrypoint.

```bash
ENTRYPOINT [ "/init" ]
```

### How to use ignity with a `CMD`

- Using `CMD` is a really convenient way to take advantage of `ignity`.
- Your `CMD` can be given at build-time in the Dockerfile, or at runtime on the command line, either way is fine.
- It will be run under the s6 supervisor, and when it fails or exits, the container will exit. You can even run
  interactive programs under the s6 supervisor !

### How to load env files

- Sometimes it's interesting to load env files to define default variables.
- You can simply put any env files in `/etc/ignity/envs` and they will be loaded during runtime in order.
- They will be overrided by container environments variables.
- They are inherited by every process (init scripts, services, finalize scripts and `CMD`), so they are meant for non
  secret values.

### How to supervise a service

- Creating a supervised service cannot be easier
- Just create a service directory with the name of your service into `/etc/ignity/services`
- Put a `run` file into it, this is the file in which you'll put your long-lived process execution
- You're done! If you want to know more about s6 supervision of servicedirs take a look to [
  `servicedir`](https://skarnet.org/software/s6/servicedir.html) documentation.

### How to run hook on service exit

- By default, services created in `/etc/ignity/services` will automatically restart.
- If a service should bring the container down, you'll need to write a `finish` script that does that.

`/etc/ignity/services/myapp/finish`:

```
#!/bin/execlineb -S0

s6-svscanctl -t /run/ignity/services-state
```

- It's possible to do more advanced operations.

`/etc/ignity/services/myapp/finish`:

```
#!/bin/execlineb -S1
if { eltest ${1} -ne 0 }
if { eltest ${1} -ne 256 }

s6-svscanctl -t /run/ignity/services-state
```

### How to start a service on-demand

- By default, all services are started at runtime.
- You can delay or disable automatic start by creating a `down` file in
  the [service directory](https://skarnet.org/software/s6/servicedir.html).
- This file can be created at build time in `/etc/ignity/services/myapp/down`.
- Or at runtime by creating the file in `/run/ignity/services/myapp/down` using init scripts.
- Note that after first services start the service directory is `/run/ignity/services-state` instead of
  `/run/ignity/services`.
- Then you can start it manually by removing the file in `/run/ignity/services-state/myapp/down` and by calling
  `s6-svc -u /run/ignity/services-state/myapp`.

### How to execute initialization and/or finalization tasks

- Just before starting user provided services.
- `ignity` will execute in order all scripts present in `/etc/ignity/init`.
- And in parallel of bringing down user provided services.
- `ignity` will execute in order all scripts present in `/etc/ignity/finalize`.
- You can use this mecanism to setup the container or validate everything or clean some resources before container exit.

### How to set container environment variables

- The container environment, and the defaults from `/etc/ignity/envs`, are inherited by every process `ignity` starts,
  so a plain script can use them:

`/etc/ignity/init/01-example`:

```sh
#!/bin/sh
echo $MYENV
```

- This script will output whatever the `MYENV` environment variable contains.
- The container environment is never copied to disk by `ignity`.
- The `with-env` helper is still available. Without option it simply runs the given program, so existing
  `#!/usr/bin/with-env sh` scripts keep working.

### How to scope secrets to a single process

- Everything exported in the container environment is inherited by all processes of the container.
- To give a secret to one process only, provide it as a file (for example a mounted secret) and load it with `with-env`,
  which can also narrow what the process inherits:

```text
with-env [-k patterns] [-d dir]... [--] prog [args...]
```

- `-k patterns`: keep only the inherited variables matching one of the comma separated names or globs
  (`HOME,LANG,APP_*`) and drop the others. `PATH` is always kept. An empty list (`-k ''`) keeps `PATH` only. Quote the
  patterns so your shell doesn't expand them.
- `-d dir`: load an envdir, which can be repeated. Each file of the directory is a variable: the file name is the
  variable name and the content is its value, verbatim (newlines inside the value are kept, which suits multi-line keys,
  only the final newline is removed). An empty file unsets the variable.
- Narrowing is applied first and the directories after it, in the order given. A variable of a directory therefore wins
  over an inherited one, and a later directory wins over an earlier one.
- Without option, `with-env` runs the program as is.
- `with-env` is a POSIX `sh` script, so it needs `/bin/sh` in the image, and `awk` when `-k` is used.

`/etc/ignity/services/myapp/run`:

```sh
#!/bin/sh
# myapp only gets a few container variables plus its own secrets
exec with-env -k 'HOME,LANG,TZ,APP_*' -d /run/secrets/myapp myapp
```

- Give each service its own directory: `-d` loads every file it contains.
- Files have their own constraints: rotation needs a restart of the process, and file mode and ownership have to match
  the user running it.

#### What this does and does not protect

- This limits what a process, and everything it spawns, inherits. It is not a boundary against other processes of the
  container.
- `/proc/<pid>/environ` is readable by processes running with the same uid, and by root. When services drop privileges
  to another uid, they cannot read the environment of PID 1 (root), and `allowPrivilegeEscalation: false` stops them
  from getting it back. Services running with the same uid as PID 1 can read it.
- Dropping the uid does not clear the environment: a service still starts with the full container environment unless you
  narrow it with `-k`.
- The `CMD` runs as `USERMAP_UID:USERMAP_GID` (see below), but it still starts with the full environment unless you
  narrow it. Init and finalize scripts run with the uid of PID 1 (root), and the full environment, unless they drop
  privileges themselves.

### How to use ignity with Kubernetes init containers

- `ignity` can run the same image twice in a pod: first as an init container, then as the main container.
- `IGNITY_MODE` selects what a container does:

| Mode       | What it runs                                                            | Exit                                                      |
|------------|-------------------------------------------------------------------------|-----------------------------------------------------------|
| `full`     | `init` scripts, services, then `CMD` (default, same as before)          | When `CMD` exits or on signal                             |
| `init`     | Only `init` scripts. Services, `finalize` scripts and `CMD` are skipped | As soon as scripts are done, with a failure if one failed |
| `services` | Services and `finalize` scripts, then `CMD`. `init` scripts are skipped | Same as `full`                                            |

- Results of the init phase are shared through a volume that you mount in both containers. `ignity` does not hand over
  any environment variable between containers.
- This is also the way to keep secrets out of the main container: only give them to the init container (environment or
  secret volume) and leave them out of the main one.

```yaml
spec:
  volumes:
    - name: shared
      emptyDir:
        medium: Memory
  initContainers:
    - name: init
      image: myapp
      command: [ "/init" ]
      env:
        - name: IGNITY_MODE
          value: init
        - name: DB_ADMIN_PASSWORD # only visible here
          valueFrom:
            secretKeyRef: { name: db, key: admin-password }
      volumeMounts:
        - { name: shared, mountPath: /shared }
  containers:
    - name: app
      image: myapp
      command: [ "/init" ]
      args: [ "myapp" ]
      env:
        - name: IGNITY_MODE
          value: services
        - name: IGNITY_SKIP_PERMS # already applied by the init container
          value: "1"
      volumeMounts:
        - { name: shared, mountPath: /shared }
```

- `perms` fixes run on every container that doesn't set `IGNITY_SKIP_PERMS=1`.
- If the init phase produces a secret for the main container, write it as a file on the shared volume with a restrictive
  mode, and remove it once consumed. A memory backed `emptyDir` keeps it off the node disk.

### How to run a container with non root user

- To run a container with a non root user, you have to define files and directories permissions in `perms` and then
  define the following in the Dockerfile

```bash
ENV \
  USERMAP_UID="1000" \
  USERMAP_GID="1000" \
  USER="exploit"
RUN preboot
USER ${USERMAP_UID}:${USERMAP_GID}
```

- This will correct permissions at build time instead of runtime and will let the container start properly with a non
  root user.

### How to run ignity as root (PID 1) with the least privileges

- This is the setup to use when the `CMD` or the services run with their own uid, which a non root PID 1 can't do.
- PID 1 stays root but only keeps the capabilities `ignity` needs:

| Capability     | Needed for                                                                                   |
|----------------|----------------------------------------------------------------------------------------------|
| `CHOWN`        | `fix-perms` changing owners                                                                  |
| `FOWNER`       | `fix-perms` changing modes of files that belong to another uid (the one it just handed over) |
| `DAC_OVERRIDE` | `fix-perms` reading what it just handed over (a `0700` directory of another uid)             |
| `SETUID`       | The `CMD` (`USERMAP_UID`) and services dropping privileges                                   |
| `SETGID`       | Same, including supplementary groups                                                         |
| `KILL`         | Sending signals to processes running as another uid: stopping services, shutdown (without it the container never stops) |

- Nothing else is used: no `NET_RAW`, `NET_BIND_SERVICE`, `SYS_CHROOT`, `MKNOD`, `SETFCAP`, `SETPCAP`, `AUDIT_WRITE`...
  Add `FSETID` only if your `perms` files set setuid or setgid bits.
- This list comes from reading the scripts and is checked by `tests/test_least_privilege.py`. It doesn't cover what your
  own init scripts and services do.
- A process that drops privileges loses its capabilities (the `CMD` ends up with none), so they only concern PID 1, the
  init and finalize scripts.
- `allowPrivilegeEscalation: false` is fine: nothing relies on setuid binaries.

**Read-only root filesystem**

- See "How to run a container in read-only mode": `/run/ignity` is the only writable mount needed, and the user has to
  exist at build time or be generated by an init container.

**Network**

- Services don't need any capability to connect (HTTP, TCP...) or to listen on a port of 1024 and above.
- Listening on a port below 1024 needs `NET_BIND_SERVICE`, but a service that dropped privileges doesn't keep the
  capabilities of PID 1, so adding it to the container doesn't help. Lower the limit for the pod instead with the
  `net.ipv4.ip_unprivileged_port_start` sysctl (`securityContext.sysctls`), or listen on a high port behind a Service.

```yaml
spec:
  volumes:
    - name: run
      emptyDir:
        medium: Memory
  containers:
    - name: app
      image: myapp
      command: [ "/init" ]
      args: [ "myapp" ]
      env:
        - { name: USERMAP_UID, value: "1000" }
        - { name: USERMAP_GID, value: "1000" }
      securityContext:
        runAsUser: 0
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: [ "ALL" ]
          add: [ "CHOWN", "FOWNER", "DAC_OVERRIDE", "SETUID", "SETGID", "KILL" ]
      volumeMounts:
        # emptyDir mounts allow exec by default
        - { name: run, mountPath: /run/ignity }
```

- Root and these capabilities are allowed by the Pod Security `baseline` level (all of them are in its default list),
  not by `restricted`, which requires `runAsNonRoot`: see "How to run ignity with a non root PID 1" there.

### How to create the user with a read-only root filesystem

- `preboot` creates `USER` in `/etc/passwd` and `/etc/group` when it is missing, which a read-only root filesystem
  doesn't allow.
- Set `IGNITY_ACCOUNTS_DIR` and it writes copies of the two files completed with the user in that directory instead
  (`/etc` is left alone). Mount them over `/etc/passwd` and `/etc/group` in the containers that need the account.
- This is meant for the init container: the mounts exist when a container starts, so the files have to be written by a
  container that ran before.
- You only need this if something has to resolve the account (`whoami`, `getpwuid`, `HOME`...). `ignity` itself works
  with numeric ids, and `USERMAP_UID` / `USERMAP_GID` don't need an account.

```yaml
spec:
  volumes:
    - name: accounts
      emptyDir: { }
    - name: run-init
      emptyDir: { medium: Memory }
    - name: run
      emptyDir: { medium: Memory }
  initContainers:
    - name: init
      image: myapp
      command: [ "/init" ]
      env:
        - { name: IGNITY_MODE, value: init }
        - { name: IGNITY_ACCOUNTS_DIR, value: /accounts }
        - { name: USER, value: app }
        - { name: USERMAP_UID, value: "1000" }
        - { name: USERMAP_GID, value: "1000" }
      securityContext:
        readOnlyRootFilesystem: true
        allowPrivilegeEscalation: false
        capabilities: { drop: [ "ALL" ] }
      volumeMounts:
        - { name: accounts, mountPath: /accounts }
        - { name: run-init, mountPath: /run/ignity }
  containers:
    - name: app
      image: myapp
      command: [ "/init" ]
      args: [ "myapp" ]
      env:
        - { name: USER, value: app }
        - { name: USERMAP_UID, value: "1000" }
        - { name: USERMAP_GID, value: "1000" }
      securityContext:
        readOnlyRootFilesystem: true
        allowPrivilegeEscalation: false
        capabilities:
          drop: [ "ALL" ]
          add: [ "SETUID", "SETGID", "KILL" ]
      volumeMounts:
        - { name: run, mountPath: /run/ignity }
        - { name: accounts, mountPath: /etc/passwd, subPath: passwd, readOnly: true }
        - { name: accounts, mountPath: /etc/group, subPath: group, readOnly: true }
```

- The main container finds the account in `/etc/passwd`, so `preboot` has nothing to create there. It doesn't need
  `IGNITY_ACCOUNTS_DIR`.
- Don't set `IGNITY_SKIP_PERMS=1` on the init container: it skips the whole `preboot`, accounts included.
- What it writes: the existing entries, plus `USER` (home `/home/USER`, shell `/bin/false`, no home directory created,
  like `useradd -M`) and its group. Nothing is added when the uid, the gid or the name is already used, and there is no
  `shadow` file.
- `USER` must be a plain name (letters, digits, `_` and `-`), and `USERMAP_UID` and `USERMAP_GID` numbers: the values
  end up in colon separated files, anything else makes `preboot` fail.
- Needs `getent` in the image (Debian and Ubuntu have it).

### How to run ignity with a non root PID 1

- This is the exception, not the recommended setup: prefer the root PID 1 with the least privileges above, which keeps
  the `CMD` and the services able to run with their own uid.
- It is only worth it when the cluster enforces Pod Security `restricted` (`runAsNonRoot: true`), or when a single uid
  for the whole container is fine.
- What changes with a non root PID 1:
    - everything runs with the same uid: the `CMD` and the services can't drop to another one, and can read each other's
      `/proc/<pid>/environ`. Narrow what they inherit with `with-env -k` and keep secrets out of the container's
      environment;
    - `preboot` can't create the user nor apply `perms`: set `IGNITY_SKIP_PERMS=1`, create the user at build time and
      fix the ownership of the image paths at build time too;
    - Kubernetes sets the uid and gid (`runAsUser`, `runAsGroup`) and the group of the volumes (`fsGroup`, how far it is
      honored depends on the volume type and the CSI driver).
- `/run/ignity` still needs its own writable mount, see "How to run a container in read-only mode".
- This setup isn't covered by the tests.

### How to run the CMD as a non root user

- By default `USERMAP_UID` and `USERMAP_GID` are `0`, so the `CMD` runs as root, like PID 1.
- If PID 1 is root and either of them is not `0`, the `CMD` runs as `USERMAP_UID:USERMAP_GID`. Supplementary groups are
  replaced by `USERMAP_GID`, the `CMD` doesn't keep the groups of root.
- Only the `CMD` is affected. Init scripts, finalize scripts and services keep running as PID 1, and services drop
  privileges themselves in their `run` script if they need it.
- The environment is not changed: `HOME`, `USER` and the other variables stay as they are, so set them in the container
  if the `CMD` needs them.
- If PID 1 isn't root already (for example `USER` is set in the Dockerfile, see above), it can't change uid: the `CMD`
  simply runs as that user.
- The uid and gid are used as is, no user account is required. Files the `CMD` has to write must belong to that uid,
  which is what `/etc/ignity/perms` is for.
- Because it isn't the uid of PID 1 anymore, the `CMD` can't read `/proc/1/environ`.

```yaml
env:
  - { name: USERMAP_UID, value: "1000" }
  - { name: USERMAP_GID, value: "1000" }
```

### How to run a container in read-only mode

- The only place `ignity` writes to is `/run/ignity`: mount a writable tmpfs (or a Kubernetes `emptyDir`) there, with
  `exec` because init scripts and services are executed from it.
- If PID 1 runs as a non root user, the uid also needs to be able to write, execute and read on this location.
- Use one mount per container: `/run/ignity` is private runtime state, `ignity` wipes it on start.

```yaml
tmpfs:
  - "/run/ignity:exec,mode=1777,uid=<uid>"
```

- Create `USER` at build time (`RUN preboot`, see above): at runtime `preboot` only creates it when it is missing, which
  needs a writable `/etc`. On Kubernetes you can generate it in an init container instead, see "How to create the user
  with a read-only root filesystem".
- Apply `perms` only on paths that are writable (volumes), or at build time and set `IGNITY_SKIP_PERMS=1`. On a
  read-only path `chown` fails and `preboot` aborts the boot.
- Whatever your own services write (`/tmp`, logs, data) needs its own writable volumes: `ignity` doesn't write anywhere
  else.

### How to fix ownership & permissions

- Sometimes it's interesting to fix ownership & permissions before proceeding because, for example, you have
  mounted/mapped a host folder inside your container.
- Ignity provides a way to tackle this issue using files in `/etc/ignity/perms`.
- The pattern format followed by fix-perms files:

```text
path recurse account fmode dmode
> /var/lib/mysql 1000:1000 0600 0700
```

- `path`: File or dir path.
- `account`: Target account `uid:gid`.
- `fmode`: Target file mode. For example, `0644`.
- `dmode`: Target dir/folder mode. For example, `0755`.

- You can use variables `{{USERMAP_UID}}` and `{{USERMAP_GID}}` in those files.
- They will be replaced at runtime or build time based on case.
- You can also skip the permission phase by using `IGNITY_SKIP_PERMS=1`
- Symlinks are never followed: a symlink found below a path gets its own owner changed, but what it points to is left
  alone, and its mode is ignored. The path itself can be a symlink, it is resolved once.

### How to drop privileges

- When it comes to executing a service, no matter it's a service or a logging service, a very good practice is to drop
  privileges before executing it.
- `s6` already includes utilities to do exactly these kind of things:

In `execline`:

```sh
#!/bin/execlineb -P
s6-setuidgid daemon
myapp
```

In `sh`:

```sh
#!/usr/bin/env sh
exec s6-setuidgid daemon myservice
```

- If you want to know more about these utilities, please take a look to: [`s6-setuidgid`](http://skarnet.org/software/s6/s6-setuidgid.html),
  [`s6-envuidgid`](http://skarnet.org/software/s6/s6-envuidgid.html) and [`s6-applyuidgid`](http://skarnet.org/software/s6/s6-applyuidgid.html).

### How to allow high inheritance

- It's convenient to prefix every scripts in `envs`, `perms`, `init` and `finalize` by number (two chars) to ensure
  execution order.
- A common pattern is to dedicated 10 number by docker image layer to allow logic evolution.

### How to customize `ignity` behaviour

It is possible somehow to tweak `ignity` behaviour by providing an already predefined set of environment variables to
the execution context:

- `IGNITY_CMD_WAIT_FOR_SERVICES_MAXTIME` (default = 5000): The maximum time (in milliseconds) the services could take to
  bring up before proceding to CMD executing.
- `IGNITY_CMD_WAIT_FOR_SERVICES` (default = 0): In order to proceed executing CMD overlay will wait until services are
  up. Be aware that up doesn't mean ready. Depending if `notification-fd` was found inside the servicedir overlay will
  use `s6-svwait -U` or `s6-svwait -u` as the waiting statement.
- `IGNITY_KILL_FINALIZE_MAXTIME` (default = 5000): The maximum time (in milliseconds) a script in `/etc/ignity/finalize`
  could take before sending a `KILL` signal to it. Take into account that this parameter will be used per each script
  execution, it's not a max time for the whole set of scripts.
- `IGNITY_KILL_GRACETIME` (default = 3000): How long (in milliseconds) `ignity` should wait to reap zombies before
  sending a `KILL` signal.
- `IGNITY_SERVICES_GRACETIME` (default = 16000): How long (in milliseconds) `ignity` should wait services down before
  sending a down signal.
- `IGNITY_SYNC_DISKS` (default = 1): Call `s6-sync` before and after sending the termination signals.
- `IGNITY_MODE` (default = full): `full` runs everything, `init` only runs the `init` scripts and exits, `services`
  skips the `init` scripts. See "How to use ignity with Kubernetes init containers".

## :heart: Contributing

If you find this project useful here's how you can help, please click the :eye: **Watch** button to avoid missing
notifications about new versions, and give it a :star2: **GitHub Star**!

You can also contribute by:

- Sending a [Pull Request](https://github.com/techcode-io/ignity/pulls) with your awesome new features and bug fixed.
- Be part of the community and help resolve [Issues](https://github.com/techcode-io/ignity/issues).

## 🧾 License

The `ignity` project is free and open-source software licensed under the Apache-2.0 license.
