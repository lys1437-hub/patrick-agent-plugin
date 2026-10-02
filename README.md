# patrick-agent plugin

LipiD 的產品工作方法 skill 包，給 Claude Code 用。

## English summary

A Claude Code plugin packaging LipiD's product-work methods as skills; the skill content is written in Traditional Chinese.

Skills:

- `feature-proposal-planning`
- `one-page-report`
- `report-and-verification`
- `skill-doctor`
- `skill-workflow-builder`
- `team-delivery-review`
- `team-weekly-review`

Installation: see [安裝](#安裝).

License: Apache-2.0 ([LICENSE](LICENSE)). Third-party notices: see [第三方來源聲明（NOTICE）](#第三方來源聲明notice).

## 安裝

### 0. 前置條件

**要有 Node.js 與 Claude Code CLI。**

```bash
npm install -g @anthropic-ai/claude-code
claude --version
```

⚠️ **一定要 CLI。** 桌面版沒有 `/plugin`，實測回 `isn't available in this environment`。
**但 CLI 裝完之後桌面版讀得到**（2026-09-07 實測，兩邊都看得見），
所以「用 CLI 裝、平常用桌面版」是可行的。

這是公開 repo；一般安裝不需要 collaborator 權限。若你的環境尚未登入 GitHub，
可選擇登入以使用其他 GitHub 功能：

```bash
gh auth login
```

### 1. 裝

```bash
claude plugin marketplace add lys1437-hub/patrick-agent-plugin
claude plugin install patrick-agent@patrick-agent-marketplace
claude plugin list
```

最後一行要看到版本號與 `enabled`。

**裝完要開一個新對話**才會載入 —— Claude Code 是在對話開始時讀 skill 清單。

### 2. 確認它真的能用

裝得起來 ≠ 能用。三層驗收見 **`ACCEPTANCE-LEVELS.md`**，
最少做第一層：打 `/patrick-agent` 確認七支 skill 都在。

## 裝完之後怎麼用

**你不會「呼叫」什麼。** 裝好之後，你的 Claude 通常會在講到「做功能提案」
「這功能要不要做」「規劃活動機制」「成效檢視」時自己套用這套方法。
**這是傾向，不是保證**：實際有沒有被觸發，請照 `ACCEPTANCE-LEVELS.md` 的 L1／L2 方法驗證。

也可以直接打 `/patrick-agent:<skill-name>` 明確指定。
⚠️ **前綴不能省** —— 打裸名叫不出來。

## 目前內容

| skill | 做什麼 |
|---|---|
| `feature-proposal-planning` | 功能提案規劃與成效檢視。含 E1–E4 證據分級、Pilot 實驗設計（樣本數／MDE／guardrail／事前定義 win-lose-inconclusive） |
| `report-and-verification` | 實際交付與決策數字的完成閘門；以 outcome、當次證據、未驗範圍及下一步回報 |
| `team-delivery-review` | 驗收別人的完成宣告，分開 workspace、commit、remote、runtime、部署狀態與發布準備度 |
| `team-weekly-review` | 從可取得來源整理團隊週報，缺來源標 unavailable，不把 commit 數當績效，也不補寫未觀測環境 |
| `skill-workflow-builder` | 以 baseline 與 forward test 建立或更新最小 Skill；一次性任務不硬建 |
| `skill-doctor` | 唯讀掃描 Skill 的斷引用、路徑耦合、description 截斷與 provenance |
| `one-page-report` | 產出單檔、自包含、可列印的一頁報告，並附交付前檢查器 |

另附宣告為唯讀的 `skill-auditor` agent（`agents/skill-auditor.md` 宣告 `tools: Read/Grep/Glob`；實際會不會被載入、工具限制是否生效，由你的 runtime 決定，作者尚未在非本機環境驗證過）；payload 以 Apache-2.0 授權，詳見 [LICENSE](LICENSE)。每次 PR 都會在 Linux、macOS 與 Windows 執行 payload 驗證與 contract tests。

## 第三方來源聲明（NOTICE）

其中兩支 skill 參考了別人公開的作品，各自附有 `NOTICE`（來源與原授權）和 `LICENSE`：

- [`skills/report-and-verification/NOTICE`](skills/report-and-verification/NOTICE)：
  參考 Anthropic `skill-creator` 的指引（Apache-2.0），以及 `obra/superpowers` 的
  `verification-before-completion` 原則（MIT）。
- [`skills/skill-workflow-builder/NOTICE`](skills/skill-workflow-builder/NOTICE)：
  改編 Anthropic `skill-creator` 的工作流設計原則（Apache-2.0）。

轉散布或改作這兩支 skill 時，請一併保留它們的 `NOTICE` 與 `LICENSE`。

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

## 維護方式

這個 repo 是可直接維護與發佈的公開 plugin payload。修改 `skills/`、文件或 manifest 時，
請透過 PR，並通過 `scripts/validate_plugin.py`、合約測試與 plugin manifest 驗證。

**版本政策：** 只要這次 PR 改了讀者會依賴的出貨內容（`skills/`、`agents/`、`TEAM_RULES.md`、
`WHY-THESE-RULES.md`、`ACCEPTANCE-LEVELS.md` 等文字或行為），就要把 `.claude-plugin/plugin.json`
的 `version` 往上跳（至少 patch）。**不允許內容變了、版本號沒變**——那會讓兩個內容不同的版本
對外看起來一樣，沒有人能靠版本號分辨自己裝到哪一份。純排版／錯字修正不在此限，由 PR 作者判斷。


---

## 歷史安裝實績（private repo 時期）

| 通路 | 狀態 |
|---|---|
| `codex plugin marketplace add lys1437-hub/patrick-agent-plugin` | ✅ **可行** —— 當時 private repo 會沿用對方的 `gh` 認證 |
| `claude plugin marketplace add <本機路徑>` | ✅ 已驗 |
| Claude Code 對 private GitHub repo | ✅ **2026-09-04 實測通過** —— 見下 |

### 2026-09-04：Claude Code 端端到端實測

```
claude plugin marketplace add lys1437-hub/patrick-agent-plugin
  → SSH not configured, cloning via HTTPS  →  ✔ Successfully added
claude plugin install patrick-agent@patrick-agent-marketplace
  → ✔ Successfully installed (scope: user)
claude plugin list
  → patrick-agent@patrick-agent-marketplace  <installed-version>  ✔ enabled
```

安裝結果落在 `~/.claude/plugins/cache/.../<installed-version>`，**釘住 `gitCommitSha`（安裝當下的版本，`claude plugin list` 可查）**；
7 支 skill ＋ `TEAM_RULES.md` ＋ `WHY-THESE-RULES.md` 都在，
`one-page-report` 的檢查器從安裝後的位置也跑得起來（exit 0）。

🔴 **順帶修掉一個錯的前提**：實測前，本機註冊的 marketplace 指向
**作者的個人 repo** —— 那個絕不能加 collaborator 的。
是 2026-08-28 拆 repo 之前的殘留，本機是 `directory` 來源所以沒出事，
但**團隊化整套設計的第一個前提，在本機設定裡是錯的，而且錯了 7 天沒人發現。**

⚠️ **作者自己的機器裝這包會有 7 支同名 skill 各兩份**（個人 `~/.claude/skills` 一份、
plugin cache 一份）。plugin 端有 `plugin:skill` 命名空間所以不是硬衝突，
但路由的選項裡會出現同名描述。作者機器讀個人正本即可，plugin 用於團隊驗收。
**作者機器讀正本就好，這包是給別人裝的。**

⚠️ **權限的已知限制**：這個 repo 在**個人帳號**底下，
GitHub 不支援個人 repo 的細分 collaborator 權限（read／triage／write 是 org 功能）。
所以受邀者拿到的是 **write**，`gh api ... -f permission=pull` 會回 204 但沒有效果。

**風險已評估為趨近零**：公開 payload 不含機密，並由 PR 與驗證流程保護。
真要唯讀只能建 GitHub Organization。

### 桌面版沒有 `/plugin`

實測回 `isn't available in this environment`，一律走 CLI。
