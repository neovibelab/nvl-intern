# -*- coding: utf-8 -*-
"""비교 판정 - 「몇 점인가」 대신 「어느 쪽이 나은가」를 묻는다 (2026-09-10 신설).

**왜 바꿨나.** 0~2 절대 척도가 변별하지 못했다. 6편 실측에서 「읽고 싶나」가 여섯 편 모두 1/2였다.
분산이 0이면 정보도 0이다. 사람도 제목 하나에 절대 점수를 매기지 못한다 - 둘을 놓고 고를 뿐이다.
그래서 판정을 **비교**로 바꾼다. 순서는 매번 섞고, 어느 쪽이 새 것인지 판정자에게 알려주지 않는다.

**한계를 적어 둔다.** 이건 대리 측정이다. 진짜 자는 독자 행동(제목 A/B의 오픈율·클릭)이고
구독자가 붙으면 켠다. 그때 이 판정이 실제 오픈율을 맞혔는지 대조해야 판정자 자체가 검증된다.
대리 측정을 정답 자리에 두지 않는다.
"""
import random
import re

from . import llm

JUDGE_KO = """너는 한국 엔터 업계에서 일하는 독자다. 글을 쓴 사람이 아니다.
두 개를 나란히 놓고 **어느 쪽이 나은지 하나만 고른다.** 점수를 매기지 않는다.

- 둘 중 하나를 반드시 고른다. 비기는 판정은 정말로 구별이 안 될 때만 쓴다.
- 어느 쪽이 먼저 쓰였는지, 누가 썼는지 모른다. 순서에 의미는 없다.
- 고른 이유를 한 줄로 댄다. **무엇이 그렇게 만들었는지**를 대야 한다. 「더 좋다」는 이유가 아니다."""

JUDGE_EN = """You are a reader working in the entertainment industry, not the writer.
Put the two side by side and **pick one.** Do not score them.

- Pick one. Use a tie only when they are genuinely indistinguishable.
- You do not know which came first or who wrote either. Order means nothing.
- Give one line saying what made the difference. "Better" is not a reason."""

TITLE_Q = """어느 제목이 나은가. 세 가지로 본다.
①**소재와 사건**이 제목에 서 있나 - 이름·수치가 있고, 동사가 무슨 일인지 말하나.
②**긴장**이 있나 - 반전·대비·미지수 중 하나. 단 **관용적 물음표는 미지수가 아니다** -
소재만 갈아 끼우면 아무 글에나 붙는 물음(「~할까?」)은 긴장으로 치지 않는다.
단 수치·고유명사가 박힌 물음은 그 글에만 붙으므로 긴장으로 친다.
③본문이 그 제목의 **약속**을 지키나.
비유만 남은 쪽에 후하지 마라 - 무슨 산업 얘긴지 모르겠으면 진 것이다.
설명만 있고 긴장이 없는 쪽도 진다. 둘 다 갖춘 쪽이 이긴다."""

BODY_Q = """어느 글이 나은가. 업계 사람이 읽고 **가져갈 것이 있는 쪽**이다.
사건을 세우고 논지를 밀고 반례를 다뤘나. 근거 없는 단정과 회피형 어미가 적은 쪽.
문장이 읽히는 쪽. 길다고 낫지 않고 단정한다고 낫지 않다."""


def compare(a: str, b: str, question: str, lang: str = "ko") -> dict:
    """A와 B 중 하나를 고른다. 순서를 섞어 자리 편향을 없앤다. 돌려주는 winner는 'a'·'b'·'tie'."""
    flip = random.random() < 0.5
    x, y = (b, a) if flip else (a, b)
    head = "[1번]\n%s\n\n[2번]\n%s" % (x, y)
    ask = (f"{question}\n\n{head}\n\nJSON: {{\"pick\":1|2|0,\"why\":\"한 줄. 0은 비김\"}}" if lang == "ko"
           else f"{question}\n\n{head}\n\nJSON: {{\"pick\":1|2|0,\"why\":\"one line. 0 means tie\"}}")
    try:
        d = llm.ask_json(ask, system=JUDGE_KO if lang == "ko" else JUDGE_EN, max_tokens=1200)
    except Exception as e:  # noqa: BLE001
        print(f"  [duel] 실패 {type(e).__name__}")
        return {"winner": "tie", "why": ""}
    pick = int(d.get("pick") or 0)
    if pick not in (1, 2):
        return {"winner": "tie", "why": str(d.get("why", ""))[:160]}
    first_is_a = not flip
    winner = "a" if (pick == 1) == first_is_a else "b"
    return {"winner": winner, "why": str(d.get("why", ""))[:160]}


