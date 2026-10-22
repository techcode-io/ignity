#!/bin/sh
# For user scripts with a #!/bin/execlineb shebang, unless another execline provides one
if [ ! -e /bin/execlineb ] && [ ! -L /bin/execlineb ]; then
  ln -s /usr/lib/ignity/bin/execlineb /bin/execlineb
fi
