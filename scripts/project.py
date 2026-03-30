#!/usr/bin/env python3
"""
Project: Bump s6 ecosystem package versions in install-ignity.sh.

This module provides version upgrade functionality for s6 ecosystem packages.
Can be run locally or in CI to keep dependencies up-to-date.

Usage:
    from scripts.project import upgrade
    result = upgrade(dry_run=False)
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

# Package definitions: (variable_name, github_repo)
PACKAGES = [
    ("SKALIBS_VERSION", "skarnet/skalibs"),
    ("EXECLINE_VERSION", "skarnet/execline"),
    ("S6_VERSION", "skarnet/s6"),
    ("S6_PORTABLE_UTILS_VERSION", "skarnet/s6-portable-utils"),
]

INSTALL_SCRIPT = Path(__file__).parent.parent / "src/usr/src/install-ignity.sh"


@dataclass
class VersionUpdate:
    package: str
    variable: str
    current: str
    latest: str
    updated: bool = False

    @property
    def has_update(self) -> bool:
        return self.current != self.latest

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "package": self.package,
            "variable": self.variable,
            "current": self.current,
            "latest": self.latest,
            "updated": self.updated,
            "has_update": self.has_update,
        }


def fetch_latest_release(repo: str) -> str | None:
    """Fetch latest release version from GitHub API using tags."""
    url = f"https://api.github.com/repos/{repo}/tags?per_page=1"
    try:
        req = urllib.request.Request(url)
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if isinstance(data, list) and len(data) > 0:
                tag = data[0].get("name", "")
                # Strip 'v' prefix if present
                return tag.lstrip("v") if tag else None
            return None
    except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
        print(f"Error fetching {repo}: {e}", file=sys.stderr)
        return None


def read_current_versions() -> dict[str, str]:
    """Read current versions from install-ignity.sh."""
    if not INSTALL_SCRIPT.exists():
        raise FileNotFoundError(f"{INSTALL_SCRIPT} not found")

    versions = {}
    content = INSTALL_SCRIPT.read_text()

    for var_name, _ in PACKAGES:
        # Match: readonly VARIABLE_NAME="version"
        pattern = rf'readonly {var_name}="([^"]+)"'
        match = re.search(pattern, content)
        if match:
            versions[var_name] = match.group(1)

    return versions


def update_script(updates: list[VersionUpdate]) -> bool:
    """Update install-ignity.sh with new versions. Returns True if changes made."""
    if not any(u.has_update for u in updates):
        return False

    content = INSTALL_SCRIPT.read_text()

    for update in updates:
        if update.has_update:
            # Replace: readonly VAR="old" with readonly VAR="new"
            pattern = rf'(readonly {update.variable}=)"{update.current}"'
            replacement = rf'\1"{update.latest}"'
            content = re.sub(pattern, replacement, content)
            update.updated = True

    INSTALL_SCRIPT.write_text(content)
    return True


def upgrade(dry_run: bool = False) -> dict[str, bool | int | list[dict] | dict]:
    """
    Upgrade s6 ecosystem package versions.

    GitHub API token is automatically read from GITHUB_TOKEN environment variable if available.

    Args:
        dry_run: If True, only check for updates without modifying files

    Returns:
        Dictionary with upgrade results
    """
    print("Checking for s6 ecosystem package updates...", file=sys.stderr)

    # Read current versions
    try:
        current_versions = read_current_versions()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return {"error": str(e), "success": False}

    # Check for updates
    updates = []
    for var_name, repo in PACKAGES:
        current = current_versions.get(var_name)
        if not current:
            print(f"Warning: {var_name} not found in {INSTALL_SCRIPT}", file=sys.stderr)
            continue

        pkg_name = repo.split("/")[1]
        latest = fetch_latest_release(repo)

        if latest:
            update = VersionUpdate(
                package=pkg_name,
                variable=var_name,
                current=current,
                latest=latest,
            )
            updates.append(update)

            if update.has_update:
                status = "✓ Update available"
            else:
                status = "✓ Up-to-date"
            print(f"{status}: {pkg_name} ({current} → {latest})", file=sys.stderr)
        else:
            print(f"✗ Failed to fetch latest version for {pkg_name}", file=sys.stderr)

    # Apply updates if not in dry-run mode
    has_changes = False
    if not dry_run:
        has_changes = update_script(updates)
        if has_changes:
            print(f"\n✓ Updated {INSTALL_SCRIPT}", file=sys.stderr)

    # Build result
    result = {
        "success": True,
        "dry_run": dry_run,
        "has_changes": has_changes,
        "updates": [u.to_dict() for u in updates],
        "updated_count": sum(1 for u in updates if u.updated),
        "available_count": sum(1 for u in updates if u.has_update),
    }

    if not any(u.has_update for u in updates):
        print("\nNo updates available.", file=sys.stderr)
    elif dry_run:
        print(f"\nDry-run: Would update {sum(1 for u in updates if u.has_update)} package(s)", file=sys.stderr)
    else:
        print(f"\nSuccessfully updated {sum(1 for u in updates if u.updated)} package(s)", file=sys.stderr)

    return result