def pick_title(cands: list[dict], body: str, lang: str = "ko") -> dict:
    """제목 후보들을 토너먼트로 좁힌다. 첫 안이 살아남았는지도 기록한다 - 스스로 고를 수 있나의 지표다."""
    cands = [c for c in cands if (c.get("title") or "").strip()]
    if not cands:
        return {}
    best, rounds = cands[0], []
    for c in cands[1:]:
        q = f"{TITLE_Q}\n\n[본문]\n{body[:2400]}" if lang == "ko" else f"{TITLE_Q}\n\n[Body]\n{body[:2400]}"
        r = compare(best["title"], c["title"], q, lang)
        rounds.append({"a": best["title"], "b": c["title"], "winner": r["winner"], "why": r["why"]})
        if r["winner"] == "b":
            best = c
    kept = best is cands[0]
    print(f"  [title-duel] {lang} {len(cands)}안 → 「{best['title']}」" + (" (첫 안 유지)" if kept else " (바꿨다)"))
    return {"best": best, "rounds": rounds, "kept_first": kept, "n": len(cands)}


def _plain(md: str) -> str:
    """발행본에서 프레임·소재 카드·격자·검수 기록을 뺀 본문만 남긴다. 날짜와 D+N도 지운다."""
    body, started = [], False
    for ln in md.split("\n"):
        t = ln.strip()
        if t.startswith("**베팅** ·") or t.startswith("> **검수 기록**"):
            break
        if not started:
            if t.startswith("<sub>●") or t.startswith("**조짐** ·"):
                started = True
            continue
        if t.startswith("**조짐** ·") or t.startswith("<sub>"):
            continue
        body.append(ln)
    out = "\n".join(body).strip()
    return re.sub(r"D\+\d+|20\d\d-\d\d-\d\d", "", out)


def growth_duels(new_pieces: list[dict], old_pieces: list[dict], lang: str = "ko") -> list[dict]:
    """이번 주 편을 지난 편과 맞붙인다. **어느 쪽이 최신인지 알려주지 않는다.**

    절대 점수로는 성장이 안 보인다. 「지난달의 나보다 나은가」가 성장의 정의에 가깝고,
    그건 비교로만 답이 나온다. 축을 제목과 글 전체로 나눠 무엇이 늘었는지 갈라 본다.
    """
    if not new_pieces or not old_pieces:
        return []
    out = []
    for np_ in new_pieces:
        op = random.choice(old_pieces)
        nb, ob = _plain(np_["md"]), _plain(op["md"])
        # 제목끼리만 붙인다. 본문을 함께 주면 본문 품질이 제목 판정으로 새어 든다.
        r_t = compare(np_["title"], op["title"], TITLE_Q, lang)
        r_b = compare(nb[:3500], ob[:3500], BODY_Q, lang)
        for axis, r in (("제목", r_t), ("본문", r_b)):
            out.append({"axis": axis, "new": np_["slug"], "old": op["slug"],
                        "winner": {"a": "new", "b": "old", "tie": "tie"}[r["winner"]], "why": r["why"]})
        print(f"  [duel] {np_['slug'][:28]} vs {op['slug'][:28]} · 제목 {out[-2]['winner']} · 본문 {out[-1]['winner']}")
    return out


def win_rate(duels: list[dict], axis: str | None = None) -> tuple[int, int]:
    """(이긴 수, 비김 제외 전체). 50%를 넘으면 지난 편보다 낫다는 뜻이다."""
    rows = [d for d in duels if axis is None or d["axis"] == axis]
    dec = [d for d in rows if d["winner"] != "tie"]
    return sum(1 for d in dec if d["winner"] == "new"), len(dec)
