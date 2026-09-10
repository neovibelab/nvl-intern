# -*- coding: utf-8 -*-
"""어제의 나를 오늘의 집필 자리에 붙인다 (2026-09-11 신설).

**왜 필요한가.** 이 실험의 핵심은 **인턴이 자기 발행본을 보고 다음 편을 더 잘 쓰는 것**이다
(2026-09-11 대표 재확인 - 「이 목표가 모든 의사결정의 기준」). 그런데 실측해 보니
집필 프롬프트가 받는 것은 소재 · 두뇌 재료 · 자기 규칙 두 줄뿐이었다.
**자기가 쓴 지난 편을 한 편도 안 읽고 있었다.** 학습 경로가 주 1회 회고에서 나온 한 문장뿐이었다.

**무엇을 붙이나.** 직전 편의 **본문**과, 그 편이 받은 **검수 지적**과 **숫자**다.
규칙 문장으로 「같은 실수를 반복하지 않는다」고 적는 것보다 실물을 놓고 대조하는 쪽이 낫다.

**고치는 법은 여전히 주지 않는다.** 숫자와 지적만 준다. 무엇을 바꿀지는 인턴이 정한다.

**부작용을 적어 둔다.** 지난 편을 읽히면 문체가 앞 편으로 수렴할 수 있다. 수렴이 개선인지 모방인지는
규칙집 유무 대조군(다음 단계)과 지난 편 대결(`duel.growth_duels`)로만 갈린다.
"""
import io
import json

from . import config, form, publish


def _log(date: str) -> dict:
    try:
        return json.loads(io.open(config.LOG_DIR / f"{date}.json", encoding="utf-8").read())
    except Exception:  # noqa: BLE001
        return {}


def _body(slug: str, lang: str = "ko") -> str:
    """발행본에서 순수 본문만. 프레임·소재 카드·격자·베팅·검수 기록은 뺀다."""
    try:
        raw = io.open(config.CONTENT_DIR / lang / f"{slug}.md", encoding="utf-8").read()
    except FileNotFoundError:
        return ""
    rest = raw.split("---\n", 2)[-1]
    out, started = [], False
    for ln in rest.split("\n"):
        t = ln.strip()
        if t.startswith("**베팅** ·") or t.startswith("**원리** ·") or t.startswith("> **검수 기록**"):
            break
        if not started:
            if t.startswith("<sub>●") or t.startswith("**조짐** ·"):
                started = True
            continue
        if t.startswith("**조짐** ·") or t.startswith("<sub>"):
            continue
        out.append(ln)
    return "\n".join(out).strip()


def _scores(s: dict) -> str:
    f = s.get("form") or {}
    if not f:
        return ""
    t = f.get("title_check") or {}
    bits = []
    if t:
        bits.append(f"제목 - 무슨 얘긴지 알려주나 {t.get('clarity')}/2 · 읽고 싶게 하나 {t.get('pull')}/2"
                    + ("" if t.get("kept_promise", True) else " · **본문이 제목의 약속을 어겼다**"))
    bits.append(f"형식 {form.score(f)}/100 · 첫 문단에 누가 무엇을 언제 {'있음' if f.get('lead_concrete') else '없음'}"
                f" · AI tell {f.get('ai_tell')} · 헤지 만자당 {f.get('hedge_10k')} · 문장 중앙 {f.get('sent_med')}자")
    return " / ".join(bits)


def recent_block(date: str, n: int = 2, lang: str = "ko", cap: int = 2600) -> str:
    """직전 n편의 기록. 가장 최근 편만 본문을 통째로 붙이고 나머지는 제목·지적·숫자만."""
    stats = [s for s in publish._load(config.DATA_DIR / "stats.json", [])
             if s.get("type") != "weekly" and s.get("date", "") < date]
    rows = stats[-n:][::-1]
    if not rows:
        return ""
    out = []
    for i, s in enumerate(rows):
        lg = _log(s["date"])
        reviews = lg.get("reviews") or []
        issues = (reviews[-1].get("issues") or []) if reviews else []
        head = (f"[D+{s.get('day')} · {s['date']}] 「{s.get('title_ko')}」 "
                f"{s.get('factor')} {s.get('from_stage')}→{s.get('to_stage')} · {s.get('tense')}"
                + (" · 검수 미통과" if s.get("unresolved") else ""))
        block = [head]
        sc = _scores(s)
        if sc:
            block.append("  숫자 · " + sc)
        for x in issues[:2]:
            block.append("  검수 지적 · " + " ".join(str(x).split())[:180])
        if i == 0:
            b = _body(s["slug"], lang)
            if b:
                block.append("\n" + b[:cap])
        out.append("\n".join(block))
    return "\n\n".join(out)


RECENT_RULE_KO = """[지난 편 - 네가 직접 쓴 것]
{recent}

**위는 네가 쓴 글과 그 글이 받은 숫자·지적이다.** 오늘 글에 그대로 이어 붙이라는 뜻이 아니다.
- **같은 지적을 두 번 받지 않는다.** 위 지적이 오늘 글에도 해당되는지 쓰기 전에 확인한다.
- **숫자는 상태이지 처방이 아니다.** 무엇을 바꿀지는 네가 정한다. 아무도 고치는 법을 알려주지 않는다.
- **문체를 앞 편에 맞추지 않는다.** 어제와 같은 구조·같은 리듬으로 쓰면 나아진 게 아니라 굳은 것이다."""
