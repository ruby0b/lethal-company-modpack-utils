#!/usr/bin/env bash
# Compare the r2modman dependency string list (clipboard) with those of the modpack.

modpack=${1:-modpack}

diff --color=always \
    <(jq <"$modpack/manifest.json" '.dependencies.[]' | cut -c2- | rev | cut -c2- | rev | sort) \
    <(xclip -selection clipboard -o | sort)
