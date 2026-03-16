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
    "zenn.md": "zenn",
}


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
        description="Validate and publish article markdown files from blogs/*/qiita.md and blogs/*/zenn.md."
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
        help="Publish every supported markdown file under blogs/.",
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
        help="Validate every supported markdown file under blogs/.",
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


def normalize_scheduled_publish_at(raw: Any) -> str | None:
    raw = normalize_scalar(raw)
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise ValidationError("scheduled_publish_at must be a non-empty string when provided.")

    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(raw, fmt).replace(tzinfo=JST)
            return dt.isoformat()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).isoformat()
    except ValueError as exc:
        raise ValidationError(
            "scheduled_publish_at must use ISO8601, YYYY-MM-DD, or YYYY-MM-DD HH:MM."
        ) from exc


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


def validate_zenn_document(document: MarkdownDocument) -> None:
    require_string(document.metadata, "title")
    require_string(document.metadata, "emoji")

    article_type = require_string(document.metadata, "type")
    if article_type not in {"tech", "idea"}:
        raise ValidationError("Zenn type must be either 'tech' or 'idea'.")

    topics = require_list(document.metadata, "topics")
    for topic in topics:
        if not isinstance(normalize_scalar(topic), str) or not str(topic).strip():
            raise ValidationError("Zenn topics must be non-empty strings.")

    require_bool(document.metadata, "published")
    optional_string(document.metadata, "slug")
    normalize_scheduled_publish_at(document.metadata.get("scheduled_publish_at"))

    publication_id = document.metadata.get("publication_id")
    if publication_id is not None and not isinstance(publication_id, int):
        raise ValidationError("publication_id must be an integer when provided.")


def validate_document(document: MarkdownDocument) -> None:
    if document.platform == "qiita":
        validate_qiita_document(document)
        return

    if document.platform == "zenn":
        validate_zenn_document(document)
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


def build_zenn_payload(document: MarkdownDocument) -> dict[str, Any]:
    metadata = document.metadata
    return {
        "article": {
            "title": require_string(metadata, "title"),
            "articleType": require_string(metadata, "type"),
            "emoji": require_string(metadata, "emoji"),
            "bodyMarkdown": document.body,
            "scheduledPublishAt": normalize_scheduled_publish_at(
                metadata.get("scheduled_publish_at")
            ),
            "published": require_bool(metadata, "published"),
            "publicationId": metadata.get("publication_id"),
        },
        "topicNames": [str(normalize_scalar(topic)).strip() for topic in require_list(metadata, "topics")],
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


def extract_slug(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "slug" and isinstance(value, str):
                return value
            found = extract_slug(value)
            if found:
                return found
    if isinstance(payload, list):
        for item in payload:
            found = extract_slug(item)
            if found:
                return found
    return None


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


def publish_zenn(document: MarkdownDocument, dry_run: bool) -> dict[str, Any]:
    payload = build_zenn_payload(document)
    original_slug = optional_string(document.metadata, "slug")
    slug = original_slug
    published = require_bool(document.metadata, "published")

    if dry_run:
        return {
            "path": str(document.path),
            "platform": document.platform,
            "action": "update" if slug else "create",
            "request": {
                "api_base": "https://zenn.dev/api",
                "create": None
                if slug
                else {"method": "POST", "path": "/articles", "json": {"topicNames": payload["topicNames"]}},
                "update": {
                    "method": "PUT",
                    "path": f"/articles/{slug or '{returned_slug}'}",
                    "json": payload,
                },
            },
            "published": published,
            "frontmatter_updated": False,
        }

    cookie = os.environ.get("ZENN_COOKIE")
    if not cookie:
        raise RuntimeError("Environment variable ZENN_COOKIE is not set.")

    create_result = None
    if not slug:
        create_result = request_json(
            url="https://zenn.dev/api/articles",
            method="POST",
            payload={"topicNames": payload["topicNames"]},
            headers={
                "Content-Type": "application/json",
                "Cookie": cookie,
                "User-Agent": "katana-blogs",
            },
        )
        slug = extract_slug(create_result)
        if not slug:
            raise RuntimeError("Could not extract slug from Zenn create response.")

    update_result = request_json(
        url=f"https://zenn.dev/api/articles/{slug}",
        method="PUT",
        payload=payload,
        headers={
            "Content-Type": "application/json",
            "Cookie": cookie,
            "User-Agent": "katana-blogs",
        },
    )

    frontmatter_updated = False
    if slug != document.metadata.get("slug"):
        document.metadata["slug"] = slug
        dump_document(document)
        frontmatter_updated = True

    return {
        "path": str(document.path),
        "platform": document.platform,
        "action": "update" if original_slug else "create",
        "slug": slug,
        "published": published,
        "create_result": create_result,
        "update_result": update_result,
        "frontmatter_updated": frontmatter_updated,
    }


def publish_document(document: MarkdownDocument, dry_run: bool) -> dict[str, Any]:
    validate_document(document)
    if document.platform == "qiita":
        return publish_qiita(document, dry_run=dry_run)
    if document.platform == "zenn":
        return publish_zenn(document, dry_run=dry_run)
    raise RuntimeError(f"Unsupported platform: {document.platform}")


def list_all_documents(repo_root: Path) -> list[Path]:
    paths = list(repo_root.glob("blogs/**/qiita.md"))
    paths.extend(repo_root.glob("blogs/**/zenn.md"))
    return sorted({path.resolve() for path in paths})


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
        cmd = ["git", "diff", "--name-only", base_sha, head_sha or "HEAD", "--", "blogs"]
    else:
        cmd = ["git", "ls-files", "blogs"]

    result = subprocess.run(
        cmd,
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    paths: list[Path] = []
    for line in result.stdout.splitlines():
        if line.endswith("/qiita.md") or line.endswith("/zenn.md"):
            candidate = (repo_root / line).resolve()
            if candidate.exists():
                paths.append(candidate)
    return sorted(set(paths))


def select_documents(args: argparse.Namespace) -> list[Path]:
    repo_root = args.repo_root.resolve()
    if args.path:
        return resolve_paths(repo_root, args.path)
    if args.all or args.command == "validate":
        return list_all_documents(repo_root)
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
