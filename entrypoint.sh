#!/bin/sh
set -e

# If a volume is mounted at /data (Fly.io persistent storage for the SQLite
# DB), its root directory is owned by root until we fix it here -- do that
# once as root, then drop down to the unprivileged appuser for the app itself.
if [ -d /data ]; then
  chown -R appuser:appuser /data
fi

exec gosu appuser "$@"
