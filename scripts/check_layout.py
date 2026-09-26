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

import re  # noqa: E402

OLD = ("**베팅**", "**원리**", "**오늘의 소재**", "**검수 기록**", "**읽은 기사**",
       "**Bet**", "**Principle**", "**Today's source**", "**What it read**")
# 2026-09-26 개편 - 예측이 본문에서 빠지고 「왜 이걸 골랐나」가 들어왔다. 종합 편은 머리가 다르다.
SWITCH = "2026-09-26"
NEW_KO = ("**무슨 일이 있었나**", "**가져갈 것**", "**원문**", "**발행 전 검사**")
NEW_EN = ("**What happened**", "**Takeaway**", "**Sources**")
SYN_KO = ("**이어 본 판**", "**오늘 더해진 것**", "**가져갈 것**", "**지난 판단 되읽기**", "**이 판의 지난 글**", "**원문**")
SYN_EN = ("**Reading the thread**", "**What today adds**", "**Takeaway**", "**Checking earlier calls**",
          "**Earlier on this thread**", "**Sources**")
# 본문 문장 속 예측 - 칸을 빼도 집필 프롬프트가 「본문 안에 자기 문장으로 넣는다」고 시켜서 남아 있었다
FORECAST = re.compile(r"\d+\s*일\s*안에|\d+\s*일\s*이내|within \d+ days|in the next \d+ days")
HEAD_MAX = 4      # 머리 블록 상한 - 본문에 닿기 전에 지치지 않게(2026-09-16 대표 지적)


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
    # 회고 편(`type: weekly`)은 소재 편의 레이아웃을 안 쓴다 - 요약·예측·격자·좌표가
    # 애초에 없다. 그걸 모르고 같은 기준을 대면 **멀쩡한 회고가 매주 실패 12건으로
    # 뜬다**(2026-09-18 실측 - 09-17 소재 편은 전부 통과였는데 검사 기본값이 오늘이라
    # 회고를 봤다). 회고에도 유효한 것 셋만 본다 - 옛 라벨·본문 추출·메일 격자 제거.
    weekly = row.get("type") == "weekly"
    synth = bool(row.get("synth"))
    new_era = date >= SWITCH
    print(f"== {date} · {row.get('title_ko', '')[:44]}\n")

    for lang, news in (("ko", SYN_KO if synth else NEW_KO), ("en", SYN_EN if synth else NEW_EN)):
        p = config.CONTENT_DIR / lang / f"{slug}.md"
        if not p.exists():
            ok(False, f"[{lang}] 발행본 파일")
            continue
        fm, body = publish.parse_piece(p)
        print(f"[{lang}]")

        i_sum = body.find(news[1] if synth else news[0])   # 종합 편은 「오늘 더해진 것」이 요약 자리다
        i_body = body.find("---", body.find("---") + 3)
        i_src = body.find("**원문**" if lang == "ko" else "**Sources**")
        i_grid = body.find("| |")
        if not weekly:
            ok(0 <= i_sum < i_body, "요약이 본문보다 앞")
            ok(i_src > i_body, "원문 목록이 본문보다 뒤")
            ok(i_grid > i_body, "격자가 본문보다 뒤")
        if not weekly:
            ok(all(x in body for x in news), "종합 편 라벨 전부" if synth else "새 라벨 전부",
               " · ".join(x.strip("*") for x in news if x not in body) or "")
        if not weekly and new_era:
            # 2026-09-26 이후 편 - 예측이 본문에 없어야 한다(칸도, 문장도)
            parts = body.split(chr(10) + "---" + chr(10))
            main = parts[2] if len(parts) > 2 else body
            ok("**예측** ·" not in body and "**Prediction** ·" not in body, "예측 칸이 본문에 없다")
            hits = FORECAST.findall(main)
            ok(not hits, "본문 문장 속 예측 없음", ", ".join(hits[:3]))
            head = parts[1] if len(parts) > 1 else ""
            blocks = [b for b in head.split(chr(10) + chr(10)) if b.strip().startswith("**")]
            ok(len(blocks) <= HEAD_MAX, "머리 블록 넷 이하", f"{len(blocks)}개")
            if row.get("selected_by") == "intern":
                ok(("**왜 이걸 골랐나**" if lang == "ko" else "**Why this one**") in head, "왜 이걸 골랐나가 머리에")
            if synth:
                rr = [ln for ln in main.split(chr(10)) if ln.startswith("- ")]
                ok(len(rr) >= 2, "되읽기 두 줄 이상", f"{len(rr)}줄")
        leftover = [x for x in OLD if x in body]
        ok(not leftover, "옛 라벨 없음", ("남음: " + ", ".join(leftover)) if leftover else "")
        ok(body.count("\n---\n") >= 3, "구분선 셋", f"{body.count(chr(10) + '---' + chr(10))}개")
        # 좌표는 2026-09-17부터 코드 스팬 한 줄에 사람 말로 들어간다.
        # 지역도 그 줄 안에 있고 따로 백틱을 갖지 않는다.
        region = fm.get("region") or ""
        shown = config.REGIONS_EN.get(region, region) if lang == "en" else region
        coord = next((l for l in body.split(chr(10)) if l.startswith("`") and l.endswith("`")), "")
        if not weekly:
            ok(bool(shown) and shown in coord, "지역이 좌표 줄에", coord.strip("`")[:52])
        if not weekly:
            ok("→" not in coord or fm.get("from_stage") != fm.get("to_stage"),
               "같은 단계를 두 번 쓰지 않는다", coord.strip("`")[:52])

        # 추출은 길이만 보지 않는다 - 머리·원문·격자가 새어 들면 길이는 넉넉한데 통로는 오염된 것이다.
        # 09-26에 duel 추출이 원문 목록과 격자 표까지 읽고 있던 것을 이 기준으로 잡았다.
        leak_marks = ("**원문**", "**Sources**", "| |", "발행 전 검사", "**무슨 일이 있었나**", "**조짐**",
                      "**왜 이걸 골랐나**", "**이어 본 판**", "**이 판의 지난 글**")
        d = duel._plain(body)
        dl = [w for w in leak_marks if w in d]
        ok(len(d) > 400 and not dl, "duel 본문 추출", f"{len(d)}자" + (f" · 샘: {', '.join(dl)}" if dl else ""))
        if lang == "ko":
            l = learn._body(slug)
            ll = [w for w in leak_marks if w in l]
            ok(len(l) > 400 and not ll, "learn 본문 추출", f"{len(l)}자" + (f" · 샘: {', '.join(ll)}" if ll else ""))
        m = mail.strip_grid(body.strip(), lang)
        ok("| |" not in m, "메일에서 격자 표 제거")
        if not weekly:
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
