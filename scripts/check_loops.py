# -*- coding: utf-8 -*-
"""학습 통로가 실제로 도는지 잰다 (2026-09-16 신설).

이 프로젝트의 핵심은 **인턴이 자기가 발행한 글을 학습해 다음 편을 더 낫게 쓰는 것**이다.
그런데 통로는 조용히 끊긴다 - 2026-09-16 하루에만 둘이 끊겨 있었다.

- `learn._body`·`duel._plain`이 격자 범례를 본문 시작 표시로 쓰고 있었는데 레이아웃을 바꾸면서
  **본문이 빈 문자열**로 나왔다. 화면으로는 멀쩡했다.
- 두뇌 저장소가 안 붙은 날(09-07~09) 회전이 **재료 0건으로 그냥 돌았다.** 워크플로가 그렇게 설계돼
  있다(`BRAIN_PAT 없으면 재료 없이 간다`) - 멈추지 않는 것은 맞지만 **끊긴 줄도 모른다.**

「하나라도 0이면 성장 지표는 의미가 없다」(`ai-intern/PROJECT.md`)를 사람 눈이 아니라 여기서 잰다.

    python scripts/check_loops.py [--days 7]
"""
import argparse
import datetime as dt
import io
import json
import pathlib
import sys
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from intern import config, duel, learn, publish  # noqa: E402

FB_API = "https://nvl-vibe-radar.vercel.app/api/intern-feedback"

# 통로가 생긴 날. 그전 편을 「끊김」이라고 부르면 검사가 늑대를 외친다 - 아직 없던 것이다.
SINCE = {"두뇌 재료": "2026-09-05", "지난 편": "2026-09-11", "추가 정보": "2026-09-14",
         "문체": "2026-09-05", "본문 추출": "2026-09-05"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()

    stats = [s for s in publish._load(config.DATA_DIR / "stats.json", []) if s.get("type") != "weekly"]
    rows = stats[-args.days:]
    dead = []

    print(f"== 편별 통로 · 최근 {len(rows)}편\n")
    print("날짜         두뇌  지난편  추가정보  문체  본문추출")
    for s in rows:
        slug, date = s["slug"], s["date"]
        brain_n = (s.get("wiki_used") or 0) + (s.get("lexicon_used") or 0)
        lg = config.LOG_DIR / f"{date}.json"
        recent_n = ctx_n = -1
        if lg.exists():
            d = json.loads(io.open(lg, encoding="utf-8").read())
            recent_n = len(d.get("recent") or "")
            ctx_n = len(d.get("context") or "")
        body_n = len(learn._body(slug))
        style_ok = bool(s.get("style"))
        cells = (("두뇌 재료", brain_n > 0, brain_n), ("지난 편", recent_n > 50, recent_n),
                 ("추가 정보", ctx_n > 50, ctx_n), ("문체", style_ok, 1 if style_ok else 0),
                 ("본문 추출", body_n > 300, body_n))
        out = []
        for name, ok, n in cells:
            if date < SINCE[name]:
                out.append("  -  ")          # 그날엔 없던 통로다
                continue
            out.append(("OK " if ok else "끊김") + f"{n:>4}")
            if not ok:
                dead.append(f"{date} {name}")
        print(date + "  " + " ".join(out))

    print("\n== 상시 통로\n")
    try:
        t = io.open(config.RULES_FILE, encoding="utf-8").read()
        ls = [l for l in t.splitlines() if l.startswith("- ")]
        last = (ls[-1].split(")")[0].strip("- (") if ls else "-")
        print(f"  자기 규칙     {len(ls)}줄 · 최근 승격 {last}")
    except FileNotFoundError:
        print("  자기 규칙     파일 없음")
        dead.append("자기 규칙 파일")

    preds = publish._load(config.DATA_DIR / "predictions.json", [])
    today = dt.datetime.now(config.KST).date()
    dues = []
    for p in preds:
        y, m, dd = map(int, p["date"].split("-"))
        dues.append(dt.date(y, m, dd) + dt.timedelta(days=int(p.get("by_days") or 90)))
    if dues:
        nearest = min(dues)
        print(f"  예측 채점     {len(preds)}건 · 첫 만기 {nearest} ({(nearest - today).days}일 뒤)")
    else:
        print("  예측 채점     0건")
        dead.append("예측")

    tot = 0
    for s in rows:
        try:
            with urllib.request.urlopen(f"{FB_API}?slug={urllib.parse.quote(s['slug'])}", timeout=15) as r:
                tot += sum((json.load(r).get("counts") or {}).values())
        except Exception:  # noqa: BLE001
            pass
    print(f"  독자 신호     최근 {len(rows)}편에 {tot}표" + ("   ← 바깥에서 오는 유일한 정답" if tot else "   ← 0. 안쪽 판정만 돌고 있다"))

    print("\n" + ("전부 돈다" if not dead else f"끊긴 자리 {len(dead)}건\n  - " + "\n  - ".join(dead)))
    return 0 if not dead else 1


if __name__ == "__main__":
    sys.exit(main())
