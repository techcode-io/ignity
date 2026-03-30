# Base image
FROM {{DOCKER_BASE_IMAGE}}

# Install ignity
COPY src/ /
RUN bash /usr/src/install-ignity.sh
COPY tests/fixtures/envs/rootfs/ /
