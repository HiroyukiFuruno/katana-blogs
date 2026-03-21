# katana-blogs

ローカルで Markdown を書き、GitHub に push したら Qiita / Zenn へ自動投稿できる記事管理基盤。

> システム構成・処理フローの詳細は [ARCHITECTURE.md](ARCHITECTURE.md) を参照。

## Prerequisites

セットアップの前に、以下のサービス登録・連携を済ませてください。

| サービス | 必要な準備 | 参考リンク |
|----------|-----------|------------|
| Qiita | アカウント登録済 | [Qiita](https://qiita.com/) |
| Qiita API | アクセストークン発行済（`write_qiita` scope） | [トークン発行画面](https://qiita.com/settings/tokens/new) |
| Zenn | GitHub 連携設定済（本リポジトリの `master` ブランチ） | [Zenn GitHub連携ガイド](https://zenn.dev/zenn/articles/connect-to-github) |

## Initial Setup

初回セットアップは対話式スクリプトで完了します。

```bash
bash scripts/setup.sh
```

スクリプトが行うこと:

1. **ツールインストール**: Homebrew, tfenv, Terraform, GitHub CLI の確認・インストール
2. **トークン設定**: Qiita Access Token を入力し `infra/github/terraform.tfvars` を生成
3. **Secrets 登録**: `terraform apply` で GitHub Actions Secrets に反映

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

- `blogs/draft/` 配下は workflow の投稿対象外。ここに置いたまま master に push しても投稿されない
- Qiita はフロントマターの `item_id` が空なら新規作成、値があれば更新処理
- Zenn への連携は、CI が `blogs/publish/<article>/zenn.md` を `articles/<article>.md` としてコピーし、Zenn の GitHub 連携が検知する仕組み
- Qiita 単体 / Zenn 単体での運用にも対応（片方のファイルだけ配置すればよい）
