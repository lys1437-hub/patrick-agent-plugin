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
| Claude Code 對 private GitHub repo | 🟡 未測（Codex 那條通了，這條沒理由不通，但沒實測過） |

⚠️ **權限的已知限制**：這個 repo 在**個人帳號**底下，
GitHub 不支援個人 repo 的細分 collaborator 權限（read／triage／write 是 org 功能）。
所以受邀者拿到的是 **write**，`gh api ... -f permission=pull` 會回 204 但沒有效果。

**風險已評估為趨近零**：內容是 `build_plugin.py` 產生的、下次 build 就覆蓋、不含機密。
真要唯讀只能建 GitHub Organization。

### 桌面版沒有 `/plugin`

實測回 `isn't available in this environment`，一律走 CLI。
