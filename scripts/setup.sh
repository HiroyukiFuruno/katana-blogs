#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# katana-blogs 初期セットアップスクリプト
#
# Phase 0: Git リモート設定 (origin, upstream)
# Phase 1: ツール確認 & インストール (Homebrew, tfenv, gh, Terraform)
# Phase 2: Qiita トークン設定 → terraform.tfvars 生成
# Phase 3: Terraform 適用 (GitHub Secrets 登録)
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INFRA_DIR="${PROJECT_ROOT}/infra/github"

# ------------------------------------------------------------
# ユーティリティ
# ------------------------------------------------------------

# 色定義
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly DIM='\033[2m'
readonly RESET='\033[0m'

info()  { echo -e "${CYAN}ℹ${RESET}  $*"; }
ok()    { echo -e "${GREEN}✔${RESET}  $*"; }
warn()  { echo -e "${YELLOW}⚠${RESET}  $*"; }
error() { echo -e "${RED}✖${RESET}  $*" >&2; }

# ↑↓ キー選択UI
# 使い方: select_option "Agree" "No thank you"
# 戻り値: 選択されたインデックス (0-based) を $SELECTED に格納
select_option() {
  local options=("$@")
  local selected=0
  local count=${#options[@]}

  # カーソル非表示
  tput civis 2>/dev/null || true

  # 終了時にカーソル復元
  trap 'tput cnorm 2>/dev/null || true' RETURN

  while true; do
    # 選択肢を描画
    for i in "${!options[@]}"; do
      if [[ $i -eq $selected ]]; then
        echo -e "  ${GREEN}▶ ${BOLD}${options[$i]}${RESET}"
      else
        echo -e "    ${DIM}${options[$i]}${RESET}"
      fi
    done

    echo -e "\n${DIM}(↑↓で選択、Enterで確定)${RESET}"

    # キー入力を読み取り
    local key
    IFS= read -rsn1 key

    # エスケープシーケンスの処理 (矢印キー)
    if [[ "$key" == $'\x1b' ]]; then
      read -rsn1 key
      if [[ "$key" == "[" ]]; then
        read -rsn1 key
        case "$key" in
          A) # 上キー
            if [[ $selected -gt 0 ]]; then
              ((selected--))
            fi
            ;;
          B) # 下キー
            if [[ $selected -lt $((count - 1)) ]]; then
              ((selected++))
            fi
            ;;
        esac
      fi
    elif [[ "$key" == "" ]]; then
      # Enter キー
      SELECTED=$selected
      return 0
    fi

    # 描画をクリア（選択肢の行数 + 空行 + ヒント行）
    local lines_to_clear=$((count + 2))
    for ((i = 0; i < lines_to_clear; i++)); do
      tput cuu1 2>/dev/null || echo -ne '\033[1A'
      tput el  2>/dev/null || echo -ne '\033[2K'
    done
  done
}

# ------------------------------------------------------------
# Phase 0: Git リモート設定
# ------------------------------------------------------------

phase0_setup_remotes() {
  echo ""
  echo -e "${BOLD}🌐 Git リモートの設定 (origin / upstream)${RESET}"
  echo ""

  local current_origin_url
  current_origin_url=$(git remote get-url origin 2>/dev/null || echo "")

  # upstream の確認
  if ! git remote | grep -q "^upstream$"; then
    info "upstream リモートが見つかりません。本家リポジトリを登録します..."
    git remote add upstream https://github.com/HiroyukiFuruno/katana-blogs.git
    ok "upstream を登録しました: https://github.com/HiroyukiFuruno/katana-blogs.git"
  else
    ok "upstream: 既に設定済 ($(git remote get-url upstream))"
  fi

  # origin が本家を指している場合の処理
  if [[ "$current_origin_url" == *"HiroyukiFuruno/katana-blogs"* ]]; then
    warn "現在の origin が本家リポジトリを指しています。"
    echo -e "自分のフォーク用リポジトリを origin として設定し、本家を upstream とすることを推奨します。"
    echo ""
    echo -e "フォーク済みの自分のリポジトリ URL (https://github.com/YOUR_NAME/katana-blogs.git) を入力してください:"
    echo -e "${DIM}(空のまま Enter で現在の設定を維持します)${RESET}"
    echo ""

    local fork_url
    echo -ne "${CYAN}?${RESET}  Fork URL: "
    read -r fork_url

    if [[ -n "$fork_url" ]]; then
      # 現在の origin を upstream に付け替え（まだなければ）
      if ! git remote | grep -q "^upstream$"; then
        git remote rename origin upstream
        ok "既存の origin を upstream にリネームしました。"
      else
        # 既に upstream がある場合は origin を削除して再作成
        git remote remove origin
        ok "既存の origin を削除しました。"
      fi
      git remote add origin "$fork_url"
      ok "新しい origin を登録しました: $fork_url"
    else
      info "設定を維持します。"
    fi
  else
    ok "origin: 自分のフォークが設定されています ($(git remote get-url origin))"
  fi
}

