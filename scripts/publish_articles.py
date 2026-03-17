#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

JST = timezone(timedelta(hours=9))
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)
NULL_GIT_SHA = "0" * 40
PLATFORM_BY_FILENAME = {
    "qiita.md": "qiita",
}
DRAFT_ARTICLES_DIR = Path("blogs/draft")
PUBLISH_ARTICLES_DIR = Path("blogs/publish")


class ValidationError(Exception):
    pass


@dataclass
class MarkdownDocument:
    path: Path
    platform: str
    metadata: dict[str, Any]
    body: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate article markdown files under blogs/draft and blogs/publish, "
            "and publish only blogs/publish."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    publish_parser = subparsers.add_parser("publish", help="Publish selected markdown files.")
    publish_parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Relative or absolute path to a markdown file. Repeat for multiple files.",
    )
    publish_parser.add_argument(
        "--all",
        action="store_true",
        help="Publish every supported markdown file under blogs/publish/.",
    )
    publish_parser.add_argument(
        "--base-sha",
        help="Base git SHA used to detect changed files. Omit to require --path or --all.",
    )
    publish_parser.add_argument(
        "--head-sha",
        default="HEAD",
        help="Head git SHA used to detect changed files. Defaults to HEAD.",
    )
    publish_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and print API requests without calling the remote platforms.",
    )
    publish_parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root. Defaults to the current directory.",
    )

    validate_parser = subparsers.add_parser("validate", help="Validate selected markdown files.")
    validate_parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Relative or absolute path to a markdown file. Repeat for multiple files.",
    )
    validate_parser.add_argument(
        "--all",
        action="store_true",
        help="Validate every supported markdown file under blogs/draft/ and blogs/publish/.",
    )
    validate_parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root. Defaults to the current directory.",
    )

    return parser.parse_args()


