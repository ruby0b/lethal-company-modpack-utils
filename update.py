#!/usr/bin/env nix-shell
#!nix-shell -i python -p python3 python3Packages.tomlkit
# Updates modpack dependencies

import argparse
from pathlib import Path
import subprocess
import sys
import concurrent.futures
from dataclasses import dataclass
import time

import tomlkit

OK = "\033[92m"  # GREEN
WARNING = "\033[93m"  # YELLOW
FAIL = "\033[91m"  # RED
ENDC = "\033[0m"  # RESET COLOR
BOLD = "\033[1m"


def main():
    game = "lethal-company"

    parser = argparse.ArgumentParser(
        description="Updates Lethal Company modpack dependencies"
    )
    parser.add_argument(
        "toml",
        help="Modpack thunderstore.toml file",
        type=Path,
        nargs="?",
        default=Path("modpack/thunderstore.toml"),
    )

    args = parser.parse_args()
    thunderstore_toml: Path = (
        args.toml if not args.toml.is_dir() else args.toml / "thunderstore.toml"
    )

    if not thunderstore_toml.exists():
        print(f"{FAIL}File not found: {thunderstore_toml}{ENDC}")
        sys.exit(1)

    with thunderstore_toml.open() as f:
        toml = tomlkit.load(f)

    toml_deps = toml["package"]["dependencies"]
    deps = [Mod(*name.split("-"), v) for name, v in toml_deps.items()]

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        latest_versions = list(executor.map(latest_version, deps))

    updates = [(m, v) for m, v in zip(deps, latest_versions) if v != m.version]

    for mod, latest in updates:
        toml_deps[f"{mod.author}-{mod.name}"] = latest
        url = f"https://thunderstore.io/c/{game}/p/{mod.author}/{mod.name}/"
        print(f"{mod.version} -> {OK}{BOLD}{latest}{ENDC}\t{url}")

    if updates and input(f"{BOLD}Update? [Y/n]{ENDC} ").lower() in ["y", ""]:
        with thunderstore_toml.open("w") as f:
            tomlkit.dump(toml, f)
        print(f"{OK}{BOLD}Wrote {thunderstore_toml}{ENDC}")
    else:
        print(f"{BOLD}No updates were made{ENDC}")
        sys.exit(1)


@dataclass
class Mod:
    author: str
    name: str
    version: str | None

    def __str__(self):
        return f"{self.author}-{self.name}-{self.version}"


def latest_version(mod: Mod, game="lethal-company"):
    print(f"📡 Checking latest version of {mod.author}-{mod.name}")

    url = f"https://thunderstore.io/c/{game}/p/{mod.author}/{mod.name}/"
    response = subprocess.run(
        ["curl", "-L", "--no-progress-meter", url], check=True, capture_output=True
    )
    time.sleep(.2) # quick and dirty rate limiting fix
    html = response.stdout.decode("utf-8")
    version = ".".join(html.split(f"{mod.author}-{mod.name}-")[1].split(".")[:3])
    return version


if __name__ == "__main__":
    main()
