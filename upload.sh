#!/usr/bin/env bash
set -e

modpack=$(readlink -f "${1:-modpack}")

[ -d "$modpack" ] || {
    echo "Usage: $0 [MODPACK_DIR] [major|minor|patch] (default: patch)" >&2
    exit 1
}

# bump version
version() { sed -n 's/\s*versionNumber\s*=\s*"\(.*\)".*/\1/p' "$modpack/thunderstore.toml"; }
old=$(version)
case "$2" in
    "major")
        perl -pi -e 's/(versionNumber = \")(\d+)\.(\d+)\.(\d+)/$1.join(".", $2+1, 0, 0)/ge' "$modpack/thunderstore.toml"
        ;;
    "minor")
        perl -pi -e 's/(versionNumber = \")(\d+)\.(\d+)\.(\d+)/$1.join(".", $2, $3+1, 0)/ge' "$modpack/thunderstore.toml"
        ;;
    "patch"|"")
        perl -pi -e 's/(versionNumber = \")(\d+)\.(\d+)\.(\d+)/$1.join(".", $2, $3, $4+1)/ge' "$modpack/thunderstore.toml"
        ;;
    *)
        echo "Usage: $0 MODPACK_DIR [major|minor|patch] (default: patch)" >&2;
        exit 1
        ;;
esac
echo "> Bumping version: $old -> $(version)"

# load TCLI_AUTH_TOKEN from modpack .env
set -o allexport
source "$modpack/.env"
set +o allexport

echo "> Downloading the latest thunderstore-cli..."

# make temp dir for executable
tmp=$(mktemp -d -t tcli-XXXXXXXXXX)
trap 'rm -rf $tmp' EXIT
cd "$tmp"

# get the latest release tag
git clone -q https://github.com/thunderstore-io/thunderstore-cli
cd thunderstore-cli
tag=$(git describe --tags --abbrev=0)
cd ..

# download the release
curl -sSL \
    -o tcli.tar.gz \
    "https://github.com/thunderstore-io/thunderstore-cli/releases/download/$tag/tcli-$tag-linux-x64.tar.gz"
tar xzf tcli.tar.gz
bin=$(readlink -f "tcli-$tag-linux-x64/tcli")

# publish
echo "> Publishing to Thunderstore..."
cd "$modpack"
"$bin" publish
