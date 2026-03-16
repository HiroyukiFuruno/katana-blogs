# GitHub Connection

このディレクトリでは、`HiroyukiFuruno/katana-blogs` で利用する GitHub 側の接続情報と運用ルールを管理します。

## 管理対象

- Repository: `HiroyukiFuruno/katana-blogs`
- Default branch: `master`
- Workflow: `.github/workflows/publish.yml`
- GitHub Secrets:
  - `QIITA_ACCESS_TOKEN`
  - `ZENN_COOKIE`

## Secrets の意味

- `QIITA_ACCESS_TOKEN`
  - Qiita API v2 の Bearer token
  - `write_qiita` scope が必要
- `ZENN_COOKIE`
  - Zenn にログインしたブラウザセッションの Cookie 文字列
  - 非公式 API を使うため、Cookie の仕様変更で無効になる可能性があります

## 推奨セットアップ

1. GitHub 上で `HiroyukiFuruno/katana-blogs` を public repository として作成する
2. `master` ブランチを保護したい場合は、初回 publish が frontmatter を同期できるよう `github-actions[bot]` の push を許可する
3. [secrets.example.env](./secrets.example.env) を `secrets.env` にコピーして値を入れる
4. `gh auth login` 済みの環境で `python3 infra/github/sync_secrets.py` を実行して repository secrets に登録する

雛形は [secrets.example.env](./secrets.example.env) と [repository.env](./repository.env) を参照してください。同期スクリプトは [sync_secrets.py](./sync_secrets.py) です。
