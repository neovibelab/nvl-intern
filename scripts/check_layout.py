# -*- coding: utf-8 -*-
"""새 레이아웃이 그대로 나갔는지 한 번에 본다 (2026-09-16 신설).

2026-09-16에 읽는 순서와 라벨을 한꺼번에 바꿨다. 바꾼 자리가 여럿이고 **그중 하나는
학습 통로를 조용히 끊었었다**(격자 범례를 본문 시작 표시로 쓰던 코드). 그런 종류는
사람이 눈으로 훑어서는 안 잡힌다. 그래서 검사를 남긴다.

    python scripts/check_layout.py [--date 2026-09-17]

보는 것 여섯.
1. 읽는 순서 - 소재 요약이 본문보다 앞, 원문·격자가 본문보다 뒤
2. 라벨 - 새 이름만 있고 옛 이름(베팅·원리·오늘의 소재·검수 기록)은 없다
3. 구분선 - 세 덩어리를 가르는 `---`가 셋
4. 지역 - 좌표 줄에 붙었다
5. **본문 추출** - `learn`·`duel`이 빈 문자열을 돌려주지 않는다(학습 통로)
6. 메일 - 격자 표가 빠지고 한 줄로 바뀌었다
"""
import argparse
import datetime as dt
import io
import pathlib
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from intern import config, duel, learn, mail, publish  # noqa: E402

OLD = ("**베팅**", "**원리**", "**오늘의 소재**", "**검수 기록**", "**읽은 기사**",
       "**Bet**", "**Principle**", "**Today's source**", "**What it read**")
NEW_KO = ("**무슨 일이 있었나**", "**예측**", "**가져갈 것**", "**원문**", "**발행 전 검사**")
NEW_EN = ("**What happened**", "**Prediction**", "**Takeaway**", "**Sources**")


def check(date: str) -> int:
    bad = []

    def ok(cond, label, detail=""):
        print(("  OK   " if cond else "  실패 ") + label + (f" · {detail}" if detail else ""))
        if not cond:
            bad.append(label)

    stats = publish._load(config.DATA_DIR / "stats.json", [])
    row = next((s for s in stats if s["date"] == date), None)
    if not row:
        print(f"{date} 기록이 없다 - 회전이 아직 안 돌았거나 날짜가 틀렸다")
        return 2
    slug = row["slug"]
    print(f"== {date} · {row.get('title_ko', '')[:44]}\n")

    for lang, news in (("ko", NEW_KO), ("en", NEW_EN)):
        p = config.CONTENT_DIR / lang / f"{slug}.md"
        if not p.exists():
            ok(False, f"[{lang}] 발행본 파일")
            continue
        fm, body = publish.parse_piece(p)
        print(f"[{lang}]")

        i_sum = body.find(news[0])
        i_body = body.find("---", body.find("---") + 3)
        i_src = body.find(news[3])
        i_grid = body.find("| |")
        ok(0 <= i_sum < i_body, "요약이 본문보다 앞")
        ok(i_src > i_body, "원문 목록이 본문보다 뒤")
        ok(i_grid > i_body, "격자가 본문보다 뒤")
        ok(all(x in body for x in news), "새 라벨 전부", " · ".join(x.strip("*") for x in news))
        leftover = [x for x in OLD if x in body]
        ok(not leftover, "옛 라벨 없음", ("남음: " + ", ".join(leftover)) if leftover else "")
        ok(body.count("\n---\n") >= 3, "구분선 셋", f"{body.count(chr(10) + '---' + chr(10))}개")
        region = fm.get("region") or ""
        shown = config.REGIONS_EN.get(region, region) if lang == "en" else region
        ok(bool(shown) and f"`{shown}`" in body, "지역이 좌표 줄에", shown)

        d = duel._plain(body)
        ok(len(d) > 300, "duel 본문 추출", f"{len(d)}자")
        if lang == "ko":
            l = learn._body(slug)
            ok(len(l) > 300, "learn 본문 추출", f"{len(l)}자")
        m = mail.strip_grid(body.strip(), lang)
        ok("| |" not in m, "메일에서 격자 표 제거")
        ok("격자 21칸" in m or "21-cell grid" in m, "메일에 격자 링크 한 줄")
        print()

    print("전부 통과" if not bad else f"실패 {len(bad)}건 · " + " / ".join(bad))
    return 0 if not bad else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    args = ap.parse_args()
    date = args.date or dt.datetime.now(config.KST).strftime("%Y-%m-%d")
    return check(date)


if __name__ == "__main__":
    sys.exit(main())
