# katana-blogs

`katana-blogs` は、ローカルで Markdown を書き、必要に応じて AI エージェントで編集し、GitHub に push したら Qiita / Zenn へ投稿できるようにした記事投稿用リポジトリです。各サービスへ手で入稿する手間を減らすための運用パッケージとして使います。

このリポジトリは Katana シリーズ専用の発信基盤ではありません。名前は `katana-blogs` ですが、実態は Markdown 執筆から投稿までの一連の流れをまとめた汎用基盤です。

## Overview

- Qiita の下書きは `blogs/draft/` で管理し、投稿対象だけを `blogs/publish/` に置きます。
- Zenn の下書きも同様に、同じ階層内で `zenn.md` として管理します。
- Qiita の場合 Github Actions の workflow が API 連携し、初回 `item_id` を自動マージします。
- Zenn の場合 workflow が自動的に `articles/` フォルダへコピー・同期し、Zenn公式の GitHub 連携により公開されます。

## Directory Layout

```text
.
├── .github/workflows/publish.yml
├── articles/
│   └── (CI/CDによって生成されたマークダウンがコピーされます)
├── blogs/
│   ├── draft/
│   │   └── <article-slug>/
│   │       ├── qiita.md
│   │       └── zenn.md
│   └── publish/
│       └── <article-slug>/
│           ├── qiita.md
│           └── zenn.md
├── infra/github/
│   ├── README.md
│   ├── main.tf
│   ├── terraform.tfvars.example
│   └── variables.tf
├── requirements.txt
├── scripts/publish_articles.py
└── tests/test_publish_articles.py
```

## Article Format

各記事は Qiita 用が `blogs/{draft,publish}/<article>/qiita.md` に、Zenn 用が `blogs/{draft,publish}/<article>/zenn.md` に配置します。メタデータは frontmatter で持ちます。

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

### `blogs/publish/<article>/zenn.md`

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

初回セットアップは `infra/github/` 配下にて Terraform を使い、GitHub Repository Secrets（Qiita用トークンなど）を登録します。

1. GitHub に `katana-blogs` を作成する
2. Zenn ダッシュボードで本リポジトリの GitHub 連携を有効にする
3. `infra/github/terraform.tfvars.example` を `infra/github/terraform.tfvars` にコピーし、`qiita_access_token` などを設定する
4. `infra/github` ディレクトリ内で `terraform init`, `terraform apply` を実行し、GitHub repository secrets に反映する
5. `master` ブランチへ `github-actions[bot]` が push できるようにしておく

接続情報の詳細は [infra/github/README.md](infra/github/README.md) を参照してください。

## Operation Flow

### 執筆と投稿の流れ (Qiita / Zenn 共通)

1. `blogs/draft/<article>/` ディレクトリを作り、その下で `qiita.md` や `zenn.md` を執筆します。
2. 投稿したくなったら、対象ディレクトリごと `blogs/publish/<article>/` に移動またはコピーします。
3. `master` に push します。
4. GitHub Actions (CI) が `blogs/publish/` 配下の変更を検知して処理を開始します。
   - **Qiita:** Qiita API で記事を投稿・更新し、発行された `item_id` を元のマークダウンに書き込みます。
   - **Zenn:** `articles/<article>.md` へファイルを自動コピーします。
5. workflow が自動で更新されたフロントマターや `articles/` のファイルを repository へ commit / push します。
6. (Zennのみ) 自動コミットされた `articles/` の差分を Zenn 側の GitHub 連携が検知し、Zenn サイト側へ即座に同期されます。

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

## Notes

- `blogs/draft/` 配下は workflow の投稿対象外です
- Qiita は `item_id` が空なら新規作成、値があれば更新します
- Zenn は `zenn-cli` による GitHub 連携を行なっているため、`articles/` 下の変更がそのまま同期対象となります
- Zenn は公式の連携を用いているため、当リポジトリの `scripts/` には依存しません
- Qiita だけ、Zenn だけの運用にも対応します