def normalize_scalar(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def normalize_for_dump(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: normalize_for_dump(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_for_dump(item) for item in value]
    return normalize_scalar(value)


def require_string(metadata: dict[str, Any], key: str) -> str:
    value = normalize_scalar(metadata.get(key))
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{key} must be a non-empty string.")
    return value.strip()


def optional_string(metadata: dict[str, Any], key: str) -> str | None:
    value = normalize_scalar(metadata.get(key))
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{key} must be a non-empty string when provided.")
    return value.strip()


def require_bool(metadata: dict[str, Any], key: str) -> bool:
    value = metadata.get(key)
    if not isinstance(value, bool):
        raise ValidationError(f"{key} must be true or false.")
    return value


def optional_bool(metadata: dict[str, Any], key: str, default: bool = False) -> bool:
    value = metadata.get(key, default)
    if not isinstance(value, bool):
        raise ValidationError(f"{key} must be true or false.")
    return value


def require_list(metadata: dict[str, Any], key: str) -> list[Any]:
    value = metadata.get(key)
    if not isinstance(value, list) or not value:
        raise ValidationError(f"{key} must be a non-empty list.")
    return value


def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(raw)
    if match is None:
        raise ValidationError("Markdown file must start with YAML frontmatter.")

    metadata = yaml.safe_load(match.group(1)) or {}
    if not isinstance(metadata, dict):
        raise ValidationError("Frontmatter must decode to a YAML object.")

    body = match.group(2).strip()
    if not body:
        raise ValidationError("Markdown body must not be empty.")

    return metadata, body


def load_document(path: Path) -> MarkdownDocument:
    platform = PLATFORM_BY_FILENAME.get(path.name)
    if platform is None:
        raise ValidationError(f"Unsupported markdown filename: {path.name}")

    metadata, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    return MarkdownDocument(path=path, platform=platform, metadata=metadata, body=body)


def dump_document(document: MarkdownDocument) -> None:
    metadata = normalize_for_dump(document.metadata)
    rendered_metadata = yaml.safe_dump(
        metadata,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    ).strip()
    rendered = f"---\n{rendered_metadata}\n---\n\n{document.body.rstrip()}\n"
    document.path.write_text(rendered, encoding="utf-8")


def is_supported_markdown_path(path: Path) -> bool:
    return path.name in PLATFORM_BY_FILENAME


def list_documents_under(repo_root: Path, articles_dir: Path) -> list[Path]:
    paths = list((repo_root / articles_dir).glob("**/qiita.md"))
    return sorted({path.resolve() for path in paths})


def list_publish_documents(repo_root: Path) -> list[Path]:
    return list_documents_under(repo_root, PUBLISH_ARTICLES_DIR)


def is_publish_document(repo_root: Path, path: Path) -> bool:
    publish_root = (repo_root / PUBLISH_ARTICLES_DIR).resolve()
    return path.resolve().is_relative_to(publish_root)


def require_publish_documents(repo_root: Path, paths: list[Path]) -> list[Path]:
    invalid_paths = [path for path in paths if not is_publish_document(repo_root, path)]
    if invalid_paths:
        joined = ", ".join(str(path) for path in invalid_paths)
        raise ValidationError(
            "publish command only supports markdown files under blogs/publish/: "
            f"{joined}"
        )
    return paths


def validate_qiita_document(document: MarkdownDocument) -> None:
    require_string(document.metadata, "title")
    tags = require_list(document.metadata, "tags")
    for tag in tags:
        if isinstance(tag, str):
            if not tag.strip():
                raise ValidationError("Qiita tags must not contain empty strings.")
            continue

        if not isinstance(tag, dict):
            raise ValidationError("Qiita tags must be strings or {name, versions} objects.")

        name = normalize_scalar(tag.get("name"))
        versions = tag.get("versions", [])
        if not isinstance(name, str) or not name.strip():
            raise ValidationError("Qiita tag objects require a non-empty name.")
        if not isinstance(versions, list):
            raise ValidationError("Qiita tag versions must be a list.")
        for version in versions:
            if not isinstance(normalize_scalar(version), str):
                raise ValidationError("Qiita tag versions must contain only strings.")

    optional_bool(document.metadata, "private")
    optional_bool(document.metadata, "tweet")
    optional_bool(document.metadata, "slide")
    optional_string(document.metadata, "item_id")


def validate_document(document: MarkdownDocument) -> None:
    if document.platform == "qiita":
        validate_qiita_document(document)
        return

    raise ValidationError(f"Unsupported platform: {document.platform}")


def build_qiita_tags(raw_tags: list[Any]) -> list[dict[str, Any]]:
    tags: list[dict[str, Any]] = []
    for raw_tag in raw_tags:
        if isinstance(raw_tag, str):
            tags.append({"name": raw_tag.strip(), "versions": []})
            continue

        tags.append(
            {
                "name": str(normalize_scalar(raw_tag["name"])).strip(),
                "versions": [
                    str(normalize_scalar(version)).strip()
                    for version in raw_tag.get("versions", [])
                    if str(normalize_scalar(version)).strip()
                ],
            }
        )
    return tags


def build_qiita_payload(document: MarkdownDocument) -> dict[str, Any]:
    metadata = document.metadata
    return {
        "title": require_string(metadata, "title"),
        "body": document.body,
        "tags": build_qiita_tags(require_list(metadata, "tags")),
        "private": optional_bool(metadata, "private"),
        "tweet": optional_bool(metadata, "tweet"),
        "slide": optional_bool(metadata, "slide"),
    }


def request_json(
    url: str,
    method: str,
    payload: dict[str, Any] | None,
    headers: dict[str, str],
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request) as response:
            if response.status == 204:
                return {}
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} returned HTTP {exc.code}: {body}") from exc


def publish_qiita(document: MarkdownDocument, dry_run: bool) -> dict[str, Any]:
    payload = build_qiita_payload(document)
    item_id = optional_string(document.metadata, "item_id")
    method = "PATCH" if item_id else "POST"
    endpoint = "https://qiita.com/api/v2/items"
    if item_id:
        endpoint = f"{endpoint}/{item_id}"

    if dry_run:
        return {
            "path": str(document.path),
            "platform": document.platform,
            "action": "update" if item_id else "create",
            "request": {
                "method": method,
                "url": endpoint,
                "json": payload,
            },
            "frontmatter_updated": False,
        }

    token = os.environ.get("QIITA_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("Environment variable QIITA_ACCESS_TOKEN is not set.")

    result = request_json(
        url=endpoint,
        method=method,
        payload=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    new_item_id = result.get("id")
    frontmatter_updated = False
    if isinstance(new_item_id, str) and new_item_id and new_item_id != item_id:
        document.metadata["item_id"] = new_item_id
        dump_document(document)
        frontmatter_updated = True

    return {
        "path": str(document.path),
        "platform": document.platform,
        "action": "update" if item_id else "create",
        "item_id": new_item_id or item_id,
        "url": result.get("url"),
        "frontmatter_updated": frontmatter_updated,
    }


def publish_document(document: MarkdownDocument, dry_run: bool) -> dict[str, Any]:
    validate_document(document)
    if document.platform == "qiita":
        return publish_qiita(document, dry_run=dry_run)
    raise RuntimeError(f"Unsupported platform: {document.platform}")


def list_all_documents(repo_root: Path) -> list[Path]:
    paths = list_documents_under(repo_root, DRAFT_ARTICLES_DIR)
    paths.extend(list_publish_documents(repo_root))
    return sorted(set(paths))


def resolve_paths(repo_root: Path, raw_paths: list[str]) -> list[Path]:
    resolved: list[Path] = []
    for raw_path in raw_paths:
        candidate = Path(raw_path)
        if not candidate.is_absolute():
            candidate = repo_root / candidate
        resolved.append(candidate.resolve())
    return sorted(set(resolved))


def changed_paths_from_git(repo_root: Path, base_sha: str | None, head_sha: str | None) -> list[Path]:
    if base_sha and base_sha != NULL_GIT_SHA:
        cmd = ["git", "diff", "--name-only", base_sha, head_sha or "HEAD", "--", str(PUBLISH_ARTICLES_DIR)]
    else:
        cmd = ["git", "ls-files", str(PUBLISH_ARTICLES_DIR)]

    result = subprocess.run(
        cmd,
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    paths: list[Path] = []
    for line in result.stdout.splitlines():
        relative_path = Path(line)
        if is_supported_markdown_path(relative_path):
            candidate = (repo_root / relative_path).resolve()
            if candidate.exists():
                paths.append(candidate)
    return sorted(set(paths))


def select_documents(args: argparse.Namespace) -> list[Path]:
    repo_root = args.repo_root.resolve()
    if args.path:
        resolved_paths = resolve_paths(repo_root, args.path)
        if args.command == "publish":
            return require_publish_documents(repo_root, resolved_paths)
        return resolved_paths
    if args.command == "validate":
        if args.all:
            return list_all_documents(repo_root)
        return list_publish_documents(repo_root)
    if args.all:
        return list_publish_documents(repo_root)
    return changed_paths_from_git(repo_root, getattr(args, "base_sha", None), getattr(args, "head_sha", None))


def run_validate(args: argparse.Namespace) -> int:
    documents = [load_document(path) for path in select_documents(args)]
    for document in documents:
        validate_document(document)
    print(json.dumps({"validated": [str(document.path) for document in documents]}, ensure_ascii=False, indent=2))
    return 0


def run_publish(args: argparse.Namespace) -> int:
    paths = select_documents(args)
    if not paths:
        print("No article markdown files selected.", file=sys.stderr)
        return 0

    summaries = []
    for path in paths:
        document = load_document(path)
        summaries.append(publish_document(document, dry_run=args.dry_run))

    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    args = parse_args()
    try:
        if args.command == "validate":
            return run_validate(args)
        if args.command == "publish":
            return run_publish(args)
        raise RuntimeError(f"Unsupported command: {args.command}")
    except (ValidationError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
