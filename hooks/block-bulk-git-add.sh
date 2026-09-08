#!/usr/bin/env bash
# patrick-agent plugin · 擋下 `git add -A` / `git add .` / `git commit -a`
#
# ── 為什麼是這一條，而不是別條 ────────────────────────────────────────
# TEAM_RULES 的「加新規則之前」三問，目前只有這一條全部答得出來：
#   1. 擋的是哪一次真實事故 → 有，見 WHY-THESE-RULES.md〈不用 git add -A〉
#   2. 犯過幾次 → 不只一次
#   3. 遵守比繞過容易嗎 → 不是。列路徑比打 -A 麻煩，所以它一定會被繞過。
#      **這就是它該被自動化、而不是寫進文件的理由。**
#
# ── 這支跟作者本機那支安全攔截器的設計刻意相反 ──────────────────────
# 本機那支：讀不到指令內容就**擋下來**（寧可被擋，也不要出事）。
# 這支：讀不到就**放行**。
#
# 因為保護對象不同。本機那支保護的是作者自己，他知道怎麼修；
# 這支跑在別人的機器上 —— **他不知道發生什麼事，只會覺得整包壞了。**
# 一支會把人卡死的 hook，第一件事就是被關掉，那比沒有更糟：
# **你以為還有保護。**
#
# 同理不使用 jq：macOS 沒有內建，團隊成員多半沒裝。
# 依賴它等於「沒裝 jq 的人，Claude 全部指令被擋」——
# 那是把「少一個前置條件」從「裝不起來」升級成「裝起來然後全卡住」。
#
# ── 這支不做什麼 ────────────────────────────────────────────────────
# 只攔 Claude 的工具呼叫，**不影響你自己在終端機打的指令**。
# 真的需要一次加全部時，自己在終端機跑就好 —— 那是人的決定，不該由 AI 代做。
#
# ── 怎麼停用 ────────────────────────────────────────────────────────
#   claude plugin disable patrick-agent@patrick-agent-marketplace
# 或在 ~/.claude/settings.json 移除對應的 hook 註冊。
# **如果它擋錯了，請告訴維護者**——被誤擋卻默默關掉，等於雙方都以為還有保護。

set -u

input=""
if [ ! -t 0 ]; then
  input="$(cat 2>/dev/null || true)"
fi

allow() { exit 0; }   # 🔴 任何看不懂的情況一律放行，見上方設計說明

[ -z "$input" ] && allow

# 純 shell 取出 .tool_input.command，不依賴 jq。
# 只認最單純的形狀；認不出來就放行。
cmd="${input#*\"command\":}"
[ "$cmd" = "$input" ] && allow          # 沒有 command 欄位
while [ "${cmd# }" != "$cmd" ]; do cmd="${cmd# }"; done   # 去掉前導空白
case "$cmd" in
  \"*) cmd="${cmd#\"}"; cmd="${cmd%%\"*}" ;;
  *)   allow ;;                          # 不是字串，形狀不認得
esac

# JSON 逸出還原（只還原會影響判斷的兩個）
cmd="${cmd//\\\"/\"}"
cmd="${cmd//\\\\/\\}"

# 只看第一個 heredoc 之前的部分 —— heredoc 內文是資料不是指令
head="${cmd%%<<*}"

deny() {
  # 訊息一定要自報家門：沒說是誰擋的，對方會以為 Claude Code 壞了，
  # 然後去 debug 錯的東西。
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$1"
  exit 0
}

case "$head" in
  *"git add -A"*|*"git add --all"*|*"git add ."*|*"git add -a"*)
    deny "【patrick-agent plugin】擋下 git add 的整批加入。請只 stage 這次真正動過的明確路徑（git add path/to/file）。原因：整批加入會把不相干的暫存檔、憑證、別人未完成的工作一起帶進 commit，而且事後很難看出是哪一次混進去的。真的需要一次加全部時，請你自己在終端機執行 —— 那是人的決定。停用方式見 plugin 的 README。"
    ;;
  *"git commit -a"*|*"git commit --all"*)
    deny "【patrick-agent plugin】擋下 git commit -a（等同先 git add -A）。請先 stage 明確路徑再 commit。真的需要時請自己在終端機執行。停用方式見 plugin 的 README。"
    ;;
esac

allow