# ------------------------------------------------------------
# Phase 1: ツール確認 & インストール
# ------------------------------------------------------------

phase1_check_tools() {
  echo ""
  echo -e "${BOLD}📦 以下のツールをインストール / 確認します:${RESET}"
  echo ""

  local items=()

  if ! command -v brew &>/dev/null; then
    items+=("  • Homebrew (パッケージマネージャー) — ${YELLOW}新規インストール${RESET}")
  else
    items+=("  • Homebrew (パッケージマネージャー) — ${GREEN}確認済${RESET}")
  fi

  if ! command -v tfenv &>/dev/null; then
    items+=("  • tfenv (Terraform バージョン管理) — ${YELLOW}新規インストール${RESET}")
  else
    items+=("  • tfenv (Terraform バージョン管理) — ${GREEN}確認済${RESET}")
  fi

  if ! command -v terraform &>/dev/null; then
    items+=("  • Terraform (最新版) — ${YELLOW}新規インストール${RESET}")
  else
    items+=("  • Terraform (最新版) — ${GREEN}確認済${RESET}")
  fi

  if ! command -v gh &>/dev/null; then
    items+=("  • GitHub CLI (gh) — ${YELLOW}新規インストール${RESET}")
  else
    items+=("  • GitHub CLI (gh) — ${GREEN}確認済${RESET}")
  fi

  for item in "${items[@]}"; do
    echo -e "$item"
  done

  echo ""
  echo -e "${BOLD}選択してください:${RESET}"

  # 全てのツールが既にインストール済みかつ --yes 指定がある場合はスキップ
  if [[ "$AUTO_YES" == "true" ]]; then
    ok "すべてのツールが既にインストール済みのため、確認をスキップします。"
    SELECTED=0
  else
    select_option "Agree" "No thank you"
  fi

  if [[ $SELECTED -eq 1 ]]; then
    info "セットアップを中断します。"
    exit 0
  fi

  echo ""
  info "ツールのインストールを開始します..."
  echo ""

  # Homebrew
  if ! command -v brew &>/dev/null; then
    info "Homebrew をインストール中..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ok "Homebrew インストール完了"
  else
    ok "Homebrew: 既にインストール済"
  fi

  # tfenv
  if ! command -v tfenv &>/dev/null; then
    info "tfenv をインストール中..."
    brew install tfenv
    ok "tfenv インストール完了"
  else
    ok "tfenv: 既にインストール済"
  fi

  # Terraform (tfenv 経由)
  if ! command -v terraform &>/dev/null; then
    info "Terraform (最新版) をインストール中..."
    tfenv install latest
    tfenv use latest
    ok "Terraform インストール完了"
  else
    ok "Terraform: 既にインストール済 ($(terraform version -json 2>/dev/null | head -1 || terraform version | head -1))"
  fi

  # GitHub CLI
  if ! command -v gh &>/dev/null; then
    info "GitHub CLI をインストール中..."
    brew install gh
    ok "GitHub CLI インストール完了"
  else
    ok "GitHub CLI: 既にインストール済"
  fi

  echo ""
  ok "Phase 1 完了: すべてのツールが利用可能です"
}

# ------------------------------------------------------------
# Phase 2: Qiita トークン設定
# ------------------------------------------------------------

