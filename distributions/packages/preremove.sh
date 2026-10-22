#!/bin/sh
# Keep the link on upgrade: rpm passes the number of versions left (1), deb `upgrade`
case "${1}" in
  1 | upgrade | failed-upgrade) exit 0 ;;
esac
if [ "$(readlink /bin/execlineb)" = /usr/lib/ignity/bin/execlineb ]; then
  rm -f /bin/execlineb
fi
