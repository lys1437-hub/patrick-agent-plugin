---
name: skill-workflow-builder
description: 建立或更新可重複使用的 Skill；一次性任務或已有流程已充分處理時不新建。
license: Apache-2.0
metadata:
  version: "0.1.0"
  provenance:
    type: derived-guidance
    sources:
      - Anthropic skill-creator (Apache-2.0)
---

# Skill 工作流建造器

把反覆出現、且需要非顯然決策規則的工作整理成最小可驗證 Skill。沿用官方 skill-creator 的範圍控制、漸進揭露與驗證原則。

## 先路由，不預設要新建

根據案例與現有 Skill 選一條路：

- `create`：任務會重複，現有 Skill 無法承接，且 baseline 有穩定、可觀測的落差。
- `update`：已有同用途 Skill；以最小修改修正已觀測落差，保留其相容介面與無關內容。
- `no-skill`：一次性任務、通用模型能力已穩定做好、缺少可重複需求，或規則只是在重述顯然步驟。

不因使用者說「做成 Skill」就跳過路由。若判斷 `no-skill`，直接說明理由並提供更輕量的替代物；不要產生 Skill 骨架。

## 建立或更新流程

1. 收集真實的成功案例、失敗案例與驗收標準。案例要能看出輸入、期望決策、可接受變化與禁止結果；資訊足夠時不追加訪談。
2. 在未載入目標 Skill 的隔離情境先跑 baseline，保存實際輸出與失敗證據。不可用想像中的弱答案代替 baseline。
3. 比較 baseline 與驗收標準，只把反覆出現、非顯然、能修正可觀測落差的規則寫入。baseline 已做好的行為不得升格成新規則。
4. 建立最小結構：必須有 `SKILL.md`；只有條件式細節才加 `references/`，重複且需確定性的操作才加 `scripts/`，輸出素材才加 `assets/`。
5. description 寫清楚正向觸發與關鍵排除；正文保留目的、路由、約束與資源入口。字數受限時，
   先保留排除條件，再保留使用者實際會說、辨識度高的專有名詞與場景詞；語意重疊的
   同義詞可由代表詞及正文承接，並以正向觸發案例驗證取捨。不得硬編使用者或機器的絕對路徑。
6. 執行官方 `quick_validate.py <skill-folder>`。若有 scripts，實跑正常與失敗路徑；逐一解析內部相對引用。
7. 用未提供標準答案的新案例做 forward test。評估實際決策與產物，不只比對字詞、章節或正則。
8. 只根據觀測到的失敗迭代；避免為單一案例累積普遍規則。

## 交付回報

回報以下內容：

- 決策：`create`、`update` 或 `no-skill`，以及案例證據。
- 來源與授權：實際使用的來源、版本或位置、license／NOTICE 處理。
- 已驗能力：驗證指令、forward test 案例與結果。
- 未驗範圍：未測的平台、工具、權限、外部副作用或案例類型。
- 檔案清單與下一步；不可把 validator 通過寫成行為已驗證。

評估本 Skill 自身或設計測試時，使用 [evals/cases.json](evals/cases.json) 與 [evals/grader.md](evals/grader.md)。

