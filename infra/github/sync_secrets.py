#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync repository secrets to GitHub from infra/github/secrets.env."
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path("infra/github/secrets.env"),
        help="Path to the local secrets env file.",
    )
    parser.add_argument(
        "--repository-file",
        type=Path,
        default=Path("infra/github/repository.env"),
        help="Path to the repository metadata env file.",
    )
    return parser.parse_args()


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        if not key or not _:
            raise ValueError(f"Invalid env line: {raw_line}")
        values[key.strip()] = value.strip()
    return values


def repository_slug(path: Path) -> str:
    values = parse_env_file(path)
    owner = values.get("GITHUB_OWNER")
    repository = values.get("GITHUB_REPOSITORY")
    if not owner or not repository:
        raise ValueError("repository.env must define GITHUB_OWNER and GITHUB_REPOSITORY.")
    return f"{owner}/{repository}"


def sync_secret(repository: str, name: str, value: str) -> None:
    subprocess.run(
        ["gh", "secret", "set", name, "--repo", repository, "--body", value],
        check=True,
    )


def main() -> int:
    args = parse_args()
    if not args.env_file.exists():
        raise SystemExit(f"Missing env file: {args.env_file}")
    if not args.repository_file.exists():
        raise SystemExit(f"Missing repository file: {args.repository_file}")

    repository = repository_slug(args.repository_file)
    secrets = parse_env_file(args.env_file)
    if not secrets:
        raise SystemExit("No secrets found to sync.")

    for name, value in secrets.items():
        sync_secret(repository, name, value)
        print(f"synced {name} to {repository}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
