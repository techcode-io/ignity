#!/usr/bin/env bash
#
# Build the ignity bundle: a rootfs with ignity and a static (musl) build of skalibs, execline, s6
# and s6-portable-utils, packaged by nfpm (see distributions/packages).
#
# Usage: build-ignity.sh <output_dir>
# Runs inside an alpine container with the repository as working directory (see scripts/tasks/build.py).

# Bash strict mode
set -eo pipefail

# Generate stacktrace on error
function runtime::stacktrace {
  local exit_code=$?
  echo >&2 "$0: Error on line '${LINENO}': ${BASH_COMMAND}"
  exit ${exit_code}
}
trap runtime::stacktrace ERR

# Versions and urls are read from the source install, its single source of truth
readonly INSTALL_SCRIPT="src/usr/src/install-ignity.sh"
readonly OUTPUT_DIR="${1:?usage: build-ignity.sh <output_dir>}"
readonly BUILD_DIR="/tmp/build"
# Same layout as the source install: out of the root filesystem, /init puts it first in PATH
readonly IGNITY_LIB_DIR="/usr/lib/ignity"

#######################################
# Log a failure.
# Arguments:
#   ${*}: Any texts.
# Outputs:
#   Log a message as failure.
#######################################
function log::failure {
  echo -e "Failed to ${*}" >&2
}

#######################################
# Log a success.
# Arguments:
#   ${*}: Any texts.
# Outputs:
#   Log a message as success.
#######################################
function log::success {
  echo -e "Succeeded to ${*}"
}

#######################################
# Try to run a command with arguments.
# Arguments:
#   $1: Suffix for log success or error.
#   ${@:2}: Any arguments.
# Returns:
#   Exit status of the command executed.
#######################################
function runtime::try {
  local status=0
  "${@:2}" || status=$?
  if [ ${status} -eq 0 ]; then
    log::success "${1}"
  else
    log::failure "${1}"
    exit ${status}
  fi
}

#######################################
# Read a readonly variable from the source install.
# Arguments:
#   $1: Variable name.
# Outputs:
#   Variable value.
#######################################
function install::get {
  sed -n "s/^readonly ${1}=\"\(.*\)\"$/\1/p" "${INSTALL_SCRIPT}"
}

#######################################
# Compile a skarnet package and install it in the container, for the next packages to build against.
# Arguments:
#   $1: Package name.
#   $2: Package version.
#   $3: Git url.
#   $4: Extra install root, empty for none.
#   ${@:5}: Configure arguments.
#######################################
function pkg::install {
  (
    runtime::try "clone ${1} v${2}" git clone -q -b "v${2}" --depth 1 "${3}" "${BUILD_DIR}/${1}"
    cd "${BUILD_DIR}/${1}"
    runtime::try "configure ${1} v${2}" ./configure "${@:5}"
    runtime::try "compile ${1} v${2}" make
    runtime::try "install ${1} v${2}" make install
    if [ -n "${4}" ]; then
      runtime::try "install ${1} v${2} in ${4}" make DESTDIR="${4}" install
    fi
  )
}

# Build dependencies
apk add --no-cache -q build-base git

rm -rf "${OUTPUT_DIR}" "${BUILD_DIR}"
mkdir -p "${OUTPUT_DIR}" "${BUILD_DIR}"
OUTPUT_ROOT="$(cd "${OUTPUT_DIR}" && pwd)"

# skalibs is only needed at build time: it goes in the throwaway container, not in the bundle
pkg::install "skalibs" "$(install::get SKALIBS_VERSION)" "$(install::get SKALIBS_URL)" "" \
  --disable-shared
readonly CONFIGURE=(
  --enable-static-libc --enable-absolute-paths
  --bindir="${IGNITY_LIB_DIR}/bin" --libexecdir="${IGNITY_LIB_DIR}/libexec"
)
pkg::install "execline" "$(install::get EXECLINE_VERSION)" "$(install::get EXECLINE_URL)" "${OUTPUT_ROOT}" \
  "${CONFIGURE[@]}"
pkg::install "s6" "$(install::get S6_VERSION)" "$(install::get S6_URL)" "${OUTPUT_ROOT}" \
  "${CONFIGURE[@]}"
pkg::install "s6-portable-utils" "$(install::get S6_PORTABLE_UTILS_VERSION)" "$(install::get S6_PORTABLE_UTILS_URL)" "${OUTPUT_ROOT}" \
  "${CONFIGURE[@]}"

# Only binaries are shipped: drop headers and static libraries
rm -rf "${OUTPUT_ROOT}/usr/include" "${OUTPUT_ROOT}"/usr/lib/*.a
runtime::try "strip binaries" strip "${OUTPUT_ROOT}${IGNITY_LIB_DIR}"/bin/* "${OUTPUT_ROOT}${IGNITY_LIB_DIR}"/libexec/*

# Every binary must be static, the bundle runs on any distribution
for bin in "${OUTPUT_ROOT}${IGNITY_LIB_DIR}"/bin/* "${OUTPUT_ROOT}${IGNITY_LIB_DIR}"/libexec/*; do
  if [ -n "$(readelf -l "${bin}" | grep INTERP || true)" ]; then
    log::failure "check ${bin} is static"
    exit 1
  fi
done
log::success "check binaries are static"

# Ignity itself, without the source install
cp -a src/. "${OUTPUT_ROOT}/"
rm -rf "${OUTPUT_ROOT}/usr/src" "${OUTPUT_ROOT}/run"
