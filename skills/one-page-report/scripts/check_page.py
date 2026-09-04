#!/usr/bin/env python3
"""交付前檢查一頁式報告 HTML。

存在的理由：這些缺陷「能做對」不代表「每次都做對」——
同一批頁面裡，有的列印規則完整、有的只有兩條 display:none，
差別不在能力，在沒有一個會擋人的檢查點。

用法：
    python3 check_page.py <file.html> [--print] [--allow-external]

    --print           這頁會被印出來（列印規則從警告升為錯誤）
    --allow-external  允許外部連結（預設視為錯誤：交付物要能離線開）

退出碼：0 = 通過（可能有警告）／1 = 有錯誤／2 = 用法錯誤
"""
import argparse
import pathlib
import re
import sys

# 語意色票的規範命名。混用同義名（--ok / --good）會讓頁面之間無法沿用樣式。
CANON = {"good", "warn", "bad", "accent"}
ALIASES = {"ok": "good", "danger": "bad", "error": "bad", "success": "good", "caution": "warn"}


def check(path: pathlib.Path, for_print: bool, allow_external: bool):
    html = path.read_text(encoding="utf-8", errors="replace")
    errors, warns = [], []

    # 1) 自包含：外部連結／資源
    ext = sorted(set(re.findall(r'(?:src|href)="(https?://[^"]+)"', html)))
    if ext and not allow_external:
        errors.append(
            "外部連結 %d 個，交付物應自包含（離線可開）：\n      - %s"
            % (len(ext), "\n      - ".join(ext[:5]))
        )
    remote_asset = re.findall(r'<(?:img|script|link)[^>]+(?:src|href)="(?!data:|#)([^"]+)"', html)
    remote_asset = [u for u in remote_asset if not u.startswith(("http", "mailto:"))]
    if remote_asset:
        errors.append("引用了外部檔案，不是單檔：%s" % ", ".join(sorted(set(remote_asset))[:5]))

    # 2) 主題三態：宣告了 dark 就要三個入口都在，否則系統深色下會壞掉
    has_toggle_dark = '[data-theme="dark"]' in html
    has_prefers = "prefers-color-scheme" in html
    if has_toggle_dark and not has_prefers:
        errors.append('有 [data-theme="dark"] 但沒有 prefers-color-scheme —— 系統深色的人看到淺色')
    if has_prefers and not has_toggle_dark:
        warns.append("只跟隨系統深淺色，沒有手動切換；簡報時無法臨時改")

    # 3) 語意 token 命名
    used = set(re.findall(r"--([a-z]+)(?:-soft)?\s*:", html))
    bad_alias = sorted(used & set(ALIASES))
    if bad_alias:
        warns.append(
            "色票用了別名 %s，規範名是 %s"
            % (", ".join("--" + a for a in bad_alias), ", ".join("--" + ALIASES[a] for a in bad_alias))
        )

    # 4) 列印
    has_page = "@page" in html
    has_print_media = "@media print" in html
    coloured = bool(re.search(r"(background|background-color)\s*:\s*(var\(--|#|rgb)", html))
    if for_print or has_page:
        if not has_page:
            errors.append("宣告要列印卻沒有 @page（紙張大小與邊界未定）")
        if coloured and "print-color-adjust" not in html:
            errors.append("有色底但缺 print-color-adjust:exact —— 印出來色塊會整片消失")
        if "break-inside" not in html and "page-break-inside" not in html:
            errors.append("缺 break-inside:avoid —— 卡片會被切在兩頁之間")
    elif coloured and not has_print_media:
        warns.append("沒有任何列印規則；有人按 Cmd+P 就會拿到走版的版本")
    elif has_print_media:
        body = " ".join(re.findall(r"@media print\s*\{(.{0,400}?)\}\s*", html, re.S))
        if body and not re.search(r"(?<!display:none)(break-inside|print-color-adjust|@page|background)", body):
            warns.append("列印規則只有隱藏元素，等於沒有真的處理列印")

    # 5) 中文字型
    if re.search(r"[一-鿿]", html) and not re.search(
        r"PingFang|Noto Sans (TC|CJK)|Heiti|JhengHei", html
    ):
        warns.append("有中文但沒指定中文字型 stack，跨機器會掉字型")

    # 6) 體積
    kb = len(html.encode("utf-8")) // 1024
    if kb > 800:
        warns.append("檔案 %d KB，寄送與開啟都會變慢；圖片考慮壓縮" % kb)

    return errors, warns


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("files", nargs="+", type=pathlib.Path)
    ap.add_argument("--print", dest="for_print", action="store_true")
    ap.add_argument("--allow-external", action="store_true")
    args = ap.parse_args()

    failed = False
    for path in args.files:
        if not path.is_file():
            print("✗ %s：找不到檔案" % path)
            failed = True
            continue
        errors, warns = check(path, args.for_print, args.allow_external)
        head = "%s" % path.name
        if errors:
            failed = True
            print("🔴 %s" % head)
            for e in errors:
                print("    ✗ %s" % e)
        elif warns:
            print("🟡 %s" % head)
        else:
            print("✅ %s" % head)
        for w in warns:
            print("    ! %s" % w)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
