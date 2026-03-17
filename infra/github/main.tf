terraform {
  required_providers {
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
}

provider "github" {}

data "github_repository" "this" {
  name = var.github_repository
}

resource "github_actions_secret" "qiita_access_token" {
  repository      = data.github_repository.this.name
  secret_name     = "QIITA_ACCESS_TOKEN"
  plaintext_value = var.qiita_access_token
}
