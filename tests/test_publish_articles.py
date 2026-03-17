from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from scripts.publish_articles import (
    ValidationError,
    build_qiita_payload,
    list_all_documents,
    list_publish_documents,
    load_document,
    select_documents,
)


class PublishArticlesTest(unittest.TestCase):
    def write_markdown(self, root: Path, relative_path: str, contents: str) -> Path:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        return path

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

    def test_list_all_documents_includes_draft_and_publish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            draft_path = self.write_markdown(
                repo_root,
                "blogs/draft/example/qiita.md",
                """---
title: Draft Example
tags:
  - python
private: false
tweet: false
slide: false
item_id:
---

body
""",
            )
            publish_path = self.write_markdown(
                repo_root,
                "blogs/publish/example/qiita.md",
                """---
title: Publish Example
tags:
  - python
private: false
tweet: false
slide: false
item_id:
---

body
""",
            )

            documents = list_all_documents(repo_root)

            self.assertEqual(documents, [draft_path.resolve(), publish_path.resolve()])

    def test_list_publish_documents_excludes_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            self.write_markdown(
                repo_root,
                "blogs/draft/example/qiita.md",
                """---
title: Draft Example
tags:
  - python
private: false
tweet: false
slide: false
item_id:
---

body
""",
            )
            publish_path = self.write_markdown(
                repo_root,
                "blogs/publish/example/qiita.md",
                """---
title: Publish Example
tags:
  - python
private: false
tweet: false
slide: false
item_id:
---

body
""",
            )

            documents = list_publish_documents(repo_root)

            self.assertEqual(documents, [publish_path.resolve()])

    def test_select_documents_rejects_draft_path_for_publish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            self.write_markdown(
                repo_root,
                "blogs/draft/example/qiita.md",
                """---
title: Draft Example
tags:
  - python
private: false
tweet: false
slide: false
item_id:
---

body
""",
            )

            args = argparse.Namespace(
                command="publish",
                path=["blogs/draft/example/qiita.md"],
                all=False,
                base_sha=None,
                head_sha="HEAD",
                repo_root=repo_root,
            )

            with self.assertRaises(ValidationError):
                select_documents(args)

    def test_select_documents_validate_defaults_to_publish_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            publish_path = self.write_markdown(
                repo_root,
                "blogs/publish/example/qiita.md",
                """---
title: Publish Example
tags:
  - python
private: false
tweet: false
slide: false
item_id:
---

body
""",
            )
            self.write_markdown(
                repo_root,
                "blogs/draft/example/qiita.md",
                """---
title: Draft Example
tags:
  - python
private: false
tweet: false
slide: false
item_id:
---

body
""",
            )

            args = argparse.Namespace(
                command="validate",
                path=[],
                all=False,
                repo_root=repo_root,
            )

            self.assertEqual(select_documents(args), [publish_path.resolve()])


if __name__ == "__main__":
    unittest.main()
