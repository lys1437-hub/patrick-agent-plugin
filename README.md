# patrick-agent plugin

LipiD 的產品工作方法 skill 包，給 Claude Code 用。

## 安裝

```bash
claude plugin marketplace add lys1437-hub/patrick-agent-plugin
claude plugin install patrick-agent@patrick-agent-marketplace
```

**裝完要開一個新對話**才會載入 —— Claude Code 是在對話開始時讀 skill 清單。

## 裝完之後怎麼用

**你不會「呼叫」什麼。** 裝好之後，你的 Claude 就懂這套方法了 ——
講到「做功能提案」「這功能要不要做」「規劃活動機制」「成效檢視」時它會自己套用。

也可以直接打 `/feature-proposal-planning` 叫它。

## 目前內容

| skill | 做什麼 |
|---|---|
| `feature-proposal-planning` | 功能提案規劃與成效檢視。含 E1–E4 證據分級、Pilot 實驗設計（樣本數／MDE／guardrail／事前定義 win-lose-inconclusive） |

## 上游 plugin：只給地址，不複製

`marketplace.json` 除了本包，還列了指向**別人作品**的 plugin。
**這裡沒有複製它們的任何內容**，只是給地址並**釘住 commit**。

| plugin | 上游 | 授權 | 釘在 |
|---|---|---|---|
| `superpowers` | `obra/superpowers` v6.3.0 | MIT | `b36e0829` |

### 為什麼要釘 sha，而不是讓它自動更新

- **不釘**：每個人安裝的時間不同就拿到不同版本，而且上游哪天改了行為，
  團隊某天突然表現不一樣——**沒人知道為什麼**。
- **釘住**：全隊拿到同一份。要升級就改這一行 sha、commit、請大家重裝，
  **升級變成一個看得見的動作。**

如果你另外有監控上游的機制，它的產出應該是「**一個 bump sha 的 PR**」，不是自動改。

### 為什麼不 fork 進來

fork 之後你就變成維護者，要自己同步、自己承擔漂移，還要處理署名。
指向上游則是零維護、零授權風險——**你沒有散布，只是給地址。**

## 其他值得裝、但不在這裡的上游

有些上游是 **marketplace 而不是單一 plugin**，要各自加：

```bash
# Anthropic 官方 Agent Skills（含 skill-creator、mcp-builder、docx、pptx…）
claude plugin marketplace add anthropics/skills
```

> ⚠️ 這一條**未經本包實測**。`anthropics/skills` 只有 `.claude-plugin/marketplace.json`、
> 沒有頂層 `plugin.json`，所以它是 marketplace 不是 plugin ——
> 不能直接寫進本包的 `plugins` 清單。已於 2026-09-04 確認
> `skills/skill-creator` 路徑存在。

## ⚠️ 這個 repo 是產生出來的，不要直接編輯

`skills/` 底下的內容是從作者的私有 repo **產生**出來的，
複製時會做環境淨化（把指向作者本機的引用改寫成對方看得懂的說明）。

**在這裡改會在下次 build 被覆蓋。** 有問題或想改內容，直接跟作者說。


---

## 安裝實績（2026-08-28 首次跨機器驗證）

| 通路 | 狀態 |
|---|---|
| `codex plugin marketplace add lys1437-hub/patrick-agent-plugin` | ✅ **可行** —— private repo 會沿用對方的 `gh` 認證 |
| `claude plugin marketplace add <本機路徑>` | ✅ 已驗 |
| Claude Code 對 private GitHub repo | ✅ **2026-09-04 實測通過** —— 見下 |

### 2026-09-04：Claude Code 端端到端實測

```
claude plugin marketplace add lys1437-hub/patrick-agent-plugin
  → SSH not configured, cloning via HTTPS  →  ✔ Successfully added
claude plugin install patrick-agent@patrick-agent-marketplace
  → ✔ Successfully installed (scope: user)
claude plugin list
  → patrick-agent@patrick-agent-marketplace  0.4.0  ✔ enabled
```

安裝結果落在 `~/.claude/plugins/cache/.../0.4.0`，**釘住 `gitCommitSha`**（`1e7a1b5`），
5 支 skill ＋ `TEAM_RULES.md` ＋ `WHY-THESE-RULES.md` 都在，
`one-page-report` 的檢查器從安裝後的位置也跑得起來（exit 0）。

🔴 **順帶修掉一個錯的前提**：實測前，本機註冊的 marketplace 指向
`/Users/patrick.lee/projects/Patrick-agent` —— **個人 repo，那個絕不能加 collaborator 的**。
是 2026-08-28 拆 repo 之前的殘留，本機是 `directory` 來源所以沒出事，
但**團隊化整套設計的第一個前提，在本機設定裡是錯的，而且錯了 7 天沒人發現。**

⚠️ **作者自己的機器裝這包會有 5 支同名 skill 各兩份**（個人 `~/.claude/skills` 一份、
plugin cache 一份）。plugin 端有 `plugin:skill` 命名空間所以不是硬衝突，
但路由的選項裡會出現兩個幾乎一樣的描述 —— 同一天在 `report-page` 上already 踩過。
**作者機器讀正本就好，這包是給別人裝的。**

⚠️ **權限的已知限制**：這個 repo 在**個人帳號**底下，
GitHub 不支援個人 repo 的細分 collaborator 權限（read／triage／write 是 org 功能）。
所以受邀者拿到的是 **write**，`gh api ... -f permission=pull` 會回 204 但沒有效果。

**風險已評估為趨近零**：內容是 `build_plugin.py` 產生的、下次 build 就覆蓋、不含機密。
真要唯讀只能建 GitHub Organization。

### 桌面版沒有 `/plugin`

實測回 `isn't available in this environment`，一律走 CLI。
