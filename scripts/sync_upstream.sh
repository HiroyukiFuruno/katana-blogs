#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# katana-blogs Upstream 同期スクリプト
#
# このスクリプトは本家リポジトリ (upstream) からの変更を
# ローカルおよび自分のフォーク (origin) に同期します。
# ============================================================

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

# ↑↓/jk キー選択UI
select_option() {
  local options=("$@")
  local selected=0
  local count=${#options[@]}

  # カーソル非表示
  tput civis 2>/dev/null || true
  # 終了時に必ずカーソルを復元
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

    echo -e "\n${DIM}(↑↓/jkで選択、Enterで確定)${RESET}"

    # キー入力を1文字読み取り
    local key
    IFS= read -rsn1 key

    if [[ "$key" == $'\x1b' ]]; then
      # エスケープシーケンスの判定 (矢印キー等)
      # 次の2文字を短いタイムアウト付きで読み取る
      read -rsn2 -t 0.01 key
      if [[ "$key" == "[A" || "$key" == "OA" ]]; then
        # 上キー
        [[ $selected -gt 0 ]] && ((selected--))
      elif [[ "$key" == "[B" || "$key" == "OB" ]]; then
        # 下キー
        [[ $selected -lt $((count - 1)) ]] && ((selected++))
      fi
    elif [[ "$key" == "k" ]]; then
      # vim-style up
      [[ $selected -gt 0 ]] && ((selected--))
    elif [[ "$key" == "j" ]]; then
      # vim-style down
      [[ $selected -lt $((count - 1)) ]] && ((selected++))
    elif [[ "$key" == "" ]]; then
      # Enter キー
      SELECTED=$selected
      return 0
    fi

    # 描画をクリアしてループ（選択肢行数 + \n + ヒント行）
    local lines_to_clear=$((count + 2))
    for ((i = 0; i < lines_to_clear; i++)); do
      tput cuu1 2>/dev/null || echo -ne '\033[1A'
      tput el  2>/dev/null || echo -ne '\033[2K'
    done
  done
}

# ------------------------------------------------------------
# 同期処理
# ------------------------------------------------------------

sync_upstream() {
  echo ""
  echo -e "${BOLD}🔄 Upstream からの変更を同期 (一括)${RESET}"
  echo ""

  if ! git remote | grep -q "^upstream$"; then
    error "upstream リモートが設定されていません。"
    echo -e "まず ${BOLD}bash scripts/setup.sh${RESET} を実行してリモート設定を行ってください。"
    exit 1
  fi

  info "upstream から最新情報を取得中..."
  git fetch upstream

  local current_branch
  current_branch=$(git rev-parse --abbrev-ref HEAD)

  echo -e "upstream/master を ${current_branch} にマージしますか?"
  select_option "Yes (実行)" "No (キャンセル)"

  if [[ $SELECTED -eq 0 ]]; then
    info "マージを実行します..."
    if git merge upstream/master; then
      ok "マージが完了しました。"

      echo ""
      echo -e "マージした内容を origin/${current_branch} にプッシュしますか?"
      select_option "Yes (プッシュ)" "No (ローカルのみ更新)"

      if [[ $SELECTED -eq 0 ]]; then
        info "プッシュを実行中..."
        git push origin "$current_branch"
        ok "プッシュが完了しました。"
      else
        info "プッシュをスキップしました。"
      fi
    else
      error "コンフリクトが発生しました。手動で解決してください。"
      exit 1
    fi
  else
    info "同期をキャンセルしました。"
  fi
}

# ------------------------------------------------------------
# メイン
# ------------------------------------------------------------

main() {
  echo ""
  echo -e "${BOLD}╔══════════════════════════════════════╗${RESET}"
  echo -e "${BOLD}║   katana-blogs Upstream 同期         ║${RESET}"
  echo -e "${BOLD}╚══════════════════════════════════════╝${RESET}"

  sync_upstream

  echo ""
  ok "同期プロセスが完了しました。"
  echo ""
}

main "$@"
