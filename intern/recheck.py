# -*- coding: utf-8 -*-
"""되읽기 - 낸 글을 다시 읽고 그 뒤 나온 것을 확인한다 (2026-09-14 신설).

**왜.** 이 실험의 핵심은 반복 학습을 통한 관점의 성장이다(2026-09-11 대표 재확인). 그런데 지금까지
인턴은 **낸 글을 다시 보지 않았다.** 틀린 것이 드러나도 모르고, 이어 쓸 거리가 생겨도 모른다.

**무엇을 하나.** 주 1회, 지난 2주 발행분 중 **확인이 걸린 편**을 골라 그 뒤 무엇이 나왔는지 찾는다.
고르는 기준 셋 - 베팅이 걸린 편 · 검수를 통과 못 한 편 · 검증에서 반박되거나 확인 못 한 주장이 있던 편.

**세 가지 처분.**
- `correction` - 그 편의 사실이 틀렸음이 드러났다. 발행본에 **정정 블록을 덧붙인다.**
- `followup` - 이어 쓸 거리가 생겼다. 다음 소재 후보로 남긴다.
- `none` - 새로 나온 것이 없다.

**본문은 고치지 않는다.** 「틀린 날도 그대로 남긴다」가 이 실험의 규칙이라, 정정은 **덧붙이는 것**이지
고쳐 쓰는 것이 아니다. 발행본을 손보면 성장 곡선이 사후 수정으로 오염돼 나아진 것인지 고친 것인지
구분이 사라진다. **이미 나간 메일도 건드리지 않는다.**

**베팅 채점과 다르다.** 채점은 기한(90일 등)에 한 번 한다. 되읽기는 기한 전에 드러난 것을 기록만 한다.
"""
import datetime as dt
import io
import json

from . import config, publish, steps

WINDOW_DAYS = 14          # 되읽을 범위. 더 넓히면 호출이 늘고 좁히면 후속을 놓친다.
MAX_TARGETS = 4           # 한 회차에 볼 편 수. 주 1회 × 4편이면 호출 4회다.

JUDGE = """너는 발행된 글 한 편과 **그 뒤에 나온 사실**을 나란히 놓고 판정한다.

셋 중 하나다.
- `correction` - 그 글이 사실로 적은 것이 **틀렸음이 드러났다.** 예측이 빗나간 것은 여기가 아니다(그건 기한에 채점한다).
- `followup` - 사실은 틀리지 않았지만 **이어 쓸 거리가 생겼다.** 후속 사건·새 당사자·숫자가 나왔다.
- `none` - 새로 나온 것이 없거나 글과 무관하다.

**틀렸다고 말하려면 출처를 댄다.** 못 대면 `none`이다. 애매하면 `none`으로 내린다 -
정정은 발행본에 영구히 붙으므로 잘못 붙이는 비용이 크다."""


def targets(date: str) -> list[dict]:
    """확인이 걸린 편을 고른다. 베팅 · 검수 미해결 · 반박되거나 확인 못 한 주장."""
    y, m, d = map(int, date.split("-"))
    since = (dt.date(y, m, d) - dt.timedelta(days=WINDOW_DAYS)).isoformat()
    rows = [s for s in publish._load(config.DATA_DIR / "stats.json", [])
            if s.get("type") != "weekly" and since <= s.get("date", "") < date]
    done = {r["slug"] for r in publish._load(config.DATA_DIR / "recheck.json", [])}
    out = []
    for s in rows:
        if s["slug"] in done:
            continue
        why = []
        if s.get("bet"):
            why.append("베팅")
        if s.get("unresolved"):
            why.append("검수 미해결")
        if (s.get("claims_total") or 0) > (s.get("claims_verified") or 0):
            why.append(f"미확인 주장 {s['claims_total'] - s['claims_verified']}개")
        if why:
            out.append({**s, "why": " · ".join(why)})
    out.sort(key=lambda s: (not s.get("unresolved"), s["date"]))
    return out[:MAX_TARGETS]


def _piece_text(slug: str) -> str:
    try:
        raw = io.open(config.CONTENT_DIR / "ko" / f"{slug}.md", encoding="utf-8").read()
    except FileNotFoundError:
        return ""
    return raw.split("---\n", 2)[-1][:3000]


