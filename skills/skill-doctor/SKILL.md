---
name: skill-doctor
provenance: 自建（2026-08-26）
user-invocable: true   # 2026-08-26 加。⚠️ 當時理由是「沒這欄叫不動」，實測證偽（14 支全都叫得動）。留著只為與另外 4 支一致，此欄實際用途未知。
description: 掃你的 skill 目錄健康度：斷引用、硬編絕對路徑、description 被 Codex 截斷、provenance 缺漏。**只回報不改檔**。觸發：「skill 健檢」「skill 有沒有問題」「check skills」。
---

# skill-doctor

掃**使用者 skill 目錄**下每一支 skill 的健康度，**回報清單，不改任何檔案**。

修不修、怎麼修，由主對話跟使用者決定。

## 用法

派工給 `skill-doctor:skill-auditor` subagent。它只有 Read／Grep／Glob，**改不壞任何東西**。

## 四項檢查

| # | 檢查 | 判準 |
|---|---|---|
| 1 | **斷引用** | 文件裡 `` `檔名` `` 形式的引用，實際解析得到嗎 |
| 2 | **硬編絕對路徑** | 有沒有家目錄開頭的絕對路徑（macOS 是 `Users`、Linux 是 `home`）。換機器會斷且不報錯 |
| 3 | **description 截斷** | 觸發詞與排除條件有沒有落在**前 123 字元**內 |
| 4 | **provenance** | frontmatter 有沒有標來歷（決定能不能散布） |

## 🔴 最容易做錯的一件事（2026-08-26 實際踩過三次）

**命中不等於問題。** 同一天我跑這個掃描三次，報了 **70 筆 → 17 筆 → 0 筆**，前兩次全是假警報：

| 假警報 | 真相 |
|---|---|
| `tw-chokepoint-analysis` 引用 `scripts/fetch_data.py` | 那是**專案目錄**的檔案，不在 skill 目錄 |
| `personal-wiki` 引用 `INDEX.md`、`_sources.md` | 那是**它自己會產生**的檔案，本來就不該預先存在 |
| `tw-chokepoint-analysis` 引用 `_skeleton.md` | 那是 `run_monthly.py` 的**產出物** |
| `create-good-skills` 提到 `skill-creator` | 出現在 **changelog 講外部產品**，不是引用 |

**每一筆都要解析到實際路徑才能報。** 報一份假清單比不報更糟 —— 它會讓人以為掃過了。

## 完成條件

- 每一筆都附**檔名與行號**，以及「為什麼判定是問題」
- 解析不到的引用要說明**試過哪些基準路徑**，不能只說「找不到」
- 沒問題就明講「N 支全部通過」，不要為了交差硬找東西
