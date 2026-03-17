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

3. `infra/github/terraform.tfvars.example` をコピーして `terraform.tfvars` を作成し、Qiitaのアクセストークンを設定する。

   ```bash
   cd infra/github
   cp terraform.tfvars.example terraform.tfvars
   ```

4. Terraform を使って GitHub Secrets を登録する

   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

雛形は [terraform.tfvars.example](terraform.tfvars.example) と [variables.tf](variables.tf) を参照してください。
