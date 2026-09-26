# -*- coding: utf-8 -*-
"""선정 후속 - 고른 것과 안 고른 것, 어느 쪽이 더 커졌나 (2026-09-26 신설).

**무엇을 재나.** 인턴이 후보 다섯 중 하나를 고른 날 이후 30일·90일 동안, 각 후보에 **후속 기사를 낸
매체가 몇 곳 붙었나.** 고른 것이 안 고른 넷보다 적게 컸으면 그날의 판단이 빗나간 것이다.
대표가 세운 첫 물음 「AI가 직접 뉴스를 셀렉할 수 있나」에 대한 가장 직접적인 자다.

**왜 매일 쌓나.** 레이더 기사 행은 시의성 10일이 지나면 지워진다(루트 지침 §5 「2종 수명제」).
30일 뒤에 한 번 조회하면 비교할 기사가 이미 없다. 그래서 **매일 회전이 불러온 최근 7일 기사**로
열려 있는 선정 기록을 갱신한다 - API 호출이 늘지 않고, 지워지기 전에 잡힌다.

**무엇으로 세나 - 한계를 적어 둔다.**
- 같은 사건인지는 제목 고유명사 셋 이상 공유로 본다(레이더 묶음과 같은 규칙). 거칠다.
- 세는 것은 **서로 다른 매체 수**다. 한국 매체는 받아쓰기가 많아 기사 수로 세면 한 건이 열 건으로 부푼다.
  매체 수도 완전하지 않다 - 새 사실을 더했는지까지는 못 본다. 이건 대리 지표다.
- 레이더가 수집하는 매체 범위 안에서만 센다. 레이더가 안 보는 곳에서 커진 사건은 안 잡힌다.

**되돌림 조건** - 3개월(인턴이 고른 편 40편 안팎)에 고른 것과 안 고른 것의 차이가 판정의 방향을
못 가르면(맞음·빗나감이 반반에서 안 벗어나면) 후속 매체 수가 중요도를 못 잰다는 뜻이다. 그때 접는다.
"""
import datetime as dt
import io
import json

from . import config, publish, radar

PATH = config.DATA_DIR / "selection_followup.json"
WINDOWS = (30, 90)
MIN_SHARED = 3
# 이 도메인에서 거의 모든 기사에 나오는 말. 레이더 토큰 규칙은 한국어 두 글자 이상을 다 뽑아서
# 이것들이 겹치면 다른 사건이 한 사건으로 묶인다(2026-09-26 실측 - 「潮玩 시장 1000억 위안」이
# 「미니드라마 시장 1000억 위안」에 걸렸다. 상위 40개 묶음 중 오탐은 이 한 건이었다).
COMMON = set("""시장 규모 매출 업계 산업 기업 음악 공연 발표 공개 올해 억원 위안 달러 엔화 성장 확대 돌파 기록
글로벌 한국 중국 일본 미국 아티스트 플랫폼 콘텐츠 엔터 엔터테인먼트""".split())


def _logs_with_selection(until: str) -> list[dict]:
    out = []
    for p in sorted(config.LOG_DIR.glob("*.json")):
        try:
            d = json.loads(io.open(p, encoding="utf-8").read())
        except Exception:  # noqa: BLE001
            continue
        sel = d.get("selection") or {}
        if sel.get("by") != "intern" or not sel.get("chosen") or d.get("date", "9") > until:
            continue
        out.append(d)
    return out


def _cands(sel: dict) -> list[dict]:
    rows = [dict(sel["chosen"], chosen=True)] + [dict(r, chosen=False) for r in sel.get("rejected") or []]
    return rows


