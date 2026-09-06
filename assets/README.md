# assets - 브랜딩 파생 사본

**여기 있는 파일을 손으로 고치지 않는다.** 정본은 NVL 저장소의 `nvl-branding/`이고,
이 폴더는 사이트와 버튼다운 메일이 URL로 가져다 쓰는 **서비스용 사본**이다.

    python scripts/brand-derive.py            # NVL 저장소에서 실행 - 파생 생성 + 여기로 배포
    python scripts/brand-derive.py --check    # 정본과 어긋난 사본 검출

| 파일 | 쓰임 |
|---|---|
| `logo-black-600.png` | 밝은 배경(메일 기본) |
| `logo-lime-600.png` | 어두운 배경. 메일 머리말 검정 띠 위 |
| `logo-white-600.png` | 라임 배경 위 |

새 브랜딩 자산은 `nvl-branding/` 아래 새 폴더에 만든다(2026-09-06 대표 지시).
