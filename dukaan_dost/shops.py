"""
shops.py

The registry of shops: each is a folder under shops/ with a config.yaml
(see shops/README.md). One running agent serves all of them; the call link
(/s/<shop>/) picks which one a call is for (DEC-034).

Shop names end up in file paths and URLs, so they are validated strictly:
lower case letters, digits, "_" and "-", 2 to 40 characters, starting with a
letter or digit. Anything else is rejected before it touches the disk.
"""

import re
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SHOPS_DIR = PROJECT_ROOT / "shops"

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,39}$")


def valid_name(name) -> bool:
    return isinstance(name, str) and bool(NAME_RE.match(name))


def shop_dir(name: str, root: Path | None = None) -> Path:
    if not valid_name(name):
        raise ValueError(f"{name!r} is not a valid shop name")
    return (root or SHOPS_DIR) / name


def exists(name, root: Path | None = None) -> bool:
    return valid_name(name) and (shop_dir(name, root) / "config.yaml").is_file()


def list_shops(root: Path | None = None) -> list:
    base = root or SHOPS_DIR
    if not base.is_dir():
        return []
    return sorted(p.name for p in base.iterdir() if valid_name(p.name) and (p / "config.yaml").is_file())


def display_name(name: str, root: Path | None = None) -> str:
    """The shop's spoken and shown name: `display_name` in config.yaml, else the folder name in title case."""
    fallback = name.replace("_", " ").replace("-", " ").title()
    if not valid_name(name):
        return fallback
    try:
        config = yaml.safe_load((shop_dir(name, root) / "config.yaml").read_text(encoding="utf-8")) or {}
        shown = config.get("display_name")
        if isinstance(shown, str) and shown.strip():
            return shown.strip()[:60]
    except (OSError, yaml.YAMLError, AttributeError):
        pass
    return fallback
