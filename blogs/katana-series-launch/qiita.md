---
title: Katana シリーズの発信基盤を GitHub Actions で自動化した
tags:
  - github-actions
  - qiita
  - python
private: false
tweet: false
slide: false
item_id:
---

# Katana の思想を、継続的に外へ出す

Katana は、現実世界のあらゆる不便を切り開いていくためのプロジェクトです。

思想だけで終わらせず、実装したことを継続して公開するために、このリポジトリでは Qiita と Zenn へ同時に記事を配信できるようにしました。

## 仕組み

- 記事は `blogs/<article>/qiita.md` と `blogs/<article>/zenn.md` に分けて持つ
- ローカルで Markdown を編集して `master` に push すると GitHub Actions が変更を検知する
- Qiita は公式 API で投稿する
- Zenn は非公式 API で投稿する
- 初回投稿で発行された識別子は frontmatter に同期される

## 運用上の利点

- 投稿先ごとの差分を Markdown レベルで管理できる
- リポジトリに記事の履歴が残る
- 変更した記事だけを更新できる

## これから

Katana シリーズでは、現実の不便に対して、小さくても切れ味のある解決策を積み上げていきます。この基盤は、その記録を継続的に届けるための最初の刀です。
