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
PLUGIN_SUBFOLDERS = ["Modules"]
# idk, the dlls are directly in these so I don't think they're subfolders
PLUGIN_FOLDERS = [
    "Diversity",
    "MirrorDecor",
    "MoreCompanyCosmetics",
    "ToggleMute",
    "UnMaskTheDead",
]
SKIP_FILES = [
    "changelog.md",
    "icon.png",
    "license.md",
    "license.txt",
    "license",
    "manifest.json",
    "readme.md",
]
PLUGIN_SUFFIXES = [
    ".assets",
    ".dll",
    ".lem",
    ".lethalbundle",
    ".mp4",
    ".pdb",
    ".png",
    ".xml",
]
PLUGIN_FILE_NAMES = [
    "assets",
    "gamblingmachinebundle",
    "immersivevisor",
    "yippeesound",
]
CONFIG_ALLOWLIST = ["BepInEx.cfg"]


def main():
    parser = argparse.ArgumentParser(
        description="Manually install a Lethal Company mod(pack)s from thunderstore.io"
    )
    parser.add_argument(
        "mod",
        help="Mod string (author-name-version). Leave out version to use the latest version.",
        type=str,
        nargs="+",
    )
    parser.add_argument(
        "--game-dir",
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
    parser.add_argument(
        "--keep-config",
        help=f"Keep existing config files. By default, config files are deleted (except {', '.join(CONFIG_ALLOWLIST)}).",
        action="store_true",
    )

    args = parser.parse_args()

    keep_config: bool = args.keep_config
    game_dir: Path = args.game_dir.resolve()
    mod_strings: list[str] = args.mod

    # Checks
    if not game_dir.exists():
        print(f"{FAIL}Game directory does not exist: {game_dir}{ENDC}")
        exit(1)
    if not (game_dir / "BepInEx").exists():
        print(
            f"{FAIL}BepInEx folder does not exist in game directory: {game_dir}{ENDC}"
        )
        exit(1)

    # Mod cleanup
    print("Deleting old mod files...")
    for item in (game_dir / "BepInEx").iterdir():
        if (
            item.is_dir()
            and item.name in MOD_FOLDERS
            and item.name not in MOD_FOLDERS_NO_DELETE
        ):
            shutil.rmtree(item)

    # Optional config cleanup
    if not keep_config:
        config_dir = game_dir / "BepInEx" / "config"
        if config_dir.exists():
            print("Deleting old config files...")
            for item in config_dir.iterdir():
                if item.is_file() and item.name not in CONFIG_ALLOWLIST:
                    item.unlink()

    # Make sure all mod folders exist
    for folder in MOD_FOLDERS:
        (game_dir / "BepInEx" / folder).mkdir(exist_ok=True)

    # Install mods
    for mod in map(Mod.parse, mod_strings):
        if mod.version is None or mod.version == "latest":
            mod.version = latest_version(mod)

        manifest = install_mod(mod, game_dir=game_dir, manifest=True)
        deps = manifest["dependencies"]
        if deps:
            print(f"{BOLD}Installing {len(deps)} dependencies:{ENDC}")

            for dependency in manifest["dependencies"]:
                install_mod(Mod.parse(dependency), game_dir=game_dir)

            print(
                f"{OK}{mod.name} {BOLD}v{mod.version}{ENDC}{OK} installed successfully!{ENDC} ({len(deps)} mods)"
            )


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
        exit(1)

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
                if item.name.lower() in SKIP_FILES:
                    continue
                is_plugin_file = item.is_file() and (
                    item.suffix in PLUGIN_SUFFIXES or item.name in PLUGIN_FILE_NAMES
                )
                is_plugin_subfolder = item.is_dir() and item.name in PLUGIN_SUBFOLDERS
                is_plugin_folder = item.is_dir() and item.name in PLUGIN_FOLDERS
                if is_plugin_file or is_plugin_subfolder:
                    plugin_folder = game_dir / "BepInEx" / "plugins" / mod.name
                    plugin_folder.mkdir(exist_ok=True)
                    target = plugin_folder / item.name
                    subprocess.run(["cp", "-r", item, target], check=True)
                elif is_plugin_folder:
                    plugin_folder = game_dir / "BepInEx" / "plugins" / item.name
                    plugin_folder.mkdir(exist_ok=True)
                    subprocess.run(["cp", "-r", item, plugin_folder], check=True)
                elif item.is_dir() and item.name.lower() in MOD_FOLDERS:
                    for file in item.iterdir():
                        if item.name.lower() == "config":
                            print(f"📝 {file.name}")
                        target = game_dir / "BepInEx" / item.name.lower() / file.name
                        subprocess.run(["cp", "-r", file, target], check=True)
                else:
                    item_type = "file" if item.is_file() else "directory"
                    print(
                        f"{WARNING}{BOLD}!!! WARNING - Skipping unknown {item_type}: {item.name}{ENDC}"
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