def _matches(titles: list[str], row_title: str) -> bool:
    """같은 사건인가. **문턱은 후보 제목의 고유명사 수에 맞춘다** (2026-09-26 시험에서 잡았다).

    레이더 토큰 규칙은 영어에서 대문자로 시작하는 단어만 뽑는다. 「Suno UMG licensing deal expands」는
    {Suno, UMG} 둘뿐이라 「셋 이상 공유」로는 영영 안 걸린다 - 고른 사건의 후속이 체계적으로 0이 되고
    선정이 늘 빗나간 것으로 나왔을 것이다. 둘뿐이면 둘 다, 셋 이상이면 셋을 요구한다. 하나면 판정하지 않는다.
    """
    t = radar._tokens(row_title) - COMMON
    for x in titles:
        ct = radar._tokens(x or "") - COMMON
        if len(ct) < 2:
            continue
        if len(t & ct) >= min(MIN_SHARED, len(ct)):
            return True
    return False


def update(date: str, rows: list[dict]) -> int:
    """오늘 불러온 레이더 행으로 열려 있는 선정 기록을 갱신한다. 새로 판정한 수를 돌려준다."""
    book = {x["date"]: x for x in publish._load(PATH, [])}
    today = dt.date.fromisoformat(date)
    judged = 0
    for lg in _logs_with_selection(date):
        sd = lg["date"]
        age = (today - dt.date.fromisoformat(sd)).days
        if age < 1 or age > max(WINDOWS):
            continue
        rec = book.get(sd) or {"date": sd, "slug": "", "cands": []}
        if not rec["cands"]:
            rec["cands"] = [{"key": c["key"], "title": c.get("title", ""), "chosen": c["chosen"],
                             "own": list(c.get("item_ids") or []), "titles": c.get("titles") or [c.get("title", "")],
                             "sources": {}} for c in _cands(lg["selection"])]
        st = next((s for s in publish._load(config.DATA_DIR / "stats.json", []) if s.get("date") == sd), None)
        rec["slug"] = (st or {}).get("slug", rec.get("slug", ""))
        for r in rows:
            when = str(r.get("published_date") or r.get("created_at") or "")[:10]
            if not when or when <= sd:
                continue
            for c in rec["cands"]:
                if r.get("id") in c["own"] or not _matches(c["titles"], r.get("title", "")):
                    continue
                src = (r.get("source") or "").strip() or "?"
                # 매체마다 처음 본 날짜만 남긴다 - 30일·90일 창으로 자를 때 쓴다
                if src not in c["sources"] or when < c["sources"][src]:
                    c["sources"][src] = when
        for w in WINDOWS:
            key = f"d{w}"
            if age >= w and key not in rec:
                cut = (dt.date.fromisoformat(sd) + dt.timedelta(days=w)).isoformat()
                counts = [(c, sum(1 for d in c["sources"].values() if d <= cut)) for c in rec["cands"]]
                mine = next(n for c, n in counts if c["chosen"])
                others = [(c["title"], n) for c, n in counts if not c["chosen"]]
                top = max((n for _, n in others), default=0)
                rec[key] = {"chosen": mine, "others": others, "max_other": top,
                            "verdict": "hit" if mine >= top else "miss"}
                judged += 1
        latest = rec.get("d90") or rec.get("d30")
        if latest:
            hit = latest["verdict"] == "hit"
            n30 = rec.get("d90", rec.get("d30"))
            rec["verdict"] = latest["verdict"]
            rec["verdict_ko"] = (f"{'맞음' if hit else '빗나감'} · 고른 것 {n30['chosen']}곳 / 안 고른 것 중 최다 {n30['max_other']}곳")
            rec["verdict_en"] = (f"{'hit' if hit else 'miss'} · picked {n30['chosen']} outlets / best passed-over {n30['max_other']}")
        book[sd] = rec
    publish._dump(PATH, sorted(book.values(), key=lambda x: x["date"]))
    return judged


def rate(window: int = 30) -> tuple[int, int]:
    """(맞음, 판정 수)."""
    rows = [x.get(f"d{window}") for x in publish._load(PATH, []) if x.get(f"d{window}")]
    return sum(1 for r in rows if r["verdict"] == "hit"), len(rows)
