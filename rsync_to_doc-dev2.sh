#!/usr/bin/env bash
set -xeuo pipefail # failfast and be verbose


# Copy the current git repo to the container,

container="incus_doc-dev2"
incusdev rsync_to_container $container delete
