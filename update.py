#!/usr/bin/env python3
# Updates modpack dependencies

import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
from dataclasses import dataclass

OK = "\033[92m"  # GREEN
WARNING = "\033[93m"  # YELLOW
FAIL = "\033[91m"  # RED
ENDC = "\033[0m"  # RESET COLOR
BOLD = "\033[1m"


def main():
    parser = argparse.ArgumentParser(
        description="Updates Lethal Company modpack dependencies"
    )
    parser.add_argument(
        "manifest",
        help="Modpack manifest.json file",
        type=Path,
    )

    args = parser.parse_args()
    manifest_path: Path = (
        args.manifest if not args.manifest.is_dir() else args.manifest / "manifest.json"
    )

    with manifest_path.open() as f:
        manifest = json.load(f)

    deps = [Mod.parse(mod) for mod in manifest["dependencies"]]

    new_manifest = copy.deepcopy(manifest)
    for i, mod in enumerate(deps):
        latest = latest_version(mod)
        if latest != mod.version:
            new_manifest["dependencies"][i] = str(Mod(mod.author, mod.name, latest))

    new_deps = [Mod.parse(mod) for mod in new_manifest["dependencies"]]

    any_updates = False
    for old, new in zip(deps, new_deps):
        if old != new:
            print(
                f"{old.author}-{old.name}  {old.version} -> {OK}{BOLD}{new.version}{ENDC}",
            )
            any_updates = True

    if not any_updates:
        print(f"{BOLD}No updates{ENDC}")
        sys.exit(0)

    update = input(f"{BOLD}Update manifest.json? [Y/n]{ENDC} ").lower() in ["y", ""]
    if any_updates and update:
        with manifest_path.open("w") as f:
            json.dump(new_manifest, f, indent=2)
        print(f"{OK}{BOLD}Wrote {manifest_path}{ENDC}")


@dataclass
class Mod:
    author: str
    name: str
    version: str | None

    @staticmethod
    def parse(mod: str):
        parts = mod.split("-")
        if len(parts) == 3:
            return Mod(*parts)
        if len(parts) == 2:
            return Mod(*parts, None)
        print(f"{FAIL}Invalid mod dependency: {mod}{ENDC}")
        sys.exit(1)

    def __str__(self):
        return f"{self.author}-{self.name}-{self.version}"

    @property
    def folder_name(self):
        return f"{self.author}-{self.name}"


def latest_version(mod: Mod, game="lethal-company"):
    print(f"📡 Checking latest version of {mod.author}-{mod.name}")

    url = f"https://thunderstore.io/c/{game}/p/{mod.author}/{mod.name}/"
    response = subprocess.run(
        ["curl", "-L", "--no-progress-meter", url], check=True, capture_output=True
    )
    html = response.stdout.decode("utf-8")
    version = ".".join(html.split(f"{mod.author}-{mod.name}-")[1].split(".")[:3])
    return version


if __name__ == "__main__":
    main()
