# -*- coding: utf-8 -*-
"""문체를 목록이 아니라 **사람 분포와의 거리**로 잰다 (2026-09-16 신설).

**금칙 목록으로는 AI티가 안 잡힌다.** 대조 공식·메타 수사·줄표를 0으로 만들어도 글은 여전히
기계가 쓴 것처럼 읽힌다. 차이는 어느 단어를 썼나가 아니라 **문장이 얼마나 고르게 생겼나**에 있다.

**자는 대표 발행본이다.** 2025년 이후 리서치·칼럼 60편의 분포를 기준선으로 두고, 인턴 글이
그 분포의 몇 퍼센타일에 있는지를 잰다. 10~90 밖이면 「사람 분포 밖」이다.
**무엇이 AI티인지 우리가 정하지 않는다** - 두 코퍼스가 실제로 갈린 축만 남겼다(2026-09-16 실측).

**드러난 것 - 규칙이 만든 AI티가 있다.** 인턴은 수식어를 **한 번도** 안 쓰고(대표 만자당 5.8),
접속부사가 절반이며 쉼표가 3분의 2다. 금칙을 피하라는 지시가 문장을 메마르게 만든 결과다.
헤지만 반대 방향이다(인턴 9.5 대 대표 0).

**고치는 법은 주지 않는다.** 숫자와 방향만 준다 - 「수식어를 써라」는 규칙을 넣으면 그 순간
다시 목록 게임이 되고, 인턴은 자기 문장이 아니라 우리 자를 맞추게 된다.

**되돌림 조건** - 분포 거리가 줄었는데 사람 기준선 대결 승률이 안 오르면 이 축은 폐기한다.
거리가 좁혀지는 것 자체는 값이 아니다.
"""
import io
import json
import re
import statistics as st

from . import config

BASELINE = config.ROOT / "reports" / "style-baseline.json"

CONJ = r"그러나|하지만|또한|즉|따라서|반면|그리고|그래서|다만|물론"
HEDGE = r"알려졌|로 보입니다|인 듯|가능성이 (있|높)|것으로 보|수 있습니다"
MODIF = r"매우|상당히|특히|크게|분명히|확실히|충분히|명확히"

# 2026-09-16 실측에서 대표 분포와 갈린 다섯. 방향은 「대표 쪽이 어디인가」다.
AXES = {
    "문장 리듬": "높을수록 들쭉날쭉",
    "접속부사": "만자당",
    "헤지": "만자당",
    "수식어": "만자당",
    "쉼표": "만자당",
}


def measure(text: str) -> dict:
    """모델을 쓰지 않는다. 전부 세는 것이다. 링크 표기는 벗기고 센다."""
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text or "")
    sents = [s.strip() for s in re.split(r"(?<=다)\.\s|(?<=요)\.\s|[.!?]\s|\n\n", t) if len(s.strip()) > 5]
    lens = [len(s) for s in sents] or [1]
    chars = max(1, len(re.sub(r"\s", "", t)))
    per10k = lambda p: round(len(re.findall(p, t)) / chars * 10000, 1)  # noqa: E731
    return {
        "문장 리듬": round(st.pstdev(lens) / (st.mean(lens) or 1), 3),
        "접속부사": per10k(CONJ),
        "헤지": per10k(HEDGE),
        "수식어": per10k(MODIF),
        "쉼표": round(t.count(",") / chars * 10000, 1),
    }


def baseline() -> dict:
    try:
        return json.loads(io.open(BASELINE, encoding="utf-8").read())
    except FileNotFoundError:
        return {}


def bounds(base: dict | None = None) -> dict:
    """축마다 대표 분포의 p10·p90 **값**. 순위가 아니라 값으로 가른다 -
    헤지처럼 0이 몰린 축에서는 순위가 헛짚는다(대표와 같은 0인데 「0% 지점」으로 잡혔다)."""
    base = base if base is not None else baseline()
    out = {}
    for k, col in (base.get("axes") or {}).items():
        if not col:
            continue
        c = sorted(col)
        out[k] = (c[int(len(c) * 0.10)], c[min(len(c) - 1, int(len(c) * 0.90))])
    return out


def percentiles(m: dict, base: dict | None = None) -> dict:
    """각 축이 대표 분포의 어디쯤인가. 보고용 위치값이고 판정은 `off_axes`가 한다."""
    base = base if base is not None else baseline()
    out = {}
    for k, v in m.items():
        col = (base.get("axes") or {}).get(k)
        if not col:
            continue
        out[k] = round(sum(1 for x in col if x < v) / len(col) * 100)
    return out


def off_axes(m: dict, base: dict | None = None) -> list[str]:
    """대표 분포의 p10~p90 값 구간을 벗어난 축. 이것이 그날의 「AI티」다."""
    bd = bounds(base)
    return [k for k, v in m.items() if k in bd and not (bd[k][0] <= v <= bd[k][1])]


def line(m: dict, pct: dict, lang: str = "ko") -> str:
    """회고·집필 자리에 붙일 한 덩어리. 숫자와 방향만 준다."""
    if not pct:
        return "문체 거리: 기준선이 아직 없다" if lang == "ko" else "Style gap: no baseline yet"
    off = off_axes(m)
    head = (f"대표 발행본 60편을 자로 놓았다. 사람 분포 밖으로 나간 축 {len(off)}개."
            if lang == "ko" else
            f"Measured against 60 pieces written by a human. Axes outside that distribution: {len(off)}.")
    rows = []
    for k in m:
        if k not in pct:
            continue
        lo, hi = bounds().get(k, (None, None))
        mark = f" **밖** (사람은 {lo}~{hi})" if k in off else ""
        rows.append(f"  - {k} {m[k]} · 사람 분포의 {pct[k]}% 지점{mark}")
    return head + "\n" + "\n".join(rows)
