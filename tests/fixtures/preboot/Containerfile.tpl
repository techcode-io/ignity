# Base image
FROM {{DOCKER_BASE_IMAGE}}

# Install ignity
{{IGNITY_INSTALL}}

ENV \
  USERMAP_UID="1000" \
  USERMAP_GID="1000" \
  USER="exploit"
RUN preboot
USER ${USERMAP_UID}:${USERMAP_GID}
