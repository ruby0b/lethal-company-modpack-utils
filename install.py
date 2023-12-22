#!/usr/bin/env python3
# This script is used to manually install a Lethal Company modpack without a mod manager.
# It is not recommended to use this if r2modman is working for you.

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
from dataclasses import dataclass

OK = "\033[92m"  # GREEN
WARNING = "\033[93m"  # YELLOW
FAIL = "\033[91m"  # RED
ENDC = "\033[0m"  # RESET COLOR
BOLD = "\033[1m"

MOD_FOLDERS = ["plugins", "config", "patchers", "core"]
MOD_FOLDERS_NO_DELETE = ["config", "core"]
PLUGIN_SUBFOLDERS = ["MirrorDecor"]
SKIP_FILES = ["README.md", "LICENSE", "manifest.json", "CHANGELOG.md", "icon.png"]
# CONFIG_ALLOWLIST = ["BepInEx.cfg"]


def main():
    parser = argparse.ArgumentParser(
        description="Manually install a Lethal Company modpack from thunderstore.io"
    )
    parser.add_argument(
        "modpack",
        help="Modpack string (author-name-version). Use 'latest' as the version to automatically fetch the latest version.",
        type=str,
    )
    parser.add_argument(
        "--game_dir",
        "-d",
        help="Path to the Lethal Company game files directory",
        type=Path,
        default=Path.home()
        / ".local"
        / "share"
        / "Steam"
        / "steamapps"
        / "common"
        / "Lethal Company",
    )

    args = parser.parse_args()

    game_dir: Path = args.game_dir.resolve()

    if not game_dir.exists():
        print(f"{FAIL}Game directory does not exist: {game_dir}{ENDC}")
        exit(1)

    if not (game_dir / "BepInEx").exists():
        print(
            f"{FAIL}BepInEx folder does not exist in game directory: {game_dir}{ENDC}"
        )
        exit(1)

    print("Deleting old mod files...")
    for item in (game_dir / "BepInEx").iterdir():
        if (
            item.is_dir()
            and item.name in MOD_FOLDERS
            and item.name not in MOD_FOLDERS_NO_DELETE
        ):
            shutil.rmtree(item)

    for folder in MOD_FOLDERS:
        (game_dir / "BepInEx" / folder).mkdir(exist_ok=True)

    modpack = Mod.parse(args.modpack)
    if modpack.version == "latest":
        modpack.version = latest_version(modpack)

    manifest = install_mod(modpack, game_dir=game_dir, manifest=True)
    print(f"{BOLD}Installing {len(manifest['dependencies'])} mods:{ENDC}")

    for mod in manifest["dependencies"]:
        install_mod(Mod.parse(mod), game_dir=game_dir)

    print(
        f"{OK}Modpack {BOLD}v{modpack.version}{ENDC}{OK} installed successfully!{ENDC} ({len(manifest['dependencies'])} mods)"
    )


@dataclass
class Mod:
    author: str
    name: str
    version: str

    @staticmethod
    def parse(mod: str):
        try:
            author, name, version = mod.split("-")
        except ValueError:
            print(f"{FAIL}Invalid mod dependency: {mod}{ENDC}")
            raise
        return Mod(author, name, version)

    def __str__(self):
        return f"{self.author}-{self.name}-{self.version}"


def latest_version(mod: Mod, game="lethal-company"):
    print(f"📡 Checking latest version of {mod.author}-{mod.name}")

    url = f"https://thunderstore.io/c/{game}/p/{mod.author}/{mod.name}/"
    response = subprocess.run(
        ["curl", "-L", "--no-progress-meter", url], check=True, capture_output=True
    )
    html = response.stdout.decode("utf-8")
    version = ".".join(html.split(f"{mod.author}-{mod.name}-")[1].split(".")[:3])

    print(f"Latest version is {version}")
    return version


def install_mod(mod: Mod, game_dir: Path, manifest=False):
    if mod.name == "BepInExPack":
        print(f"Skipping BepInExPack...")
        return

    url = f"https://thunderstore.io/package/download/{mod.author}/{mod.name}/{mod.version}"

    print(f"📡 Downloading {mod}")

    with TemporaryDirectory() as temp_dir:
        with working_directory(temp_dir):
            # download the zip
            zip_path = Path("mod.zip")
            subprocess.run(
                ["curl", "-L", "--no-progress-meter", "-o", zip_path, url], check=True
            )

            # extract the zip
            content_dir = Path("mod/").resolve()
            shutil.unpack_archive(zip_path, extract_dir=content_dir)
            os.chdir(content_dir)

            # mod folders may be in the root of the zip, or in the BepInEx folder
            for item in content_dir.iterdir():
                if item.is_dir() and item.name.lower() == "bepinex":
                    os.chdir(item)
                    break

            for item in Path.cwd().iterdir():
                if item.name in SKIP_FILES:
                    continue
                is_dll = item.is_file() and item.suffix == ".dll"
                is_plugin_subfolder = item.is_dir() and item.name in PLUGIN_SUBFOLDERS
                if is_dll or is_plugin_subfolder:
                    target = game_dir / "BepInEx" / "plugins" / item.name
                    subprocess.run(["cp", "-r", item, target], check=True)
                elif item.is_dir() and item.name in MOD_FOLDERS:
                    for file in item.iterdir():
                        if item.name == "config":
                            print(f"📝 {file.name}")
                        target = game_dir / "BepInEx" / item.name / file.name
                        subprocess.run(["cp", "-r", file, target], check=True)
                else:
                    print(
                        f"{WARNING}{BOLD}WARNING - Skipping unknown file/folder: {item.name}{ENDC}"
                    )

            if manifest and (content_dir / "manifest.json").exists():
                with open(content_dir / "manifest.json") as f:
                    return json.load(f)


@contextmanager
def working_directory(directory):
    owd = os.getcwd()
    try:
        os.chdir(directory)
        yield directory
    finally:
        os.chdir(owd)


if __name__ == "__main__":
    main()