def run(date: str) -> list[dict]:
    """고른 편마다 그 뒤 나온 것을 찾고 처분을 정한다. 결과는 `data/recheck.json`에 쌓인다."""
    rows = targets(date)
    if not rows:
        print("  [recheck] 되읽을 편이 없다")
        return []
    bets = {b["slug"]: b for b in publish._load(config.DATA_DIR / "predictions.json", [])}
    out = []
    for s in rows:
        body = _piece_text(s["slug"])
        bet = bets.get(s["slug"]) or {}
        head = (f"[{s['date']} 발행] {s.get('title_ko')}\n"
                f"[좌표] {s.get('factor')} {s.get('from_stage')}→{s.get('to_stage')} · {s.get('tense')}\n"
                f"[그때 건 예측] {bet.get('claim_ko', '없음')}\n\n{body}")
        print(f"  [recheck] {s['date']} 「{str(s.get('title_ko'))[:26]}」 · {s['why']}")
        ctx = steps.context(head[:2500])
        block = steps.context_block(ctx)
        verdict = {"kind": "none", "why": "새로 나온 것이 없다", "source": ""}
        if block:
            try:
                verdict = steps.llm.ask_json(f"""[그때 쓴 글]
{head[:2500]}

[그 뒤 나온 것]
{block[:2500]}

JSON: {{"kind":"correction|followup|none","why":"한 줄","source":"매체와 URL"}}""",
                                            system=JUDGE, max_tokens=1500)
            except Exception as e:  # noqa: BLE001
                print(f"    판정 실패 {type(e).__name__}")
        kind = verdict.get("kind") if verdict.get("kind") in ("correction", "followup", "none") else "none"
        rec = {"slug": s["slug"], "date": s["date"], "checked": date, "why_picked": s["why"],
               "kind": kind, "why": str(verdict.get("why", ""))[:200],
               "source": str(verdict.get("source", ""))[:200], "found": block[:1200]}
        print(f"    → {kind} · {rec['why'][:70]}")
        out.append(rec)
    log = publish._load(config.DATA_DIR / "recheck.json", [])
    publish._dump(config.DATA_DIR / "recheck.json", log + out)
    return out


def apply_corrections(rows: list[dict]) -> int:
    """정정을 **발행본 아래에 덧붙인다.** 본문은 한 글자도 고치지 않는다."""
    n = 0
    for r in rows:
        if r["kind"] != "correction" or not r.get("why"):
            continue
        for lang in ("ko", "en"):
            p = config.CONTENT_DIR / lang / f"{r['slug']}.md"
            if not p.exists():
                continue
            s = io.open(p, encoding="utf-8").read()
            if "**정정**" in s or "**Correction**" in s:
                continue
            line = (f"\n> **정정** · {r['checked']} · {r['why']}"
                    f"{' (' + r['source'] + ')' if r.get('source') else ''}\n"
                    f">\n> 본문은 발행 당시 그대로 둡니다. 이 실험은 틀린 날도 지우지 않습니다.\n"
                    if lang == "ko" else
                    f"\n> **Correction** · {r['checked']} · {r['why']}"
                    f"{' (' + r['source'] + ')' if r.get('source') else ''}\n"
                    f">\n> The body is left as published. This experiment does not delete its mistakes.\n")
            io.open(p, "w", encoding="utf-8", newline="\n").write(s.rstrip() + "\n" + line)
            n += 1
    if n:
        print(f"  [recheck] 정정 블록 {n}곳에 덧붙였다")
    return n


def summary(rows: list[dict], lang: str = "ko") -> str:
    """회고 프롬프트에 넣을 한 줄. 없으면 없다고 적는다."""
    if not rows:
        return "되읽기: 이번 주에 확인이 걸린 편이 없었다" if lang == "ko" else "Re-read: nothing was due"
    c = sum(1 for r in rows if r["kind"] == "correction")
    f = sum(1 for r in rows if r["kind"] == "followup")
    lines = [f"지난 편 {len(rows)}개를 다시 읽었다. 정정 {c}건 · 이어 쓸 거리 {f}건."
             if lang == "ko" else
             f"Re-read {len(rows)} earlier pieces. Corrections {c}, follow-ups {f}."]
    for r in rows:
        if r["kind"] != "none":
            lines.append(f"  - [{r['kind']}] {r['date']} · {r['why'][:120]}")
    return "\n".join(lines)