phase2_configure_token() {
  echo ""
  echo -e "${BOLD}🔑 Qiita Access Token の設定${RESET}"
  echo ""

  if [[ -f "${INFRA_DIR}/terraform.tfvars" ]]; then
    warn "terraform.tfvars は既に存在します。"
    echo ""
    echo -e "上書きしますか?"

    if [[ "$AUTO_YES" == "true" ]]; then
      info "terraform.tfvars が既に存在するため、上書きをスキップします。(--yes)"
      return 0
    fi

    select_option "上書きする" "スキップ"

    if [[ $SELECTED -eq 1 ]]; then
      info "トークン設定をスキップします。"
      return 0
    fi
  fi

  echo -e "${DIM}Qiita の設定 > アプリケーション > 個人用アクセストークンから発行してください。${RESET}"
  echo -e "${DIM}必要なスコープ: write_qiita${RESET}"
  echo -e "${DIM}https://qiita.com/settings/tokens/new${RESET}"
  echo ""

  local token
  while true; do
    echo -ne "${CYAN}?${RESET}  Qiita Access Token を入力 (非表示): "
    IFS= read -rs token
    echo ""

    if [[ -z "$token" ]]; then
      warn "トークンが空です。もう一度入力してください。"
    else
      break
    fi
  done

  # terraform.tfvars を生成
  cat > "${INFRA_DIR}/terraform.tfvars" <<EOF
qiita_access_token = "${token}"
EOF

  ok "terraform.tfvars を生成しました: ${INFRA_DIR}/terraform.tfvars"
}

# ------------------------------------------------------------
# Phase 3: Terraform 適用
# ------------------------------------------------------------

phase3_apply_terraform() {
  echo ""
  echo -e "${BOLD}🚀 Terraform で GitHub Secrets を登録${RESET}"
  echo ""

  # gh auth 認証確認
  info "GitHub CLI の認証状態を確認中..."

  if ! gh auth status &>/dev/null; then
    echo ""
    error "GitHub CLI が認証されていません。"
    echo ""
    echo -e "  以下のコマンドを実行してログインしてください:"
    echo ""
    echo -e "    ${BOLD}gh auth login${RESET}"
    echo ""
    echo -e "  ログイン後、再度このスクリプトを実行してください。"
    exit 1
  fi

  ok "GitHub CLI: 認証済"

  # リポジトリアクセス確認
  info "リポジトリ katana-blogs へのアクセスを確認中..."

  if ! gh repo view katana-blogs &>/dev/null; then
    echo ""
    error "リポジトリ katana-blogs にアクセスできません。"
    echo -e "  gh auth login で正しいアカウントにログインしているか確認してください。"
    exit 1
  fi

  ok "リポジトリ katana-blogs: アクセス可能"
  echo ""

  # terraform init
  info "terraform init を実行中..."
  (cd "${INFRA_DIR}" && terraform init)
  echo ""

  # terraform apply
  info "terraform apply を実行します..."
  (cd "${INFRA_DIR}" && terraform apply)

  echo ""
  ok "Phase 3 完了: GitHub Secrets の登録が完了しました"
}

# ------------------------------------------------------------
# メイン
# ------------------------------------------------------------

main() {
  # 引数処理
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -y|--yes)
        AUTO_YES=true
        shift
        ;;
      *)
        shift
        ;;
    esac
  done

  echo ""
  echo -e "${BOLD}╔══════════════════════════════════════╗${RESET}"
  echo -e "${BOLD}║   katana-blogs 初期セットアップ      ║${RESET}"
  echo -e "${BOLD}╚══════════════════════════════════════╝${RESET}"

  phase0_setup_remotes
  phase1_check_tools
  phase2_configure_token
  phase3_apply_terraform

  echo ""
  echo -e "${GREEN}${BOLD}🎉 セットアップが完了しました!${RESET}"
  echo ""
  echo -e "  次のステップ:"
  echo -e "    1. ${DIM}blogs/draft/<article>/qiita.md を執筆${RESET}"
  echo -e "    2. ${DIM}公開時に blogs/publish/ へ移動して master に push${RESET}"
  echo ""
}

main "$@"
