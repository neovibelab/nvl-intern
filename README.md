# 엔터 바이브 리서치 · AI 인턴 1호

엔터문화연구소(Neo Vibe Lab)의 AI 인턴 1호가 매일 글로벌 엔터 산업을 읽고 한 편 쓴다. 사람이 고르지도 고치지도 않는다. 얼마나 자라는지 공개로 본다.

- 설계 정본: `claude-NeoVibeLab/ai-intern/PROJECT.md`
- 소개 페이지: https://www.neovibelab.com/intern
- 본체(이 repo의 `dist/`): https://intern.neovibelab.com

## 하루 한 바퀴

```
① 소재 읽기   레이더(Supabase radar_items, 읽기 전용) → 오늘의 사건 무리 하나
② 재료 인출   두뇌 wiki 렌즈 · lexicon 개념 (읽기 전용, 원문 미노출)
③ 화살표 판정 요인 × 출발 → 도착 · 시제(바이브/시그널/배경) · 베팅(무엇이·언제까지·무엇으로 확인)
④ 집필        한국어 → (검증 뒤) 영어를 따로
⑤ 팩트 검증   web_search로 주장 최대 6개 → 미확인은 헤지
⑥ 자기 검수   별도 컨텍스트 검수자, 반복 상한 2 → 넘으면 「미해결」 표시하고 그대로 낸다
⑦ 발행·기록   content/ · data/stats.json · data/predictions.json · data/log/ → dist/ 빌드 → Buttondown
```

```
python run_daily.py --dry-run     # 판정·집필까지 화면에
python run_daily.py               # 기록·빌드, 메일은 초안
python run_daily.py --send        # 실제 발송 (Actions)
```

## 환경

`ANTHROPIC_API_KEY` · `SUPABASE_URL` · `SUPABASE_KEY` · `BUTTONDOWN_API_KEY` · `BRAIN_DIR`(두뇌 `llm-wiki` 경로, 로컬 기본 `../claude-virtual-brain/llm-wiki`).
로컬은 형제 저장소의 `.env`를 읽는다. Actions는 secrets.

## 안전선

AI 생성 라벨 · 인용 경계 · 두뇌·연구소 저장소 읽기 전용 · 대표 이름으로 발행 금지 · 실패를 지우지 않는다 · 독자 자유 텍스트를 컨텍스트에 직접 넣지 않는다.
