# -*- coding: utf-8 -*-
"""이미 나간 편도 새 읽기 순서로 맞춘다 (2026-09-16).

앞으로 나가는 편은 `publish.piece_markdown`이 새 순서로 조립하지만 지난 편들은 옛 순서로 서 있다.
사이트에서 위아래로 훑으면 **어떤 편은 본문이 세 번째 스크롤, 어떤 편은 첫 화면**이라 어지럽다.

로그에서 다시 만들지 않는다 - 09-06처럼 회전 기록이 없는 편이 있고, 다시 만들면 이름 표기 같은
후처리가 어긋난다. **이미 있는 마크다운의 덩어리를 옮기기만 한다.** 글자는 하나도 바뀌지 않는다.

    python scripts/relayout.py [--dry]
"""
import argparse
import io
import json
import pathlib
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from intern import config, publish  # noqa: E402

NL = chr(10)
HR = NL + NL + "---" + NL + NL
SRC_HEAD = ("**오늘의 소재**", "**Today's source**")
LINK_HEAD = {"ko": "**읽은 기사**", "en": "**What it read**"}


def blocks(body: str) -> list[str]:
    return [b for b in body.strip().split(NL + NL) if b.strip()]


def relayout(body: str, lang: str, region: str) -> str | None:
    """새 순서로 다시 세운다. 이미 새 순서면 None."""
    if "---" in blocks(body)[:4] or LINK_HEAD[lang] in body:
        return None
    bs = blocks(body)
    frame = coord = title = src_sum = grid = legend = None
    links: list[str] = []
    rest: list[str] = []
    for b in bs:
        t = b.strip()
        if frame is None and t.startswith("**"):
            frame = t
        elif coord is None and t.startswith("`["):
            coord = t
        elif title is None and t.startswith("# "):
            title = t
        elif src_sum is None and t.startswith(SRC_HEAD):
            src_sum = t
        elif t.startswith("- ["):
            links.append(t)
        elif grid is None and t.startswith("| |"):
            grid = t
        elif legend is None and t.startswith("<sub>●"):
            legend = t
        else:
            rest.append(t)
    if not (frame and coord and title):
        return None

    if region:
        coord = coord + f" · `{region}`"
    # 검수 기록(인용문) 앞에 근거 묶음을 끼운다. 그게 없으면 맨 끝 푸터 앞에.
    cut = next((i for i, b in enumerate(rest) if b.startswith("> ")), len(rest) - 1)
    meta_blocks = []
    if links:
        meta_blocks.append(LINK_HEAD[lang] + NL + NL + NL.join(links))
    if grid:
        meta_blocks.append(grid)
    if legend:
        meta_blocks.append(legend)

    head = [frame, "---", coord, title] + ([src_sum] if src_sum else [])
    mid = rest[:cut]
    tailing = rest[cut:]
    out = head + ["---"] + mid + (["---"] + meta_blocks if meta_blocks else []) + tailing
    return (NL + NL).join(out) + NL


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    done = skipped = 0
    for lang in ("ko", "en"):
        for path in sorted((config.CONTENT_DIR / lang).glob("*.md")):
            fm, body = publish.parse_piece(path)
            if not fm:
                continue
            region = fm.get("region") or ""
            if lang == "en":
                region = config.REGIONS_EN.get(region, region)
            new = relayout(body, lang, region)
            if new is None:
                skipped += 1
                continue
            print(f"  {lang}/{path.stem[:34]}")
            done += 1
            if args.dry:
                continue
            io.open(path, "w", encoding="utf-8", newline=NL).write(
                "---" + NL + json.dumps(fm, ensure_ascii=False, indent=1) + NL + "---" + NL + NL + new)
    print(f"재배열 {done}편 · 그대로 둔 것 {skipped}편" + (" (미저장)" if args.dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
