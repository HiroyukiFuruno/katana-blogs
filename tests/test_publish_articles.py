from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.publish_articles import (
    build_qiita_payload,
    build_zenn_payload,
    load_document,
    normalize_scheduled_publish_at,
)


class PublishArticlesTest(unittest.TestCase):
    def test_load_document_reads_frontmatter_and_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "qiita.md"
            path.write_text(
                """---
title: Example
tags:
  - python
private: false
tweet: false
slide: false
item_id:
---

# Heading

body
""",
                encoding="utf-8",
            )

            document = load_document(path)

            self.assertEqual(document.platform, "qiita")
            self.assertEqual(document.metadata["title"], "Example")
            self.assertIn("# Heading", document.body)

    def test_build_qiita_payload_supports_string_and_versioned_tags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "qiita.md"
            path.write_text(
                """---
title: Example
tags:
  - python
  - name: github-actions
    versions:
      - v1
private: false
tweet: true
slide: false
item_id:
---

body
""",
                encoding="utf-8",
            )

            payload = build_qiita_payload(load_document(path))

            self.assertEqual(payload["title"], "Example")
            self.assertEqual(payload["tags"][0]["name"], "python")
            self.assertEqual(payload["tags"][1]["versions"], ["v1"])
            self.assertTrue(payload["tweet"])

    def test_build_zenn_payload_normalizes_schedule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "zenn.md"
            path.write_text(
                """---
title: Example
emoji: "⚔️"
type: tech
topics:
  - python
published: true
slug:
scheduled_publish_at: "2026-03-17 09:30"
publication_id:
---

body
""",
                encoding="utf-8",
            )

            payload = build_zenn_payload(load_document(path))

            self.assertEqual(payload["article"]["articleType"], "tech")
            self.assertEqual(
                payload["article"]["scheduledPublishAt"],
                "2026-03-17T09:30:00+09:00",
            )

    def test_normalize_scheduled_publish_at_accepts_iso8601(self) -> None:
        self.assertEqual(
            normalize_scheduled_publish_at("2026-03-17T00:30:00+09:00"),
            "2026-03-17T00:30:00+09:00",
        )


if __name__ == "__main__":
    unittest.main()
