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

from intern import config, duel, issues, learn, publish  # noqa: E402

FB_API = "https://nvl-vibe-radar.vercel.app/api/intern-feedback"

# 통로가 생긴 날. 그전 편을 「끊김」이라고 부르면 검사가 늑대를 외친다 - 아직 없던 것이다.
SINCE = {"두뇌 재료": "2026-09-05", "지난 편": "2026-09-11", "추가 정보": "2026-09-14",
         "문체": "2026-09-05", "본문 추출": "2026-09-05",
         # 2026-09-26 - 고르는 판단(인턴이 골랐나) · 잇는 판단(같은 판의 지난 글을 읽었나)
         "선정": "2026-09-26", "스레드": "2026-09-26"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()

    stats = [s for s in publish._load(config.DATA_DIR / "stats.json", []) if s.get("type") != "weekly"]
    rows = stats[-args.days:]
    dead = []

    print(f"== 편별 통로 · 최근 {len(rows)}편\n")
    print("날짜         두뇌  지난편  추가정보  문체  본문추출  선정  스레드")
    iss = issues.load()
    for s in rows:
        slug, date = s["slug"], s["date"]
        brain_n = (s.get("wiki_used") or 0) + (s.get("lexicon_used") or 0)
        lg = config.LOG_DIR / f"{date}.json"
        recent_n = ctx_n = -1
        sel_by, thr_n, has_prior = "", -1, False
        if lg.exists():
            d = json.loads(io.open(lg, encoding="utf-8").read())
            recent_n = len(d.get("recent") or "")
            ctx_n = len(d.get("context") or "")
            sel_by = (d.get("selection") or {}).get("by", "")
            thr_n = (d.get("issue") or {}).get("thread_chars", -1)
        iid = iss["pieces"].get(slug)
        has_prior = bool(iid) and len(issues.members(iss, iid, before=date)) > 0
        body_n = len(learn._body(slug))
        style_ok = bool(s.get("style"))
        cells = (("두뇌 재료", brain_n > 0, brain_n), ("지난 편", recent_n > 50, recent_n),
                 ("추가 정보", ctx_n > 50, ctx_n), ("문체", style_ok, 1 if style_ok else 0),
                 ("본문 추출", body_n > 300, body_n),
                 # 선정 - 인턴이 골랐으면 OK. 코드로 떨어졌으면(선정 실패) 끊김
                 ("선정", sel_by == "intern", 1 if sel_by == "intern" else 0),
                 # 스레드 - 같은 판에 지난 글이 있는데 집필 자리에 안 붙었으면 끊김. 새 판이면 붙일 게 없다
                 ("스레드", (not has_prior) or thr_n > 50, max(thr_n, 0)))
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
    # 대장에는 by_days가 없고 by_date만 있다. 전에는 by_days를 찾다 못 찾아 전부 90일로 셌다 -
    # 180일짜리 예측도 90일 만기로 잡혀 「첫 만기 12-04」라고 보고했는데 실제는 12-05였다(2026-09-26 발견).
    dues = [dt.date.fromisoformat(p["by_date"]) for p in preds if p.get("by_date")]
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

    # 잇는 판단 - 판이 몇 개이고, 종합할 때가 된 판이 있나, 종합 편이 이기나
    tomorrow = (today + dt.timedelta(days=1)).isoformat()
    live = [(iid, len(issues.members(iss, iid)), len(issues.unsynth(iss, iid))) for iid in iss["issues"]]
    ripe = [x for x in live if issues.ripe(iss, x[0], tomorrow)]
    multi = [x for x in live if x[1] >= 2]
    print(f"  이어 쓰는 판  {len(iss['issues'])}개 · 두 편 이상 {len(multi)}개 · 종합할 때가 된 판 {len(ripe)}개"
          + (f" (가장 많이 쌓인 판 {max(x[2] for x in live)}편)" if live else ""))
    w, t = duel.synth_rate()
    print(f"  종합 편 대결  {w}/{t}" + ("   ← 과반을 못 넘으면 종합 모드를 끈다(표본 6)" if t else "   ← 아직 종합 편이 없다"))
    fu = publish._load(config.DATA_DIR / "selection_followup.json", [])
    picked = [s for s in stats if s.get("selected_by") == "intern"]
    print(f"  선정 후속     인턴이 고른 편 {len(picked)} · 30일 판정 {sum(1 for x in fu if x.get('verdict'))}건"
          + ("" if fu else "   ← 첫 판정은 고른 날로부터 30일 뒤"))

    print("\n" + ("전부 돈다" if not dead else f"끊긴 자리 {len(dead)}건\n  - " + "\n  - ".join(dead)))
    return 0 if not dead else 1


if __name__ == "__main__":
    sys.exit(main())
