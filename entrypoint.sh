#!/bin/sh
set -e

# compose.yaml bind-mounts the host's ./src into /app/src, which brings in
# the host's ownership (not the container's appuser) -- fix it here as root,
# then drop down to the unprivileged appuser for the app itself.
chown -R appuser:appuser /app/src

exec gosu appuser "$@"
