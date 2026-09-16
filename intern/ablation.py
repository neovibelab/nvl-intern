# -*- coding: utf-8 -*-
"""두뇌 재료가 글을 **낫게 만드는가** (2026-09-16 신설, 대표 지시).

재료가 프롬프트에 들어간다는 것은 확정이다 - 편당 1만 5천~2만 자가 판정과 집필에 붙는다.
확정되지 않은 것은 **그게 소용이 있느냐**다. 파일명 어휘가 본문에 나타나는지로 재 봤더니
10편 중 4편이었는데, 렌즈는 단어가 아니라 관점을 주므로 **그 숫자는 아무것도 증명하지 않는다.**

대조군으로 가른다. **같은 소재·같은 판정·같은 지난 편으로 두 판을 쓴다.** 하나는 재료를 붙이고
하나는 맨몸이다. 판정자는 어느 쪽이 어느 쪽인지 모른다.

- 이기면 두뇌가 값을 한다. 승률이 얼마인지도 같이 나온다.
- **비기거나 지면 그게 더 중요한 결과다** - 매일 2만 자를 붙이면서 아무것도 안 사고 있다는 뜻이고,
  그러면 렌즈 고르는 법(`brain.retrieve`)을 고쳐야지 양을 늘릴 일이 아니다.

한 편에 집필 2회 + 판정 1회가 든다. 주간 회고가 **매주 2편씩** 돌려 표본을 쌓는다 -
한 번의 실험이 아니라 누적으로 본다. 표본이 작을 때 한 주 숫자를 추세로 읽지 않는다.
"""
import io
import json
import random

from . import config, duel, publish, steps

Q_KO = ("둘 다 같은 사건을 다룬 글이다. **어느 쪽이 더 나은 글인가.**\n"
        "볼 것 - 각도가 뻔하지 않은가 · 근거가 사건 밖으로 이어지는가 · "
        "다른 업종이 가져갈 것이 있는가 · 아는 소리를 반복하지 않는가.\n"
        "길이나 문체가 아니라 **말하는 내용**으로 고른다.")
Q_EN = ("Both pieces cover the same event. **Which one is better.**\n"
        "Look at - is the angle non-obvious, does the evidence reach beyond the event, "
        "is there something another industry can take, does it avoid restating what everyone knows.\n"
        "Judge the substance, not length or style.")


def one(date: str, lang: str = "ko") -> dict | None:
    """그날의 재료·판정으로 두 판을 새로 쓰고 블라인드로 붙인다.

    **발행본을 그대로 쓰지 않는다.** 발행본은 검수를 거쳤고 고쳐졌을 수 있어서,
    맨몸 초안과 붙이면 재료가 아니라 검수가 이긴 것을 재게 된다. 두 판 다 새로 쓴다.
    """
    lg = config.LOG_DIR / f"{date}.json"
    if not lg.exists():
        return None
    d = json.loads(io.open(lg, encoding="utf-8").read())
    cl = d.get("cluster") or {}
    if not cl.get("items"):
        return None
    cluster_text = "\n".join(f"- [{x.get('source')}] {x.get('title')}" for x in cl["items"])
    j = d.get("judgment") or {}
    if not j.get("angle_ko"):
        return None
    recent, extra = d.get("recent") or "", d.get("context") or ""

    from . import brain  # noqa: PLC0415 - 두뇌 경로가 없을 때 import만으로 죽지 않게
    mats = brain.retrieve(cluster_text)
    if not mats["text"]:
        print(f"  [ablation] {date} 두뇌 재료가 비었다 - 붙일 것이 없다")
        return None

    with_brain = steps.write_ko(cluster_text, j, mats["text"], recent, extra)
    bare = steps.write_ko(cluster_text, j, "", recent, extra)
    r = duel.compare(with_brain[:3500], bare[:3500], Q_KO if lang == "ko" else Q_EN, lang)
    winner = {"a": "brain", "b": "bare", "tie": "tie"}[r["winner"]]
    print(f"  [ablation] {date} · {winner} · {r['why'][:70]}")
    return {"date": date, "lang": lang, "winner": winner, "why": r["why"],
            "wiki": mats["wiki"], "lexicon": mats["lexicon"],
            "chars": {"brain": len(with_brain), "bare": len(bare), "materials": len(mats["text"])}}


def run(dates: list[str], lang: str = "ko") -> list[dict]:
    out = [x for x in (one(d, lang) for d in dates) if x]
    if out:
        log = publish._load(config.DATA_DIR / "brain_duels.json", [])
        log.extend(out)
        publish._dump(config.DATA_DIR / "brain_duels.json", log)
    return out


def pick_dates(rows: list[dict], n: int = 2) -> list[str]:
    """재료가 실제로 붙었던 날 중에서 고른다. 0건인 날을 붙이면 대조가 성립하지 않는다."""
    ok = [s["date"] for s in rows if (s.get("wiki_used") or 0) + (s.get("lexicon_used") or 0) > 0]
    random.shuffle(ok)
    return ok[:n]


def summary(lang: str = "ko") -> str:
    """누적 승률 한 줄. 회고가 읽는다."""
    log = publish._load(config.DATA_DIR / "brain_duels.json", [])
    if not log:
        return ("두뇌 대조: 아직 표본이 없다" if lang == "ko" else "Brain ablation: no samples yet")
    w = sum(1 for x in log if x["winner"] == "brain")
    b = sum(1 for x in log if x["winner"] == "bare")
    t = len(log) - w - b
    if lang == "ko":
        return (f"두뇌 재료를 붙인 판이 맨몸 판을 이긴 횟수 {w}/{len(log)} (맨몸 {b} · 비김 {t}). "
                f"**같은 소재·같은 판정으로 두 판을 새로 써서 블라인드로 붙인 것이다.** "
                f"이기지 못하면 렌즈를 고르는 법을 고쳐야 한다 - 양을 늘릴 일이 아니다.")
    return (f"Pieces written with the lab's lenses beat bare ones {w}/{len(log)} "
            f"(bare {b} · tie {t}). Same event, same call, both freshly written, judged blind.")
