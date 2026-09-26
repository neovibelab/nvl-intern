# -*- coding: utf-8 -*-
"""① 소재 읽기 - 레이더(Supabase radar_items)를 읽기 전용으로 가져와 오늘의 사건 무리 하나를 고른다.

버튼도 큐도 안 거친다. 정본 = ai-intern/PROJECT.md 「매일 파이프라인」 ①.
"""
import collections
import json
import os
import re
from datetime import timedelta

import requests

from . import config

COLUMNS = "id,title,url,summary,region,source,collector,tense,factor,stage,event_key,published_date,created_at"
STOP = set("""the a an of and or for to in on with new his her its at by is are will can more music industry says said
how why what who this that from about after before over under into 가운데 그리고 하지만 대한 위해 통해 관련 지난 오는
최근 이번 올해 내년 대해 라며 했다 한다 있다 없다""".split())


def _headers() -> dict:
    key = os.environ.get("SUPABASE_KEY", "")
    return {"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"}


def fetch_live(hours: int = 168) -> list[dict]:
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/radar_items"
    cutoff = (config.today_kst() - timedelta(hours=hours)).isoformat()
    params = {"select": COLUMNS, "status": "in.(pending,picked)", "created_at": f"gte.{cutoff}",
              "is_entertainment": "eq.true", "order": "created_at.desc"}
    out, offset, page = [], 0, 500
    while True:
        h = dict(_headers(), **{"Range-Unit": "items", "Range": f"{offset}-{offset + page - 1}"})
        r = requests.get(url, headers=h, params=params, timeout=30)
        if r.status_code == 400 and "is_entertainment" in params:
            params.pop("is_entertainment"); continue
        r.raise_for_status()
        rows = r.json()
        out.extend(rows)
        if len(rows) < page:
            break
        offset += page
    return [r for r in out if r.get("collector") != "interview"]


def _tokens(title: str) -> set:
    words = re.findall(r"[A-Z][A-Za-z0-9&'.-]{2,}|[가-힣]{2,}|[一-龥]{2,}|[ァ-ヶー]{2,}", title or "")
    return {w for w in words if w.lower() not in STOP}


def cluster(rows: list[dict]) -> list[dict]:
    """event_key가 있으면 그것으로, 없으면 제목 고유명사 3개 공유로 묶는다(레이더와 같은 규칙)."""
    groups: dict[str, list[dict]] = collections.defaultdict(list)
    loose = []
    for r in rows:
        if r.get("event_key"):
            groups[r["event_key"]].append(r)
        else:
            loose.append(r)
    for r in loose:
        t = _tokens(r.get("title", ""))
        placed = False
        for k, g in groups.items():
            if any(len(t & _tokens(x.get("title", ""))) >= 3 for x in g):
                g.append(r); placed = True; break
        if not placed:
            groups[f"t:{r['id']}"].append(r)
    out = []
    for k, g in groups.items():
        tenses = collections.Counter(x.get("tense") for x in g if x.get("tense"))
        factors = collections.Counter(x.get("factor") for x in g if x.get("factor"))
        stages = collections.Counter(x.get("stage") for x in g if x.get("stage"))
        out.append({
            "key": k, "items": g, "n": len(g),
            "radar_tense": tenses.most_common(1)[0][0] if tenses else None,
            "factor": factors.most_common(1)[0][0] if factors else None,
            "stage": stages.most_common(1)[0][0] if stages else None,
            "latest": max(x.get("published_date") or x.get("created_at") or "" for x in g),
            "regions": sorted({x.get("region") for x in g if x.get("region")}),
        })
    return out


def used_keys() -> set:
    used = set()
    for p in config.LOG_DIR.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            for k in d.get("cluster", {}).get("item_ids", []):
                used.add(k)
            if d.get("cluster", {}).get("key"):
                used.add(d["cluster"]["key"])
        except Exception:
            pass
    return used


def _public(c: dict) -> bool:
    return any((x.get("url") or "").startswith("http") and "mail.google.com" not in (x.get("url") or "") for x in c["items"])


def _score(c: dict) -> tuple:
    tense_rank = {"soon": 3, "now": 2, None: 1, "done": 0, "brief": -1}.get(c["radar_tense"], 1)
    coord = 1 if (c["factor"] and c["stage"]) else 0
    col = max({"vibe_search": 3, "gnews": 2, "newsroom": 2, "newsletter": 1}.get(x.get("collector"), 1) for x in c["items"])
    return (tense_rank, coord, col, c["n"], c["latest"])


def candidates(clusters: list[dict], exclude: set, n: int = 5) -> list[dict]:
    """오늘의 후보 n개. **여기까지만 코드가 한다** (2026-09-26).

    전에는 정렬 맨 위를 그대로 썼다(`pick_today`) - 소재를 인턴이 고른 적이 없었다.
    대표가 세운 첫 물음이 「AI가 직접 뉴스를 셀렉할 수 있나」였는데 그 물음이 한 번도 시험되지 않았다.
    이제 코드는 쓸 수 없는 것(이미 쓴 것·끝난 것·원문 없는 것)을 걸러 다섯으로 좁히고,
    **고르는 것은 인턴이 한다**(`steps.select`). 정렬은 후보를 좁히는 데만 쓴다.
    """
    cands = [c for c in clusters if c["key"] not in exclude
             and not any(x["id"] in exclude for x in c["items"])
             and c["radar_tense"] not in ("brief", "done") and _public(c)]
    cands.sort(key=_score, reverse=True)
    out = cands[:n]
    for c in out:
        c["item_ids"] = [x["id"] for x in c["items"]]
    return out


def pick_today(clusters: list[dict], exclude: set) -> dict | None:
    """정렬 맨 위 하나. **선정이 실패했을 때의 대체**로만 쓴다(2026-09-26).

    「곧」(soon) 우선, 그다음 「지금」(now)·미분류. 소스 수·최신순. 이미 쓴 사건은 뺀다.
    2026-09-06 뒤집음. 전에는 now가 위였고 D+1·D+2가 둘 다 signal로 나왔다. 레이더 기본 화면이
    바이브이고 소개 페이지가 「아직 오지 않은 변화」를 약속하는데 선택이 반대를 향하고 있었다.
    """
    c = candidates(clusters, exclude, n=1)
    return c[0] if c else None


def describe(c: dict, max_items: int = 6) -> str:
    lines = []
    for x in c["items"][:max_items]:
        lines.append(f"- [{x.get('region')}/{x.get('source')}] {x.get('title')}\n  {(x.get('summary') or '')[:400]}\n  {x.get('url')}")
    return "\n".join(lines)
