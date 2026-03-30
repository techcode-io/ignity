#!/usr/bin/env bash

# Bash strict mode
set -eo pipefail

# Generate stacktrace on error
function runtime::stacktrace {
  local exit_code=$?
  echo >&2 "$0: Error on line '${LINENO}': ${BASH_COMMAND}"
  exit ${exit_code}
}
trap runtime::stacktrace ERR

# Variables environments
readonly SKALIBS_URL="https://github.com/skarnet/skalibs.git"
readonly EXECLINE_URL="https://github.com/skarnet/execline.git"
readonly S6_URL="https://github.com/skarnet/s6.git"
readonly S6_PORTABLE_UTILS_URL="https://github.com/skarnet/s6-portable-utils.git"
readonly SKALIBS_VERSION="2.14.4.0"
readonly EXECLINE_VERSION="2.9.7.0"
readonly S6_VERSION="2.13.2.0"
readonly S6_PORTABLE_UTILS_VERSION="2.3.1.0"
BUILD_DEPENDENCIES="ca-certificates build-essential git"

# Fine tuning
export DEBIAN_FRONTEND=noninteractive

#######################################
# Log a failure.
# Globals:
#   DISABLE_CONSOLE_COLORS
# Arguments:
#   ${*}: Any texts.
# Outputs:
#   Log a message as failure.
#######################################
function log::failure {
  if [ -z "${DISABLE_CONSOLE_COLORS:-}" ]; then
    echo -e "\033[31m✗\033[0m Failed to ${*}" >&2
  else
    echo -e "Failed to ${*}" >&2
  fi
}

#######################################
# Log a success.
# Globals:
#   DISABLE_CONSOLE_COLORS
# Arguments:
#   ${*}: Any texts.
# Outputs:
#   Log a message as success.
#######################################
function log::success {
  if [ -z "${DISABLE_CONSOLE_COLORS:-}" ]; then
    echo -e "\033[32m✓\033[0m Succeeded to ${*}"
  else
    echo -e "Succeeded to ${*}"
  fi
}


#######################################
# Execute a command with arguments.
# Globals:
#   SILENT_STDOUT
#   SILENT_STDERR
# Arguments:
#   ${@}: Any arguments.
# Returns:
#   Exit status of the command executed.
#######################################
function runtime::exec {
  local err_exit_ctx; err_exit_ctx=$(shopt -o errexit || true)

  set +e
  if [ -z "${SILENT_STDOUT:-}" ] && [ -z "${SILENT_STDERR:-}" ]; then
    "${@}"
  elif [ -n "${SILENT_STDOUT:-}" ] && [ -n "${SILENT_STDERR:-}" ]; then
    "${@}" &> /dev/null
  elif [ -z "${SILENT_STDOUT:-}" ] && [ -n "${SILENT_STDERR:-}" ]; then
    "${@}" 2> /dev/null
  else
    "${@}" > /dev/null
  fi
  local status=$?
  if echo "${err_exit_ctx}" | grep -q "on"; then
    set -e
  fi
  return ${status}
}

#######################################
# Try to run a command with arguments.
# Globals:
#   SILENT_STDOUT
#   CATCH_ERROR
# Arguments:
#   $1: Suffix for log success or error.
#   ${@:2}: Any arguments.
# Returns:
#   Exit status of the command executed.
#######################################
function runtime::try {
  # shellcheck disable=SC2068
  runtime::exec ${@:2}
  local status=$?
  if [ ${status} -eq 0 ]; then
    log::success "${1}"
  else
    log::failure "${1}"
    if [ -n "${CATCH_ERROR:-}" ]; then
      return 0
    else
      exit ${status}
    fi
  fi
  return ${status}
}

#######################################
# Retrieve an environment variable or return default value.
# Arguments:
#   ${1}: Environment variable to get.
#   ${2}: Default value.
# Outputs:
#   Environment variable value or default value.
#######################################
function env::get_or_default {
  local var; var=$(printf '%s\n' "${!1}")
  if [ -z "${var}" ]; then
    echo -e "${2}"
  else
    echo -e "${var}"
  fi
}

#######################################
# Retrieve an environment variable or return empty value.
# Arguments:
#   ${1}: Environment variable to get.
# Outputs:
#   Environment variable value or empty value.
#######################################
function env::get_or_empty {
  env::get_or_default "${1}" ""
}

#######################################
# Compile and install dependencies.
# Arguments:
#   ${@}: Any arguments.
# Returns:
#   Exit status of the command executed.
#######################################
function pkg::install {
  (
    runtime::try "clone ${1} v${2}" git clone -q -b "v${2}" --depth 1 "${3}" "/tmp/${1}"
    cd "/tmp/${1}"
    runtime::try "configure ${1} v${2}" ./configure ${4}
    runtime::try "compile ${1} v${2}" make
    runtime::try "install ${1} v${2}" make install
  )
}

# Diff to do iso uninstall after build
dpkg -l | awk '{print $2;}' > /tmp/before

# Install build dependencies
apt-get update > /dev/null
apt-get install --no-install-recommends -y ${BUILD_DEPENDENCIES}

# Shallow clone skalibs, execline, s6, s6-portable-utils
pkg::install "skalibs" "${SKALIBS_VERSION}" "${SKALIBS_URL}" "--enable-shared"
pkg::install "execline" "${EXECLINE_VERSION}" "${EXECLINE_URL}" "--enable-shared"
pkg::install "s6" "${S6_VERSION}" "${S6_URL}"
pkg::install "s6-portable-utils" "${S6_PORTABLE_UTILS_VERSION}" "${S6_PORTABLE_UTILS_URL}"

# Diff to do iso uninstall
dpkg -l | awk '{print $2;}' > /tmp/after
BUILD_DEPENDENCIES=$(diff /tmp/before /tmp/after | grep ">" | awk '{print $2;}')

# Purge build dependencies and cleanup apt
apt-get purge -y --auto-remove ${BUILD_DEPENDENCIES}
apt-get clean && rm -rf /var/lib/apt/lists/* && rm -rf /tmp/*

# Auto remove
rm -f /usr/src/install-ignity.sh
