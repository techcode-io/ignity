# Base image
FROM {{DOCKER_BASE_IMAGE}}

# Install ignity
COPY src/ /
RUN bash /usr/src/install-ignity.sh
COPY tests/fixtures/capabilities/rootfs/ /

# /data/sub already belongs to another uid and can't be entered by anyone else: fix-perms
# can only fix what is inside with CAP_DAC_OVERRIDE
RUN mkdir -p /data/sub \
 && touch /data/file /data/sub/inner \
 && chmod 644 /data/file /data/sub/inner \
 && chmod 755 /data \
 && chown -R 1234:1234 /data/sub \
 && chmod 700 /data/sub
