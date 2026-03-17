# katana-blogs

`katana-blogs` は、ローカルで Markdown を書き、必要に応じて AI エージェントで編集し、GitHub に push したら Qiita / Zenn へ投稿できるようにした記事投稿用リポジトリです。各サービスへ手で入稿する手間を減らすための運用パッケージとして使います。

このリポジトリは Katana シリーズ専用の発信基盤ではありません。名前は `katana-blogs` ですが、実態は Markdown 執筆から投稿までの一連の流れをまとめた汎用基盤です。

## Overview

- Qiita の下書きは `blogs/draft/` で管理し、投稿対象だけを `blogs/publish/` に置きます。
- Zenn は `zenn-cli` を使って `articles/` 配下で管理します（`published: false` で下書き）。
- Qiita は Github Actions の workflow が `blogs/publish/**` の変更を検知して自動投稿します。
- Zenn は `zenn-cli` による GitHub 連携を活用し、`master` への push ごとに自動同期されます。
- 初回投稿で発行された Qiita の `item_id` は `blogs/publish/` 側の frontmatter に自動反映されます。
- workflow が frontmatter の更新差分を commit / push するため、投稿済み状態をリポジトリ内で自己管理できます。

## Directory Layout

```text
.
├── .github/workflows/publish.yml
├── articles/
│   └── <article-slug>.md
├── blogs/
│   ├── draft/
│   │   └── <article-slug>/
│   │       └── qiita.md
│   └── publish/
│       └── <article-slug>/
│           └── qiita.md
├── infra/github/
│   ├── README.md
│   ├── repository.env
│   ├── secrets.example.env
│   └── sync_secrets.py
├── requirements.txt
├── scripts/publish_articles.py
└── tests/test_publish_articles.py
```

## Article Format

各記事は Qiita 用が `blogs/draft/<article>/qiita.md`（投稿時は `blogs/publish/`）に、Zenn 用が `articles/<article>.md` に配置します。メタデータは frontmatter で持ちます。

### `blogs/publish/<article>/qiita.md`

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

### `articles/<article>.md`

```md
---
title: "記事タイトル"
emoji: "⚔️"
type: "tech"
topics: ["python", "github-actions"]
published: true
---

# 本文
```

## Prerequisites

- **Zenn GitHub 連携**: [Zenn のダッシュボード](https://zenn.dev/dashboard/deploys) で「GitHub からのデプロイ」を有効にし、本リポジトリ (`katana-blogs`) の `master` ブランチを連携する。これにより `articles/` 下の記事が push のたびに自動同期される

## Initial Setup

初回セットアップは `infra/github/` 配下の情報を埋めて、GitHub 側へ接続情報を登録します。

1. GitHub に `katana-blogs` を作成する
2. Zenn ダッシュボードで本リポジトリの GitHub 連携を有効にする
3. `infra/github/secrets.example.env` を `infra/github/secrets.env` にコピーし、`QIITA_ACCESS_TOKEN` を設定する
4. `gh auth login` 済みの環境で `python3 infra/github/sync_secrets.py` を実行し、GitHub repository secrets に反映する
5. `master` ブランチへ `github-actions[bot]` が push できるようにしておく

接続情報の詳細は [infra/github/README.md](infra/github/README.md) を参照してください。

## Operation Flow

### Qiita

1. `blogs/draft/<article>/` に記事を書く
2. 投稿したくなったら `blogs/publish/<article>/` に移動またはコピーする
3. `master` に push する
4. GitHub Actions が `blogs/publish/` 配下の変更だけを検知して投稿する
5. 初回投稿で発行された `item_id` を workflow が Markdown に書き戻して commit / push する

### Zenn

1. `npx zenn new:article` または `articles/` 配下に手動でファイルを作成する
2. `published: false` （下書き）としてプレビュー (`npx zenn preview`) しながら執筆する
3. 投稿したくなったら `published: true` に変更する
4. `master` に push する
5. Zenn GitHub アプリが自動で同期・投稿する

## Local Commands

依存インストール:

```bash
python3 -m pip install --requirement requirements.txt
npm install
```

Zenn ローカルプレビュー:

```bash
npx zenn preview
```

Qiita (draft / publish) をまとめて検証:

```bash
python3 scripts/publish_articles.py validate --all
```

Qiita (publish 対象だけ) を dry-run:

```bash
python3 scripts/publish_articles.py publish --all --dry-run
```

GitHub Secrets の同期:

```bash
python3 infra/github/sync_secrets.py
```

## Notes

- `blogs/draft/` 配下は workflow の投稿対象外です
- Qiita は `item_id` が空なら新規作成、値があれば更新します
- Zenn は `zenn-cli` による GitHub 連携を行なっているため、`articles/` 下の変更がそのまま同期対象となります
- Zenn は公式の連携を用いているため、当リポジトリの `scripts/` には依存しません
- Qiita だけ、Zenn だけの運用にも対応します
