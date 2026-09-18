# 엔터 바이브 리서치 · AI 인턴 1호

엔터문화연구소(Neo Vibe Lab)의 AI 인턴 1호가 매일 글로벌 엔터 산업을 읽고 한 편 쓴다. 사람이 고르지도 고치지도 않는다. 얼마나 자라는지 공개로 본다.

- 설계 정본: `claude-NeoVibeLab/ai-intern/PROJECT.md`
- 소개 페이지: https://www.neovibelab.com/intern
- 본체(이 repo의 `dist/`): https://intern.neovibelab.com

## 비용 (2026-09-18 실측)

한 편 **$1.51** · 평일 기준 월 **약 $32**. 단계별 내역은 실행 끝에 `step_report()`가 찍고 `trace["usage_by_step"]`에 남는다.

- **집필·판정은 4분의 1이 안 된다.** `write_ko`·`write_en`·`judge` 셋을 합쳐 18%다. 2026-09-06 모델 벤치의 「편당 $0.21」은 `write_ko` 하나를 잰 값이고 지금도 맞다. 나머지는 벤치가 보지 않은 자리에서 나간다.
- **사실 검증을 haiku로 내렸다** (2026-09-18 대표 지시). 하는 일이 판단이 아니라 「이 주장이 출처에 있나」 대조이고, 판정 어휘가 셋으로 닫혀 있으며, 실패하면 `unverified`로 떨어져 `hedge`가 문장을 눅인다. 모델은 `INTERN_MODEL_VERIFY`로 되돌린다.
  - 실측 = 호출당 $0.1358 -> $0.0404, **70% 감소**(소재가 달라도 호출당은 비교된다). 단계 순위도 1위에서 3위로 내려갔다.
- **검색을 3회에서 2회로 조였다.** 서버사이드 검색은 검색할 때마다 앞선 결과를 다시 읽어 입력이 누적으로 자란다. `INTERN_SEARCH_USES`로 조정한다.
- **되돌림 조건** - `unverified` 비율이 2주 연속 절반을 넘으면 검증을 Opus로 되돌린다. 검증이 안 되면 hedge가 문장을 눅여 글이 흐려진다.

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
