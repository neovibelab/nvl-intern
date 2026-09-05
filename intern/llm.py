# -*- coding: utf-8 -*-
"""Anthropic 호출 얇은 층. 모델 폴백·JSON 파싱·토큰 집계. 키 값은 절대 출력하지 않는다.

실측(2026-09-05): claude-sonnet-5는 temperature를 거부하고(400), 응답에 thinking 블록이 먼저 온다.
thinking이 max_tokens를 먹으면 text가 비어서 온다 → 비면 예산을 두 배로 한 번 다시 묻는다.
"""
import json
import re
from typing import Any

from anthropic import Anthropic, NotFoundError

from . import config

_client: Anthropic | None = None
USAGE = {"input": 0, "output": 0, "calls": 0, "search_uses": 0}
WEB_SEARCH_TOOL = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}]


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
    resp = _create(model or config.MODEL_MAIN, **kw)
    USAGE["calls"] += 1
    USAGE["input"] += getattr(resp.usage, "input_tokens", 0) or 0
    USAGE["output"] += getattr(resp.usage, "output_tokens", 0) or 0
    stu = getattr(resp.usage, "server_tool_use", None)
    USAGE["search_uses"] += (getattr(stu, "web_search_requests", 0) or 0) if stu else 0
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
