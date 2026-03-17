# GitHub Connection

このディレクトリでは、`katana-blogs` で利用する GitHub 側の接続情報と運用ルールを管理します。

## 管理対象

- Repository: `katana-blogs`
- Default branch: `master`
- Workflow: `.github/workflows/publish.yml`
- GitHub Secrets:
  - `QIITA_ACCESS_TOKEN`

## Secrets の意味

- `QIITA_ACCESS_TOKEN`
  - Qiita API v2 の Bearer token
  - `write_qiita` scope が必要

## 推奨セットアップ

前提として Mac 環境かつ Homebrew がインストールされているものとします。Homebrew が無い場合は、公式サイト等の手順に従って事前にインストールしてください。

1. CLI ツールのインストール

   ```bash
   brew install tfenv
   tfenv install latest
   brew reinstall gh # 既にインストールされている場合も再インストール・更新
   ```

2. GitHub CLI ログイン

   ```bash
   gh auth login
   ```

3. `infra/github/repository.env` の値を自分のリポジトリ情報に合わせて書き換える
   - `GITHUB_OWNER` (例: あなたのGitHubユーザー名またはOrganization名)
   - `GITHUB_REPOSITORY`
   - `GITHUB_DEFAULT_BRANCH`

4. `infra/github/secrets.example.env` を `infra/github/secrets.env` にコピーして値を入れる

5. ターミナルでリポジトリのルート (repository root) に移動し、以下のコマンドを実行して GitHub repository secrets に登録する

   ```bash
   python3 infra/github/sync_secrets.py
   ```

雛形は [secrets.example.env](secrets.example.env) と [repository.env](repository.env) を参照してください。同期スクリプトは [sync_secrets.py](sync_secrets.py) です。
