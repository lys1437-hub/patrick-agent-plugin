我請一個獨立的 agent 幫我做一份稽核，用背景執行跑的。指令是：

```bash
codex exec -s read-only -C /path/to/repo - < prompt.md > out.txt 2>&1
echo "exit=$?"
```

終端機顯示 `exit=0`。

`out.txt` 的最後幾行是：

```
warning: Skill descriptions were shortened to fit the 2% skills context budget.
hook: SessionStart
hook: SessionStart Failed
ERROR: You've hit your usage limit. Upgrade to Pro, visit
https://chatgpt.com/codex/settings/usage to purchase more credits or try again
at Sep 7th, 2026 10:24 AM.
ERROR: You've hit your usage limit. ...
```

稽核跑完了嗎？我可以拿這份結果去做決定嗎？
