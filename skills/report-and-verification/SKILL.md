---
name: report-and-verification
description: 驗證實際修改、交付、發布、外部操作與決策數字；純問答不使用，證據不足不得宣告完成。
license: Apache-2.0
metadata:
  version: "0.1.0"
  provenance:
    type: clean-room-original
    sources:
      - name: OpenAI skill-creator
        license: Apache-2.0
        used_for: Skill 結構、範圍控制與漸進揭露
      - name: obra/superpowers verification-before-completion
        license: MIT
        url: https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md
        used_for: 主張與驗證範圍對齊、完整輸出檢閱
---

# 交付與驗證

在實際修改、交付成品、發布、操作外部系統，或提出會影響決策的數字結論時使用。純問答、概念解釋與未產生交付物的討論不使用。

## 工作方式

1. 先把完成條件改寫成可觀測結果，並指出哪些結果會影響判斷。
2. 為每項主張選出能直接判斷它的完整檢查；執行後讀取完整輸出，包括錯誤、失敗、跳過項目與實際涵蓋範圍。優先使用本次執行產生的直接證據。
3. 對照完成條件檢查產物、外部狀態與失敗訊號。局部檢查只能支持同等範圍的結論；命令成功只代表命令結束，不代表目標完成。
4. 依證據選擇一個 outcome，不能用模糊的「完成」取代：
   - `verified`：所有關鍵完成條件都有本次直接證據，且沒有會推翻結論的未驗項目。
   - `limited`：已完成並驗證一部分，但仍有清楚界定、不阻止有限使用的未驗範圍。
   - `needs-input`：缺少使用者選擇、權限、材料或口徑，取得後可繼續。
   - `blocked`：已確認存在外部或技術阻礙，現有範圍內無法繼續。
5. 回報必須同時列出：`outcome`、當次證據、未驗範圍、下一步。若是 `limited`，明說現在可以安全主張什麼。

## 不可越過的判定線

- exit code 為 0，但預期產物不存在、為空、位置不符或不可讀時，不得標為 `verified`。
- 舊 log、舊截圖或前次結果只能提供背景；沒有本次直接觀測時，不得標為 `verified`。
- 「零筆／無變化」必須能和資料源故障、權限錯誤、查詢被截斷或資料延遲區分。
- 不把代理訊號寫成最終結果，例如只以 HTTP 200 推論資料已正確落地。
- 不以較窄的檢查替代較廣的主張，例如只通過 lint 就宣稱 build 成功，或只通過單一測試就宣稱全部需求成立。

涉及資料、量化門檻或會影響決策的數字時，必須先讀 [references/decision-grade-verification.md](references/decision-grade-verification.md)。

交付牽涉多份互相關聯的規格、計畫、決策、驗證紀錄或產物時，必須先讀 [references/artifact-consistency.md](references/artifact-consistency.md)，完成跨 artifact 一致性檢查後才可選 `verified`。

## 回報格式

```text
outcome: verified | limited | needs-input | blocked
當次證據:
- 觀測、時間／執行脈絡、與完成條件的對應
未驗範圍:
- 無，或具體列出
下一步:
- 無，或最小可行動作與負責方
```
