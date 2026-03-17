---
title: "Katana シリーズの記事を GitHub Actions から自動投稿する基盤を作った"
emoji: "⚔️"
type: "tech"
topics: ["github-actions", "qiita", "zenn", "python"]
published: true
---

# Katana を継続的に発信するための基盤

Katana は、現実世界のあらゆる不便を切り開いていくプロジェクトです。

アイデアや試作を一度きりで終わらせず、実装と学びを継続的に公開していくために、Qiita と Zenn へ同時に記事を届ける仕組みを整えました。

## 何を作ったか

このリポジトリでは、記事ごとに `blogs/<article>/qiita.md` と `articles/<article>.md` を持ちます。ローカルで Markdown を編集し、`master` ブランチに push すると GitHub Actions が変更された記事だけを判定して投稿します。

Qiita には公式 API を使い、Zenn は `zenn-cli` による GitHub 連携を活用します。初回投稿で発行された `item_id` は Qiita 用の frontmatter に自動反映されるので、2 回目以降は同じ記事を更新できます。Zenn は GitHub 連携により自動的に同期されます。

## この構成にした理由

- 記事ごとの差分を Git で管理しやすい
- Qiita と Zenn で書き分けたい内容を素直に分離できる
- 接続情報を `infra/github` に集約できる

## Katana のこれから

Katana シリーズは、現実世界で放置されがちな不便を切り開くための実装集です。この基盤もその一部として、学びと改善の履歴を外に出し続けるために使っていきます。
