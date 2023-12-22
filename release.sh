#!/usr/bin/env sh
set -e

version() { sed -n 's/\s*"version_number":\s*"\(.*\)".*/\1/p' modpack/manifest.json; }

old=$(version)

case "$1" in
    "major")
        perl -pi -e 's/(\"version_number\": \")(\d+)\.(\d+)\.(\d+)/$1.join(".", $2+1, 0, 0)/ge' modpack/manifest.json
        ;;
    "minor")
        perl -pi -e 's/(\"version_number\": \")(\d+)\.(\d+)\.(\d+)/$1.join(".", $2, $3+1, 0)/ge' modpack/manifest.json
        ;;
    "patch" | "")
        perl -pi -e 's/(\"version_number\": \")(\d+)\.(\d+)\.(\d+)/$1.join(".", $2, $3, $4+1)/ge' modpack/manifest.json
        ;;
    *)
        echo "Usage: $0 [major|minor|patch] (default: patch)"
        exit 1
esac

echo "$old -> $(version)"

rm modpack.zip || true
cd modpack
apack ../modpack.zip ./*
