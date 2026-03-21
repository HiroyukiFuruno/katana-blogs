# ${YOUR_REPOSITORY_NAME}

ローカルで Markdown を書き、GitHub に push したら Qiita / Zenn へ自動投稿できる記事管理基盤。

> システム構成・処理フローの詳細は [ARCHITECTURE.md](ARCHITECTURE.md) を参照。

## 事前準備

セットアップの前に、以下のサービス登録・連携を済ませてください。

| サービス | 必要な準備 | 参考リンク |
| --- | --- | --- |
| Qiita | アカウント登録済 | [Qiita](https://qiita.com/) |
| Qiita API | アクセストークン発行済（`write_qiita` scope） | [トークン発行画面](https://qiita.com/settings/tokens/new) |
| Zenn | GitHub 連携設定済（本リポジトリの `master` ブランチ） | [Zenn GitHub連携ガイド](https://zenn.dev/zenn/articles/connect-to-github) |

## 導入手順

1. **Fork**: GitHub上で [HiroyukiFuruno/katana-blogs](https://github.com/HiroyukiFuruno/katana-blogs) を自分のアカウントに Fork します。
2. **Clone**: Fork した自分のリポジトリをローカルにクローンします。

   ```bash
   # リポジトリ名を決める（例: my-blog）
   export YOUR_REPOSITORY_NAME=xxxxx

   git clone https://github.com/自分のユーザー名/${YOUR_REPOSITORY_NAME}.git
   cd ${YOUR_REPOSITORY_NAME}
   ```

## 初期セットアップ

初回セットアップは対話式スクリプトで完了します。

```bash
bash scripts/setup.sh
```

スクリプトが行うこと:

1. **リモート設定**: `origin` (自分のフォーク) と `upstream` (本家) を構成
2. **ツールインストール**: Homebrew, tfenv, Terraform, GitHub CLI の確認・インストール
3. **トークン設定**: Qiita Access Token を入力し `infra/github/terraform.tfvars` を生成
4. **Secrets 登録**: `terraform apply` で GitHub Actions Secrets に反映

## メンテナンス

### Upstream との同期

本家リポジトリ (`HiroyukiFuruno/katana-blogs`) の更新を自分のフォークに取り込むには、以下のコマンドを実行します。

```bash
bash scripts/sync_upstream.sh
```

このコマンドは `upstream` からフェッチし、現在のブランチに `upstream/master` をマージします。

## ローカルコマンド

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

## 注意事項

- **CI が自動で push する**: workflow は `item_id` の書き戻しや `articles/` の同期コミットを `master` に push する。ローカルとの差分が生まれるため、**作業開始前に `git pull` を習慣化すること**
- `blogs/draft/` 配下は workflow の投稿対象外。ここに置いたまま master に push しても投稿されない。
  - **注意**: リポジトリを Public に設定している場合、下書き（draft/）の内容も GitHub 上で公開される。下書きを非公開にしたい場合は、リポジトリを **Private** に設定することを推奨。
- Qiita はフロントマターの `item_id` が空なら新規作成、値があれば更新処理
- Zenn への連携は、CI が `blogs/publish/<article>/zenn.md` を `articles/<article>.md` としてコピーし、Zenn の GitHub 連携が検知する仕組み
- Qiita 単体 / Zenn 単体での運用にも対応（片方のファイルだけ配置すればよい）
