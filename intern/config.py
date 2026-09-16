# -*- coding: utf-8 -*-
"""경로·환경·어휘. 정본 = claude-NeoVibeLab/ai-intern/PROJECT.md."""
import io
import os
import pathlib
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content"
DATA_DIR = ROOT / "data"
LOG_DIR = DATA_DIR / "log"
DIST_DIR = ROOT / "dist"
RULES_FILE = ROOT / "rules" / "self-rules.md"
PROMPTS_DIR = ROOT / "prompts"

KST = timezone(timedelta(hours=9))


def load_env() -> None:
    """로컬은 형제 저장소의 .env를 읽고(값은 출력하지 않는다), Actions는 이미 주입돼 있다."""
    cands = [
        ROOT / ".env",
        ROOT.parent / "claude-NeoVibeLab" / "claude_API" / ".env",
        ROOT.parent / "claude-NeoVibeLab" / "nvl-vibe-radar" / ".env",
    ]
    for p in cands:
        if not p.exists():
            continue
        for line in io.open(p, encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()

BRAIN_DIR = pathlib.Path(os.environ.get("BRAIN_DIR") or (ROOT.parent / "claude-virtual-brain" / "llm-wiki"))
# 2026-09-06 Sonnet 5 → Opus 5. 근거 = 옆 세션 작성 모델 비교(두 소재·3회) - Sonnet은 분량 3/3 미달·사실 합성 1/3.
# 인턴 프롬프트 실측 = scripts/bakeoff.py · reports/bakeoff/RESULT.md
MODEL_MAIN = os.environ.get("INTERN_MODEL_MAIN", "claude-opus-5")
MODEL_FAST = os.environ.get("INTERN_MODEL_FAST", "claude-haiku-4-5")
MODEL_FALLBACK = {"claude-opus-5": "claude-sonnet-5", "claude-sonnet-5": "claude-sonnet-4-6",
                  "claude-haiku-4-5": "claude-haiku-4-5-20251001"}

FACTORS = ("IP", "포맷", "테크", "자본", "정책", "교차산업", "교차정체성")
STAGES = ("생산", "유통", "소비")
FACTORS_EN = {"IP": "IP", "포맷": "Format", "테크": "Tech", "자본": "Capital", "정책": "Policy",
              "교차산업": "Cross-industry", "교차정체성": "Cross-identity"}
STAGES_EN = {"생산": "production", "유통": "distribution", "소비": "consumption"}
# 저장값(레이더) ↔ 공개 어휘
# 세 번째 시제는 2026-09-10에 「배경」에서 「뉴스」로 바꿨다(대표 지시). 배경은 용도를 가리키는
# 이름이었고 독자가 알아야 하는 것은 성격이다 - 흐름이 아니라 그날의 사건. 옛 값도 계속 읽는다.
TENSE_FROM_RADAR = {"soon": "vibe", "now": "signal", "done": "news", "brief": "news", None: None}
TENSE_KO = {"vibe": "바이브", "signal": "시그널", "news": "뉴스", "background": "뉴스"}

# 2026-09-10 DNS 확인(A 76.76.21.21 · 프록시 꺼짐 · HTTPS 200)으로 정식 주소 복귀.
SITE_URL = os.environ.get("INTERN_SITE_URL", "https://intern.neovibelab.com")
LAB_URL = "https://www.neovibelab.com/"          # 연구소 - 인턴 사이트 어디서나 한 번에 돌아간다
ABOUT_URL = "https://www.neovibelab.com/lab/ai-intern"   # 2026-09-06 대표 지시 - 주소에서 「AI 인턴 실험」이 보여야 한다
NEWSLETTER_URL = "https://maily.so/draft.briefing?via=intern"
# 독자 신호는 레이더 서버를 경유한다. 정적 페이지에 Supabase 키를 심으면 레이더 표가 통째로 열린다.
FEEDBACK_API = os.environ.get("INTERN_FEEDBACK_API", "https://nvl-vibe-radar.vercel.app/api/intern-feedback")
# 소재가 어디 이야기인가(2026-09-16). 「한국이냐 아니냐」가 먼저 읽혀야 해서 한국이 맨 앞이고,
# 여러 곳이 걸치면 글로벌이다. 수집기 지역(`radar_items.region`)과 다른 축이다.
REGIONS = ["한국", "북미", "유럽", "일본", "중화권", "동남아", "글로벌"]
REGIONS_EN = {"한국": "Korea", "북미": "North America", "유럽": "Europe", "일본": "Japan",
              "중화권": "Greater China", "동남아": "Southeast Asia", "글로벌": "Global"}

BUTTONDOWN_USER = "nvl-intern"   # 구독 폼이 던지는 곳. 발송 계정과 같은 이름이라 여기 한 번만 적는다
LAUNCH_DATE = os.environ.get("INTERN_LAUNCH_DATE", "")  # D+N 계산 기준. 비면 첫 발행일


def today_kst() -> datetime:
    return datetime.now(KST)


def ensure_dirs() -> None:
    for d in (CONTENT_DIR / "ko", CONTENT_DIR / "en", DATA_DIR, LOG_DIR, DIST_DIR, RULES_FILE.parent, PROMPTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
