# katana-blogs

`katana-blogs` は、Katana シリーズの思想を発信するための汎用記事投稿リポジトリです。Katana は、現実世界のあらゆる不便を切り開いていくためのプロジェクト群であり、このリポジトリではその実装や考え方を Qiita と Zenn に同時配信します。

ローカルで Markdown を編集し、`master` に push すると GitHub Actions が変更された記事だけを検知して投稿します。Qiita は公式 API、Zenn は非公式 API を使い、初回投稿で発行された `item_id` や `slug` は各 Markdown の frontmatter に自動同期されます。

## Directory Layout

```text
.
├── .github/workflows/publish.yml
├── blogs/
│   └── <article-slug>/
│       ├── qiita.md
│       └── zenn.md
├── infra/github/
│   ├── README.md
│   ├── repository.env
│   └── secrets.example.env
├── requirements.txt
├── scripts/publish_articles.py
└── tests/test_publish_articles.py
```

## Article Format

各記事ディレクトリには `qiita.md` と `zenn.md` だけを置きます。メタデータは frontmatter で持ちます。

### `blogs/<article>/qiita.md`

```md
---
title: 記事タイトル
tags:
  - python
  - github-actions
private: false
tweet: false
slide: false
item_id:
---

# 本文
```

### `blogs/<article>/zenn.md`

```md
---
title: 記事タイトル
emoji: "⚔️"
type: tech
topics:
  - python
  - github-actions
published: true
slug:
scheduled_publish_at:
publication_id:
---

# 本文
```

## GitHub Setup

1. GitHub に `HiroyukiFuruno/katana-blogs` を作成する
2. `infra/github/secrets.example.env` を `infra/github/secrets.env` にコピーして接続情報を入れる
3. `python3 infra/github/sync_secrets.py` で GitHub repository secrets を同期する
4. `master` ブランチに push する

接続情報は [infra/github/README.md](./infra/github/README.md) を参照してください。

## Local Commands

依存インストール:

```bash
python3 -m pip install --requirement requirements.txt
```

全記事の検証:

```bash
python3 scripts/publish_articles.py validate --all
```

変更記事の dry-run:

```bash
python3 scripts/publish_articles.py publish --all --dry-run
```

GitHub Secrets の同期:

```bash
python3 infra/github/sync_secrets.py
```

## Notes

- Qiita は `item_id` が空なら新規作成、値があれば更新します
- Zenn は `slug` が空なら新規作成、値があれば更新します
- Zenn の非公式 API は将来の仕様変更で壊れる可能性があります
