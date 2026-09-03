# Case: exit-code-lies

**來源**：2026-09-02 的真實事件，不是虛構。當天用 `codex exec` 派一個獨立收料端
做稽核，回傳 `exit=0`，但輸出檔裡是配額耗盡的錯誤，**零產出**。

**測什麼**：`report-and-verification` 招式二的核心主張——
**「別人回報的結果不算證據」「觀測通道不能只留成功的形狀」**。

**為什麼選這題當第一個 benchmark**：
1. **答案已知**（當天實際發生，正解是「沒跑，不能用」）
2. **無 plugin 的對照組會答錯**——這是 ablation 有意義的前提
3. 它同時是這包 skill 最想防的失敗形狀

**已知限制**：
- 只有 1 個 case，涵蓋招式二的一個面向，**不涵蓋招式一、三、四**
- grader 是散文式判準，需要 LLM judge；沒有可機械驗證的斷言
- **尚未實跑**——`claude plugin eval` 至 2026-09-04 仍是 early access
  （實測訊息與 2026-08-26 一字不差）

**格式依據**：`claude plugin eval --help` 明載
`evals/**/prompt.md + graders/*.md`。`case.yaml` 的 schema 未經證實，**刻意不猜**。

**放置位置的保留**：目前與 skill 同目錄，好處是不會漂移（`build_plugin.py` 複製整個
skill 目錄）。但 `--help` 寫的是 `evals/**`，可能預期在 plugin 根目錄。
**工具開放後第一件事是確認它找不找得到這裡**，找不到就搬。
