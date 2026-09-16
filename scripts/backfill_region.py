# -*- coding: utf-8 -*-
"""이미 나간 편에 지역을 소급해 찍는다 (2026-09-16).

앞으로는 판정이 같이 찍지만 지난 편에는 그 칸이 없다. **빈 칸으로 두면 목록에서 지역이 있는
편과 없는 편이 섞여 「한국이냐 아니냐」를 물어볼 수 없게 된다.**

**발행본을 기준으로 돈다.** 기록(`stats.json`)에 빠진 편이 있어도 사이트에 서 있으면 채운다
(09-06 편이 그랬다). 회전 기록이 없으면 그 편이 스스로 적어 둔 소재 요약을 쓴다.
소재 제목만 보고 빠른 모델이 고른다 - 본문 전체가 필요한 판단이 아니다. 회고는 소재가 없어 건너뛴다.

    python scripts/backfill_region.py [--dry]
"""
import argparse
import io
import json
import pathlib
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")   # 윈도 콘솔 기본값(cp949)이 줄표에서 죽는다
except Exception:  # noqa: BLE001
    pass

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from intern import config, llm, publish  # noqa: E402

NL = chr(10)


def pick(titles: list[str]) -> str:
    d = llm.ask_json(
        "아래 뉴스가 **어디 이야기인가** 하나 고른다. 기사가 실린 매체가 아니라 사건이 벌어진 곳이다."
        + NL + "여러 지역에 걸쳐 있으면 「글로벌」." + NL + "눈금: " + " | ".join(config.REGIONS) + NL + NL
        + NL.join(f"- {t}" for t in titles[:6])
        + NL + NL + 'JSON: {"region": "..."}',
        model=config.MODEL_FAST, max_tokens=300)
    r = str(d.get("region") or "").strip()
    return r if r in config.REGIONS else "글로벌"


def write_fm(path, region: str) -> None:
    fm, body = publish.parse_piece(path)
    if not fm:
        return
    fm["region"] = region
    io.open(path, "w", encoding="utf-8", newline=NL).write(
        "---" + NL + json.dumps(fm, ensure_ascii=False, indent=1) + NL + "---" + NL + body)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    config.load_env()

    stats = publish._load(config.DATA_DIR / "stats.json", [])
    by_slug = {x.get("slug"): x for x in stats}
    done = 0
    for path in sorted((config.CONTENT_DIR / "ko").glob("*.md")):
        fm, _ = publish.parse_piece(path)
        if not fm or fm.get("type") == "weekly" or fm.get("region"):
            continue
        slug, date = path.stem, fm.get("date", "")
        titles = []
        lg = config.LOG_DIR / f"{date}.json"
        if lg.exists():
            d = json.loads(io.open(lg, encoding="utf-8").read())
            titles = [x.get("title") for x in (d.get("cluster") or {}).get("items", []) if x.get("title")]
        if not titles:
            summary = (fm.get("source_summary") or "").strip()
            titles = [x for x in (fm.get("title"), summary) if x]
        if not titles:
            print(f"  소재를 못 찾았다 {slug} - 건너뛴다")
            continue
        r = pick(titles)
        print(f"  {date} · {r} · {titles[0][:50]}")
        if args.dry:
            continue
        for lang in ("ko", "en"):
            q = config.CONTENT_DIR / lang / f"{slug}.md"
            if q.exists():
                write_fm(q, r)
        if slug in by_slug:
            by_slug[slug]["region"] = r
        done += 1
    if not args.dry:
        publish._dump(config.DATA_DIR / "stats.json", stats)
    print(f"지역 채움 {done}편" + (" (미저장)" if args.dry else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
