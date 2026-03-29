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

## :package: Prerequisites

- [Taskfile](https://taskfile.dev/) for development.
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
2. `cd ignity && task setup`

### Test

- To test you have to use the workflow script.

```bash
task test
```

- It will test project code with the current environment.

### Package

- To package you have to use the workflow script.

```bash
task package
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
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | --------------- |
| `IGNITY_CMD_WAIT_FOR_SERVICES_MAXTIME` | The maximum time (in milliseconds) the services could take to bring up before proceding to CMD executing              | 5000            |
| `IGNITY_CMD_WAIT_FOR_SERVICES`         | In order to proceed executing CMD overlay will wait until services are up                                             | 0               |
| `IGNITY_KILL_FINALIZE_MAXTIME`         | The maximum time (in milliseconds) a script in `/etc/ignity/finalize` could take before sending a `KILL` signal to it | 5000            |
| `IGNITY_KILL_GRACETIME`                | How long (in milliseconds) `ignity` should wait to reap zombies before sending a `KILL` signal                        | 3000            |
| `IGNITY_SERVICES_GRACETIME`            | How long (in milliseconds) `ignity` should wait services down before sending a down signal                            | 5000            |
| `USER`                                 | User name to map with uid and gid                                                                                     | root            |
| `USERMAP_GID`                          | User gid to map on files                                                                                              | 0               |
| `USERMAP_UID`                          | User uid to map on files                                                                                              | 0               |

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
- It will be run under the s6 supervisor, and when it fails or exits, the container will exit. You can even run interactive programs under the s6 supervisor !

### How to load env files

- Sometimes it's interesting to load env files to define default variables.
- You can simply put any env files in `/etc/ignity/envs` and they will be loaded during runtime in order.
- They will be overrided by container environments variables.

### How to supervise a service

- Creating a supervised service cannot be easier
- Just create a service directory with the name of your service into `/etc/ignity/services`
- Put a `run` file into it, this is the file in which you'll put your long-lived process execution
- You're done! If you want to know more about s6 supervision of servicedirs take a look to [`servicedir`](https://skarnet.org/software/s6/servicedir.html) documentation.

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
- You can delay or disable automatic start by creating a `down` file in the [service directory](https://skarnet.org/software/s6/servicedir.html).
- This file can be created at build time in `/etc/ignity/services/myapp/down`.
- Or at runtime by creating the file in `/run/ignity/services/myapp/down` using init scripts.
- Note that after first services start the service directory is `/run/ignity/services-state` instead of `/run/ignity/services`.
- Then you can start it manually by removing the file in `/run/ignity/services-state/myapp/down` and by calling `s6-svc -u /run/ignity/services-state/myapp`.

### How to execute initialization and/or finalization tasks

- Just before starting user provided services.
- `ignity` will execute in order all scripts present in `/etc/ignity/init`.
- And in parallel of bringing down user provided services.
- `ignity` will execute in order all scripts present in `/etc/ignity/finalize`.
- You can use this mecanism to setup the container or validate everything or clean some resources before container exit.

### How to set container environment variables

- If you want your custom script to have container environments available just make use of `with-env` helper, which will push all of those into your execution environment, for example:

`/etc/ignity/init/01-example`:

```sh
#!/usr/bin/with-env sh
echo $MYENV
```

- This script will output whatever the `MYENV` enviroment variable contains.
- This helper is only here for custom environments variables pushed in `/run/ignity/envs` directory.

### How to run a container with non root user

- To run a container with a non root user, you have to define files and directories permissions in `perms` and then define the following in the Dockerfile

```bash
ENV \
  USERMAP_UID="1000" \
  USERMAP_GID="1000" \
  USER="exploit"
RUN preboot
USER ${USERMAP_UID}:${USERMAP_GID}
```

- This will correct permissions at build time instead of runtime and will let the container start properly with a non root user.

### How to run a container in read-only mode

- To run the container in read-only mode, you will have to mount a tmpfs at `/run/ingity`.
- If you want to run it with a non root user, you will also need to match uid able to write, execute and read on this location.

```yaml
tmpfs:
  - "/run/ignity:exec,mode=1777,uid=<uid>"
```

### How to fix ownership & permissions

- Sometimes it's interesting to fix ownership & permissions before proceeding because, for example, you have mounted/mapped a host folder inside your container.
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

### How to drop privileges

- When it comes to executing a service, no matter it's a service or a logging service, a very good practice is to drop privileges before executing it.
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

- If you want to know more about these utilities, please take a look to: [`s6-setuidgid`](http://skarnet.org/software/s6/s6-setuidgid.html), [`s6-envuidgid`](http://skarnet.org/software/s6/s6-envuidgid.html) and [`s6-applyuidgid`](http://skarnet.org/software/s6/s6-applyuidgid.html).

### How to allow high inheritance

- It's convenient to prefix every scripts in `envs`, `perms`, `init` and `finalize` by number (two chars) to ensure execution order.
- A common pattern is to dedicated 10 number by docker image layer to allow logic evolution.

### How to customize `ignity` behaviour

It is possible somehow to tweak `ignity` behaviour by providing an already predefined set of environment variables to the execution context:

- `IGNITY_CMD_WAIT_FOR_SERVICES_MAXTIME` (default = 5000): The maximum time (in milliseconds) the services could take to bring up before proceding to CMD executing.
- `IGNITY_CMD_WAIT_FOR_SERVICES` (default = 0): In order to proceed executing CMD overlay will wait until services are up. Be aware that up doesn't mean ready. Depending if `notification-fd` was found inside the servicedir overlay will use `s6-svwait -U` or `s6-svwait -u` as the waiting statement.
- `IGNITY_KILL_FINALIZE_MAXTIME` (default = 5000): The maximum time (in milliseconds) a script in `/etc/ignity/finalize` could take before sending a `KILL` signal to it. Take into account that this parameter will be used per each script execution, it's not a max time for the whole set of scripts.
- `IGNITY_KILL_GRACETIME` (default = 3000): How long (in milliseconds) `ignity` should wait to reap zombies before sending a `KILL` signal.
- `IGNITY_SERVICES_GRACETIME` (default = 5000): How long (in milliseconds) `ignity` should wait to reap zombies before sending a down signal.

## :heart: Contributing

If you find this project useful here's how you can help, please click the :eye: **Watch** button to avoid missing
notifications about new versions, and give it a :star2: **GitHub Star**!

You can also contribute by:

- Sending a [Pull Request](https://github.com/techcode-io/ignity/pulls) with your awesome new features and bug fixed.
- Be part of the community and help resolve [Issues](https://github.com/techcode-io/ignity/issues).

## 🧾 License

The `ignity` project is free and open-source software licensed under the Apache-2.0 license.
