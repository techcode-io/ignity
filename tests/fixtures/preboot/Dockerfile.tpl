# Base image
FROM {{DOCKER_BASE_IMAGE}}

# Install ignity
COPY src/ /
RUN bash /usr/src/install-ignity.sh

ENV \
  USERMAP_UID="1000" \
  USERMAP_GID="1000" \
  USER="exploit"
RUN preboot
USER ${USERMAP_UID}:${USERMAP_GID}
