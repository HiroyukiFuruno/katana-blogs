---
title: "サンプル: Qiita に Markdown を投稿する"
tags:
  - github-actions
  - qiita
  - python
private: false
tweet: false
slide: false
item_id:
---

# サンプル記事

このファイルは `katana-blogs` のサンプルです。

## 使い方

- `blogs/draft/` 配下のため、そのままでは workflow の投稿対象になりません
- 実際に投稿する場合は `blogs/publish/<article>/qiita.md` に移動またはコピーして使います
- 初回投稿後は `item_id` が自動で書き戻されます

## メモ

Qiita 用の frontmatter には `title`、`tags`、`private` などを設定します。
