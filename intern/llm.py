# -*- coding: utf-8 -*-
"""Anthropic 호출 얇은 층. 모델 폴백·JSON 파싱·토큰 집계. 키 값은 절대 출력하지 않는다.

실측(2026-09-05): claude-sonnet-5는 temperature를 거부하고(400), 응답에 thinking 블록이 먼저 온다.
thinking이 max_tokens를 먹으면 text가 비어서 온다 → 비면 예산을 두 배로 한 번 다시 묻는다.
"""
import json
import re
import sys
from typing import Any

from anthropic import Anthropic, NotFoundError

from . import config

_client: Anthropic | None = None
USAGE = {"input": 0, "output": 0, "calls": 0, "search_uses": 0}
# 단계별 집계 (2026-09-18). 키 = (단계 함수 이름, 모델).
# 값 = {"input", "output", "calls", "search_uses"}.
# 호출부를 안 건드리려고 스택에서 단계 이름을 읽는다.
USAGE_BY_STEP: dict[tuple[str, str], dict[str, int]] = {}


def _caller_step() -> str:
    """이 모듈 밖 첫 호출자의 함수 이름. ask_json -> ask 같은 내부 중첩은 건너뛴다."""
    f = sys._getframe(1)
    while f is not None:
        name = f.f_globals.get("__name__", "")
        if not name.endswith(".llm"):
            return f.f_code.co_name
        f = f.f_back
    return "?"
# 검색 예산 (2026-09-18 조임 3 -> 2). 서버사이드 검색은 검색할 때마다 앞선 결과를
# 다시 읽어 입력이 누적으로 자란다. 주장 6개에 검색 12회가 붙고 있었다.
_SEARCH_USES = int(__import__("os").environ.get("INTERN_SEARCH_USES", "2"))
WEB_SEARCH_TOOL = [{"type": "web_search_20250305", "name": "web_search",
                    "max_uses": _SEARCH_USES}]


def client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic()
    return _client


def _create(model: str, **kw):
    try:
        return client().messages.create(model=model, **kw)
    except NotFoundError:
        fb = config.MODEL_FALLBACK.get(model)
        if not fb or fb == model:
            raise
        print(f"  [llm] 모델 {model} 없음 → {fb}")
        return client().messages.create(model=fb, **kw)


def _text_of(resp) -> str:
    parts = [b.text for b in resp.content if getattr(b, "type", "") == "text" and getattr(b, "text", "")]
    return "\n".join(parts).strip()


def ask(prompt: str, system: str = "", model: str | None = None, max_tokens: int = 4000,
        tools: list | None = None, temperature: float | None = None, _retry: bool = True) -> str:
    kw: dict[str, Any] = dict(max_tokens=max_tokens, messages=[{"role": "user", "content": prompt}])
    if system:
        kw["system"] = system
    if tools:
        kw["tools"] = tools
    used_model = model or config.MODEL_MAIN
    resp = _create(used_model, **kw)
    n_in = getattr(resp.usage, "input_tokens", 0) or 0
    n_out = getattr(resp.usage, "output_tokens", 0) or 0
    stu = getattr(resp.usage, "server_tool_use", None)
    n_ws = (getattr(stu, "web_search_requests", 0) or 0) if stu else 0
    USAGE["calls"] += 1
    USAGE["input"] += n_in
    USAGE["output"] += n_out
    USAGE["search_uses"] += n_ws
    # 단계별 (2026-09-18). 어느 단계가 값을 먹는지 보려면 합계로는 안 된다.
    slot = USAGE_BY_STEP.setdefault(
        (_caller_step(), getattr(resp, "model", used_model)),
        {"input": 0, "output": 0, "calls": 0, "search_uses": 0})
    slot["calls"] += 1
    slot["input"] += n_in
    slot["output"] += n_out
    slot["search_uses"] += n_ws
    text = _text_of(resp)
    if not text or resp.stop_reason == "max_tokens":
        print(f"  [llm] {'빈 응답' if not text else '잘림'} · stop={resp.stop_reason} · blocks={[getattr(b, 'type', '?') for b in resp.content]}"
              f" · out={getattr(resp.usage, 'output_tokens', 0)} · max={max_tokens}")
        if _retry:
            return ask(prompt, system=system, model=model, max_tokens=max_tokens * 2, tools=tools, _retry=False)
    return text


def ask_json(prompt: str, system: str = "", model: str | None = None, max_tokens: int = 4000,
             tools: list | None = None) -> dict:
    text = ask(prompt + "\n\n답은 JSON 하나만. 설명·코드펜스 없이.", system=system, model=model,
               max_tokens=max_tokens, tools=tools)
    return parse_json(text)


def parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.S)
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception as e:
            raise ValueError(f"JSON 파싱 실패: {str(e)[:80]} :: {text[:200]}")
    raise ValueError(f"JSON 없음 :: {text[:200]}")
# 100만 토큰당 (입력, 출력) 달러. 웹서치는 1,000건당 $10.
PRICE = {
    "claude-fable-5-1": (10.0, 50.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-haiku-4-5-20251001": (1.0, 5.0),
}


def cost_of(model: str, n_in: int, n_out: int, n_ws: int = 0) -> float:
    pin, pout = PRICE.get(model, PRICE.get(model.rsplit("-", 1)[0], (0.0, 0.0)))
    return n_in / 1e6 * pin + n_out / 1e6 * pout + n_ws * 0.01


def step_report() -> str:
    """단계별 비용표. 비싼 순. 어느 단계를 싼 모델로 내릴지 고르는 자리다."""
    rows = []
    for (step, model), v in USAGE_BY_STEP.items():
        rows.append((cost_of(model, v["input"], v["output"], v["search_uses"]),
                     step, model, v))
    rows.sort(reverse=True)
    total = sum(r[0] for r in rows) or 1.0
    out = ["", "단계별 비용 (합계 $%.3f)" % total,
           "%-22s %-26s %5s %10s %9s %5s %8s %6s"
           % ("단계", "모델", "호출", "입력", "출력", "검색", "비용", "비중")]
    for c, step, model, v in rows:
        out.append("%-22s %-26s %5d %10s %9s %5d %8s %5.1f%%"
                   % (step, model, v["calls"], "{:,}".format(v["input"]),
                      "{:,}".format(v["output"]), v["search_uses"],
                      "$%.3f" % c, c / total * 100))
    return "\n".join(out)
