#!/usr/bin/env sh
set -e

modpack=${1:-modpack}

version() { sed -n 's/\s*"version_number":\s*"\(.*\)".*/\1/p' "$modpack/manifest.json"; }

old=$(version)

case "$2" in
    "major")
        perl -pi -e 's/(\"version_number\": \")(\d+)\.(\d+)\.(\d+)/$1.join(".", $2+1, 0, 0)/ge' "$modpack/manifest.json"
        ;;
    "minor")
        perl -pi -e 's/(\"version_number\": \")(\d+)\.(\d+)\.(\d+)/$1.join(".", $2, $3+1, 0)/ge' "$modpack/manifest.json"
        ;;
    "patch"|"")
        perl -pi -e 's/(\"version_number\": \")(\d+)\.(\d+)\.(\d+)/$1.join(".", $2, $3, $4+1)/ge' "$modpack/manifest.json"
        ;;
    *)
        echo "Usage: $0 MODPACK_DIR [major|minor|patch] (default: patch)" >&2;
        exit 1
        ;;
esac

echo "$old -> $(version)"

arc="$(basename "$modpack").zip"

rm "$arc" || true
cd "$modpack"
apack "../$arc" ./*
