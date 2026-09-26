# -*- coding: utf-8 -*-
"""엔터 바이브 리서치 · AI 인턴 1호 - 하루 한 바퀴.

  python run_daily.py                 # 소재 읽기 → 판정 → 집필 → 검증 → 검수 → 기록 → 사이트 빌드 (메일은 초안만)
  python run_daily.py --send          # Buttondown 실제 발송 (Actions에서)
  python run_daily.py --dry-run       # 판정·집필까지만, 파일 안 씀
  python run_daily.py --date 2026-09-05

사람은 없다. 정본 = claude-NeoVibeLab/ai-intern/PROJECT.md.
"""
import argparse
import json
import sys
import time

from intern import ablation, config, duel, llm, radar, brain, steps, publish, build_site, mail, weekly, form, learn, recheck, style, issues

MAX_REVIEW_ROUNDS = 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=config.today_kst().strftime("%Y-%m-%d"))
    ap.add_argument("--send", action="store_true", help="Buttondown 실제 발송")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--hours", type=int, default=168, help="레이더 창(시간)")
    ap.add_argument("--no-brain", action="store_true")
    ap.add_argument("--rebuild", action="store_true", help="그날 로그의 판정·최종 원고로 발행물만 다시 만든다(LLM은 소재 요약·표기 정리만)")
    ap.add_argument("--force", action="store_true", help="그날 이미 발행했어도 다시 쓴다")
    ap.add_argument("--weekly", action="store_true", help="요일과 무관하게 주간 회고를 쓴다")
    ap.add_argument("--daily", action="store_true", help="요일과 무관하게 데일리를 쓴다")
    args = ap.parse_args()
    if args.rebuild:
        return rebuild(args)
    # 리듬은 **도착 기준**이다 - 월~금 한 편 · 토요일 회고 · 일요일 없음.
    # 발송이 다음 날 08:00 예약으로 바뀌었으므로(2026-09-14) 작성 요일은 한 칸 앞이다.
    #   작성  일 월 화 수 목 | 금(회고) | 토(휴재)
    #   도착  월 화 수 목 금 | 토        | -
    # 회고를 토요일 도착으로 둔 이유는 일요일 열람률이 낮아서다(2026-09-06 대표 판단, 그대로 유효).
    y, m, d = map(int, args.date.split("-"))
    wd = __import__("datetime").date(y, m, d).weekday()      # 0=월 … 4=금 5=토 6=일
    if args.weekly or (wd == 4 and not args.daily):
        return run_weekly(args)
    if wd == 5 and not args.daily:
        print("  [rhythm] 토요일은 쉰다(일요일 도착분이 없다). 기록만 남긴다.")
        publish._dump(config.LOG_DIR / f"{args.date}.json", {"date": args.date, "rest": True})
        return 0
    config.ensure_dirs()
    # 하루 한 편. 손으로 돌린 날 예약 실행이 또 돌면 같은 날짜에 두 편이 생긴다(2026-09-10 신설).
    if not args.force and any(x.get("date") == args.date for x in publish._load(config.DATA_DIR / "stats.json", [])):
        print(f"  [rhythm] {args.date}는 이미 발행했다. 다시 쓰려면 --force")
        return 0
    t0 = time.time()
    trace: dict = {"date": args.date, "steps": {}}
    print(f"== AI 인턴 1호 · {args.date} · model {config.MODEL_MAIN}")

    # ① 소재 읽기
    rows = radar.fetch_live(args.hours)
    clusters = radar.cluster(rows)
    print(f"  [radar] 살아있는 행 {len(rows)} · 무리 {len(clusters)}")
    # ①' 고르기 (2026-09-26) - 전에는 정렬 맨 위를 그대로 썼다. 인턴이 소재를 고른 적이 없었다.
    iss = issues.load()
    cands = radar.candidates(clusters, radar.used_keys())
    sel = steps.select(cands, issues.open_text(iss, args.date)) if cands else None
    pick = cands[sel["chosen"]] if sel else (cands[0] if cands else None)
    trace["selection"] = _selection_trace(cands, sel, pick)
    if sel and not sel.get("only_one"):
        print(f"  [select] 후보 {len(cands)} 중 [{sel['chosen']}] · {sel['reason_ko'][:70]}")
        print(f"  [select] 이슈 {(sel.get('issue') or {}).get('id') or '새 판 · ' + (sel.get('issue') or {}).get('label_ko', '')}")
    elif cands:
        print(f"  [select] 인턴 선정 없음(후보 {len(cands)}) → 정렬 맨 위로 대신했다")
    if not pick:
        print("  [radar] 오늘 쓸 사건이 없다. 「오늘은 없음」으로 기록만.")
        trace["steps"]["radar"] = {"rows": len(rows), "picked": None}
        publish._dump(config.LOG_DIR / f"{args.date}.json", trace)
        return 0
    cluster_text = radar.describe(pick)
    print(f"  [radar] 오늘의 사건: {pick['items'][0]['title'][:70]} ({pick['n']}건 · 레이더 {pick['radar_tense']} · {pick['factor']}×{pick['stage']})")
    trace["cluster"] = {"key": pick["key"], "item_ids": pick["item_ids"], "n": pick["n"], "radar_tense": pick["radar_tense"],
                        "factor": pick["factor"], "stage": pick["stage"], "titles": [x["title"] for x in pick["items"]],
                        "urls": [x["url"] for x in pick["items"]],
                        "items": [{k: x.get(k) for k in ("title", "url", "source", "region", "published_date")} for x in pick["items"][:6]]}
    # ①' 소재 요약 (독자가 본문보다 먼저 본다)
    src_sum = steps.summarize_sources(cluster_text)
    trace["source_summary"] = src_sum
    for x, te in zip(trace["cluster"]["items"], src_sum.get("titles_en", [])):
        x["title_en"] = te
    print(f"  [source] {src_sum['ko'][:70]}")

    # ② 재료
    mats = {"text": "", "wiki": [], "lexicon": []} if args.no_brain else brain.retrieve(cluster_text)
    trace["materials"] = {"wiki": mats["wiki"], "lexicon": mats["lexicon"]}
    if not (mats["wiki"] or mats["lexicon"]):
        # BRAIN_PAT이 없거나 만료되면 여기가 조용히 빈다. 로그에 한 줄이라도 남긴다.
        print(f"  [brain] 재료 없음 - 두뇌를 못 읽었다({config.BRAIN_DIR}). 관점 렌즈 없이 쓴다")

    # ③ 판정
    extra = steps.context_block(steps.context(cluster_text))   # ②' 그 뒤 무엇이 나왔나
    trace["context"] = extra
    j = steps.judge(cluster_text, pick, mats["text"], extra)
    # 정본 규칙 - 「이미」만으로 된 편은 내지 않는다. 다음 후보로 한 번만 넘어간다.
    # **2026-09-10부터 이 가드가 꺼져 있었다.** 시제 이름이 「배경→뉴스」로 바뀌면서 판정기는 news를
    # 돌려주는데 여기는 background를 찾았다(2026-09-26 발견). 그동안 뉴스 판정이 한 편도 없어 피해는 없었다.
    if j["tense"] in ("news", "background"):
        rest = [c for c in cands if c["key"] != pick["key"]]
        sel2 = steps.select(rest, issues.open_text(iss, args.date)) if rest else None
        alt = rest[sel2["chosen"]] if sel2 else (rest[0] if rest else None)
        if alt:
            trace["selection"] = _selection_trace(rest, sel2, alt, skipped=pick)
        print(f"  [judge] 뉴스 판정 → 다음 후보로: {(alt['items'][0]['title'][:60] if alt else '없음')}")
        trace["skipped"] = {"key": pick["key"], "reason": "background", "judgment": j}
        if alt:
            pick = alt
            cluster_text = radar.describe(pick)
            src_sum = steps.summarize_sources(cluster_text)
            trace["source_summary"] = src_sum
            trace["cluster"] = {"key": pick["key"], "item_ids": pick["item_ids"], "n": pick["n"],
                                "radar_tense": pick["radar_tense"], "factor": pick["factor"], "stage": pick["stage"],
                                "titles": [x["title"] for x in pick["items"]], "urls": [x["url"] for x in pick["items"]],
                                "items": [{k: x.get(k) for k in ("title", "url", "source", "region", "published_date")} for x in pick["items"][:6]]}
            for x, te in zip(trace["cluster"]["items"], src_sum.get("titles_en", [])):
                x["title_en"] = te
            mats = {"text": "", "wiki": [], "lexicon": []} if args.no_brain else brain.retrieve(cluster_text)
            trace["materials"] = {"wiki": mats["wiki"], "lexicon": mats["lexicon"]}
            extra = steps.context_block(steps.context(cluster_text))   # 소재가 바뀌었으니 다시 찾는다
            trace["context"] = extra
            j = steps.judge(cluster_text, pick, mats["text"], extra)
    trace["judgment"] = j
    print(f"  [judge] {steps.header_line(j, 'ko')} · 레이더 {j.get('radar_tense') or '미분류'}와 "
          f"{'일치' if j.get('agrees') else '비교 불가' if j.get('agrees') is None else '불일치'} · 베팅 {'있음' if j.get('bet') else '없음'}")
    print(f"  [judge] 각도: {j['angle_ko'][:80]}")

    # ④ 집필 ko
    recent = learn.recent_block(args.date)          # 어제의 나 - 본문·검수 지적·숫자
    if recent:
        print(f"  [learn] 지난 편 {len(recent)}자를 집필 자리에 붙였다")
    trace["recent"] = recent[:400]
    # ④ 잇는 판단 (2026-09-26) - 같은 이슈의 이전 편. 직전 두 편(문체·지적 학습)과 별개 통로다.
    sel_iss = (trace.get("selection") or {}).get("issue") or {}
    iid = sel_iss.get("id") if sel_iss.get("id") in iss["issues"] else None
    synth = issues.ripe(iss, iid, args.date)
    prior = issues.unsynth(iss, iid, before=args.date) if synth else []
    thread = issues.thread_block(iss, iid, args.date, "ko", full=synth) if iid else ""
    trace["issue"] = {"id": iid, "hint": sel_iss, "synth": synth, "prior": [x["slug"] for x in prior],
                      "thread_chars": len(thread)}
    if thread:
        print(f"  [issue] 「{issues.label(iss, iid)}」 이전 편 {len(thread)}자를 붙였다" + (" · **종합 편**" if synth else ""))
    reread_ko: list = []
    if synth:
        ko, reread_ko = steps.write_synth_ko(cluster_text, j, mats["text"], thread, extra,
                                             issues.label(iss, iid, "ko"), len(prior))
    else:
        ko = steps.write_ko(cluster_text, j, mats["text"], recent, extra, thread)
    trace["draft_ko_v1"] = ko
    trace["reread_ko"] = reread_ko
    print(f"  [write] ko v1 {len(ko)}자" + (f" · 되읽기 {len(reread_ko)}줄" if synth else ""))

    # ⑤ 검증
    claims = steps.extract_claims(ko)
    results = []
    for c in claims:
        r = steps.verify_claim(c); r["claim"] = c; results.append(r)
        print(f"  [verify] {r['status']:12s} {c[:60]}")
    ko = steps.hedge(ko, results, "ko")
    trace["claims"] = results
    verified = sum(1 for r in results if r["status"] == "verified")

    # ⑥ 검수 (별도 컨텍스트)
    rounds, unresolved, last_issues, reviews = 0, False, [], []
    while True:
        prev = reviews[-1].get("blocking") if reviews else None
        rv = steps.review(ko, j, prev_issues=prev); reviews.append(rv); rounds += 1
        print(f"  [review] {rounds}회차 {rv['verdict']} · 차단 {len(rv.get('blocking', []))} · 개선 {len(rv.get('notes', []))} · {rv.get('one_line','')[:60]}")
        if rv["verdict"] == "pass":
            break
        last_issues = rv.get("blocking") or rv["issues"]
        if rounds >= MAX_REVIEW_ROUNDS:
            unresolved = True; break
        ko = steps.revise(ko, rv["issues"])
    trace["reviews"] = reviews
    # ⑥' 기계 게이트 - 분량 규격과 대조 공식. 수정 루프가 끝난 뒤라야 되돌려지지 않는다
    # 종합 편은 문턱이 다르다 - 기본값(700~1000)으로 두면 1,400자 글이 1,000자로 잘린다(2026-09-26).
    ko, trace["gate"] = steps.final_gate(ko, "ko", *((1200, 1600) if synth else ()))
    # ⑥'' 표기·인링크 정리 (논지는 안 건드린다)
    links = steps.link_sources(trace["cluster"]["items"], results)
    ko = steps.polish(ko, "ko", links)
    trace["draft_ko_final"] = ko

    # ④' 집필 en (검증된 ko를 딛고 따로 쓴다)
    en = steps.write_en(cluster_text, j, ko, synth=synth, reread_ko=reread_ko)
    en, reread_en = steps.split_reread(en, steps.SPLIT_EN) if synth else (en, [])
    trace["reread_en"] = reread_en
    en = steps.polish(en, "en", links)
    trace["draft_en_final"] = en
    # ⑦' 제목 - 최종 본문에서 뽑는다(판정 단계 제목은 임시였다)
    trace["working_title"] = {"ko": j.get("title_ko"), "en": j.get("title_en")}
    nouns = form.source_nouns(trace["cluster"]["items"], ko)
    tk = steps.title_from_body(ko, j, "ko", nouns); te = steps.title_from_body(en, j, "en", nouns)
    j["title_ko"], j["title_en"] = tk["title"], te["title"]
    # 후보끼리 붙여 고른다. 절대 점수로는 변별이 안 됐다(2026-09-10 - 6편 전부 같은 점수).
    dk = duel.pick_title(tk.get("candidates", []), ko, "ko")
    de = duel.pick_title(te.get("candidates", []), en, "en")
    if dk:
        j["title_ko"] = dk["best"]["title"]; tk = dict(tk, **dk["best"])
    if de:
        j["title_en"] = de["best"]["title"]; te = dict(te, **de["best"])
    tc = steps.title_check(j["title_ko"], ko, "ko")  # 절대 판정은 기록만 - 대조군으로 남긴다
    trace["title"] = {"ko": tk, "en": te, "check": tc, "duel_ko": dk, "duel_en": de}

    outlets = [x.get("source") or "" for x in trace["cluster"]["items"]]
    last_issues_en = steps.issues_en(last_issues) if unresolved else []
    name_maps = {"ko": steps.name_map([ko, src_sum["ko"], " ".join(outlets)] + last_issues, "ko"),
                 "en": steps.name_map([en, src_sum["en"], " ".join(outlets)] + last_issues_en, "en")}
    trace["name_map"] = name_maps
    print(f"  [names] ko {len(name_maps['ko'])} · en {len(name_maps['en'])}")
    print(f"  [write] en {len(en.split())} words")

    trace["usage"] = dict(llm.USAGE)
    # 단계별 내역 (2026-09-18). 어느 단계가 값을 먹는지 합계로는 안 보인다.
    trace["usage_by_step"] = {f"{s}|{m}": v for (s, m), v in llm.USAGE_BY_STEP.items()}
    print(llm.step_report())
    print(f"  [llm] calls {llm.USAGE['calls']} · in {llm.USAGE['input']} · out {llm.USAGE['output']} · search {llm.USAGE['search_uses']} · {time.time()-t0:.0f}s")
    if args.dry_run:
        sl = trace.get("selection") or {}
        print("\n" + "=" * 60 + "\n" + steps.header_line(j, "ko") + "\n# " + j["title_ko"]
              + ("\n\n왜 이걸 골랐나 · " + sl.get("reason_ko", "") if sl.get("reason_ko") else "")
              + ("\n[종합 편 · 이전 " + str(len(prior)) + "편]" if synth else "")
              + "\n\n" + ko + "\n\n원리 · " + j["principle_ko"]
              + ("\n\n지난 판단 되읽기\n" + "\n".join("- " + x for x in reread_ko) if reread_ko else ""))
        return 0

    # ⑦ 발행·기록
    slug = publish.slugify(j.get("title_en", ""), args.date)
    meta = {"day": publish.day_number(args.date), "radar_tense": pick["radar_tense"], "claims_total": len(results),
            "claims_verified": verified, "review_rounds": rounds, "unresolved": unresolved, "last_issues": last_issues,
            "last_issues_en": last_issues_en,
            "sources": trace["cluster"]["urls"], "source_items": trace["cluster"]["items"], "source_summary": src_sum,
            "name_map": name_maps, "title_source": {"ko": tk.get("source", ""), "en": te.get("source", "")},
            "style": style.measure(ko),
            "form": dict(form.measure(j["title_ko"], ko, trace["cluster"]["items"]), title_check=tc,
                          title_kept_first=dk.get("kept_first") if dk else None,
                          title_cands=dk.get("n") if dk else 0),
            "wiki": mats["wiki"], "lexicon": mats["lexicon"]}
    # 선정·이슈·종합 (2026-09-26)
    # 없는 id를 인턴이 지어내면 그대로 새 이슈 id가 된다 - 기존 이슈에 있는 id만 받고, 아니면 라벨로 새로 연다.
    # 라벨마저 없으면 편 제목을 이슈 이름으로 쓴다(한 편짜리 판으로 시작).
    iid = issues.assign(iss, slug, args.date, iid,
                        sel_iss.get("label_ko") or j["title_ko"], sel_iss.get("label_en") or j["title_en"])
    meta.update(selection=trace.get("selection") or {}, synth=synth, synth_n=len(prior),
                issue={"id": iid, "label_ko": issues.label(iss, iid, "ko"), "label_en": issues.label(iss, iid, "en")},
                reread={"ko": reread_ko, "en": reread_en},
                # 종합 편은 이어 읽은 편을 전부 건다 - 평소처럼 넷에서 자르면 목록과 본문이 어긋난다
                thread_links={lg: issues.thread_links(iss, iid, args.date, lg, n=max(4, len(prior)))
                              for lg in ("ko", "en")})
    trace["form"] = meta["form"]
    _off = style.off_axes(meta["style"])
    print(f"  [style] 사람 분포 밖 {len(_off)}개" + (f" · {' · '.join(_off)}" if _off else ""))
    print(f"  [form] 점수 {form.score(meta['form'])}/100 · 제목 고유명사 {meta['form']['title_noun']}(기록만) · "
          f"리드 구체 {meta['form']['lead_concrete']} · AI tell {meta['form']['ai_tell']} · 문장중앙 {meta['form']['sent_med']}자")
    publish.record(args.date, slug, j, meta, ko, en, trace)
    # 이슈는 기록이 성공한 뒤에 저장한다 - 기록이 실패하면 없는 편이 스레드에 매달린다
    if synth:
        issues.mark_synth(iss, iid, slug, args.date)
    issues.save(iss)
    publish.rule_candidates(last_issues if unresolved else [i for rv in reviews for i in rv.get("issues", [])], args.date)
    # 종합 편이면 개별 편 요약과 블라인드로 붙인다 - 「잇는 판단」이 글을 낫게 하는지 재는 자
    if synth:
        try:
            r = duel.synthesis_duel(slug, [x["slug"] for x in prior], "ko")
            if r:
                print(f"  [duel] 종합 편 vs 개별 요약 · {'종합 승' if r.get('winner') == 'synth' else '개별 승' if r.get('winner') == 'parts' else '비김'}")
        except Exception as e:  # noqa: BLE001
            print(f"  [duel] 종합 대결 건너뜀 {type(e).__name__}")
    build_site.build()
    print(f"  [publish] content/ko/{slug}.md · content/en/{slug}.md · D+{meta['day']}" + (" · 종합 편" if synth else ""))

    # 메일
    ko_md = io_piece("ko", slug); en_md = io_piece("en", slug)
    for lang, md in (("ko", ko_md), ("en", en_md)):
        title = j["title_ko"] if lang == "ko" else j["title_en"]
        mail.send_piece(lang, meta["day"], title, md, slug, send=args.send)
    print(f"== 완료 {time.time()-t0:.0f}s")
    return 0


def run_weekly(args) -> int:
    """⑨ 주간 회고(토요일) - 새 소재를 안 찾는다. 한 주의 자기 기록만 읽는다."""
    t0 = time.time()
    week = weekly.week_number(args.date)
    g = weekly.gather(args.date)
    g["duels"] = weekly.run_duels(args.date, g["rows"], "ko")  # 지난 편과 blind로 붙인다
    # 두뇌 재료가 값을 하는지 **매주 2편씩 대조군으로 쌓는다**(2026-09-16 대표 지시).
    # 한 번의 실험이 아니라 누적으로 본다 - 표본이 작을 때 한 주 숫자는 동전 던지기와 구분이 안 된다.
    try:
        ablation.run(ablation.pick_dates(g["rows"], 2), "ko")
    except Exception as e:  # noqa: BLE001
        print(f"  [ablation] 건너뜀 {type(e).__name__}")
    # 되읽기 - 낸 글을 다시 보고 그 뒤 나온 것을 확인한다. 회고 전에 돌려야 회고의 재료가 된다.
    g["recheck"] = recheck.run(args.date)
    recheck.apply_corrections(g["recheck"])
    print(f"== 주간 회고 {week}주차 · {args.date} · 이번 주 {g['n']}편 · 격자 {g['cells']}칸 · "
          f"불일치 {g['disagree']}/{g['compared']} · 미해결 {g['unresolved']} · 검증 {g['verified']}/{g['claims']}")
    print(f"  [signals] {g['signals']}")
    if not g["rows"]:
        print("  [weekly] 이번 주 발행이 없다. 회고를 쓰지 않는다.")
        publish._dump(config.LOG_DIR / f"{args.date}.json", {"date": args.date, "weekly": week, "empty": True})
        return 0
    ko = weekly.reflect(g, "ko")
    print(f"  [weekly] ko {len(ko)}자")
    ko, gate = steps.final_gate(ko, "ko", lo=700, hi=950)
    en = weekly.reflect(g, "en")
    print(f"  [weekly] en {len(en.split())} words")
    trace = {"date": args.date, "weekly": week, "gather": {k: v for k, v in g.items() if k != "rows"},
             "rows": [s["slug"] for s in g["rows"]], "gate": gate, "ko": ko, "en": en, "usage": dict(llm.USAGE)}
    # 단계별 내역 (2026-09-18). 회고는 데일리와 단계 구성이 다르다 - 새 소재를
    # 안 찾는 대신 되읽기·대조군·듀얼이 붙는다. dry-run이 아래에서 일찍 돌아가므로
    # 여기서 찍어야 두 경로 다 보인다.
    trace["usage_by_step"] = {f"{s}|{m}": v for (s, m), v in llm.USAGE_BY_STEP.items()}
    print(llm.step_report())
    if args.dry_run:
        print("\n" + "=" * 60 + "\n" + ko)
        return 0
    trace["rules_new"] = weekly.harvest(args.date, g, ko)  # 인턴이 쓴 한 줄이 다음 주 프롬프트로 간다
    slug = weekly.record(args.date, week, g, ko, en, trace)
    build_site.build()
    print(f"  [publish] content/ko/{slug}.md · content/en/{slug}.md")
    for lang in ("ko", "en"):
        title = f"{week}주차 회고" if lang == "ko" else f"Week {week} review"
        fm, body = publish.parse_piece(config.CONTENT_DIR / lang / f"{slug}.md")
        mail.send_piece(lang, publish.day_number(args.date), title, body.strip(), slug, send=args.send)
    print(f"== 완료 {time.time()-t0:.0f}s")
    return 0


def rebuild(args) -> int:
    """로그(판정·최종 원고)는 그대로 두고 발행물만 새 구조로 다시 만든다. 구조 규칙이 바뀐 날 쓴다."""
    log_p = config.LOG_DIR / f"{args.date}.json"
    trace = json.loads(open(log_p, encoding="utf-8").read())
    j = trace["judgment"]; cl = trace["cluster"]
    items = cl.get("items")
    if not items:
        # 옛 로그: 레이더에서 그 항목을 다시 읽는다
        items = []
        try:
            rows = radar.fetch_live(24 * 30)
            byid = {r["id"]: r for r in rows}
            for i in cl["item_ids"]:
                r = byid.get(i)
                if r:
                    items.append({k: r.get(k) for k in ("title", "url", "source", "region", "published_date")})
        except Exception as e:
            print(f"  [rebuild] 레이더 재조회 실패: {str(e)[:80]}")
        if not items:
            items = [{"title": t, "url": u} for t, u in zip(cl.get("titles", []), cl.get("urls", []))]
        cl["items"] = items
    cluster_text = "\n".join(f"- [{x.get('region')}/{x.get('source')}] {x.get('title')}\n  {x.get('url')}" for x in items)
    src_sum = trace.get("source_summary") or {}
    if not src_sum.get("titles_en"):
        src_sum = steps.summarize_sources(cluster_text)
    trace["source_summary"] = src_sum
    for x, te in zip(items, src_sum.get("titles_en", [])):
        x["title_en"] = te
    results = trace.get("claims", []); reviews = trace.get("reviews", [])
    unresolved = bool(reviews) and reviews[-1].get("verdict") != "pass"
    last_issues = reviews[-1].get("issues", []) if unresolved else []
    links = steps.link_sources(items, results)
    synth = bool((trace.get("issue") or {}).get("synth"))
    ko, trace["gate"] = steps.final_gate(trace["draft_ko_final"], "ko", *((1200, 1600) if synth else ()))
    ko = steps.polish(ko, "ko", links)
    en = steps.polish(trace["draft_en_final"], "en", links)
    trace["draft_ko_final"], trace["draft_en_final"] = ko, en
    outlets = [x.get("source") or "" for x in items]
    last_issues_en = steps.issues_en(last_issues) if unresolved else []
    name_maps = {"ko": steps.name_map([ko, src_sum["ko"], " ".join(outlets)] + last_issues, "ko"),
                 "en": steps.name_map([en, src_sum["en"], " ".join(outlets)] + last_issues_en, "en")}
    trace["name_map"] = name_maps
    print(f"  [names] ko {name_maps['ko']} · en {name_maps['en']}")
    slug = publish.slugify(j.get("title_en", ""), args.date)
    mats = trace.get("materials", {})
    meta = {"day": publish.day_number(args.date), "radar_tense": cl.get("radar_tense"), "claims_total": len(results),
            "claims_verified": sum(1 for r in results if r.get("status") == "verified"), "review_rounds": len(reviews),
            "unresolved": unresolved, "last_issues": last_issues, "last_issues_en": last_issues_en,
            "sources": cl.get("urls", []), "source_items": items,
            "source_summary": src_sum, "name_map": name_maps, "wiki": mats.get("wiki", []), "lexicon": mats.get("lexicon", [])}
    # 선정·이슈 (2026-09-26). 옛 로그에는 없다 - 없으면 비워 두고, 이슈는 소급 대장(issues.json)에서 읽는다.
    iss = issues.load()
    iid = iss["pieces"].get(slug) or (trace.get("issue") or {}).get("id")
    meta.update(selection=trace.get("selection") or {}, synth=synth,
                synth_n=len((trace.get("issue") or {}).get("prior") or []),
                issue={"id": iid, "label_ko": issues.label(iss, iid, "ko") if iid else "",
                       "label_en": issues.label(iss, iid, "en") if iid else ""},
                reread={"ko": trace.get("reread_ko") or [], "en": trace.get("reread_en") or []},
                thread_links={lg: issues.thread_links(iss, iid, args.date, lg,
                                                      n=max(4, len((trace.get("issue") or {}).get("prior") or [])))
                              for lg in ("ko", "en")})
    trace["usage_rebuild"] = dict(llm.USAGE)
    publish.record(args.date, slug, j, meta, ko, en, trace)
    build_site.build()
    print(f"  [rebuild] content/ko/{slug}.md · content/en/{slug}.md · D+{meta['day']}")
    for lang in ("ko", "en"):
        title = j["title_ko"] if lang == "ko" else j["title_en"]
        mail.send_piece(lang, meta["day"], title, io_piece(lang, slug), slug, send=args.send)
    return 0


def _selection_trace(cands: list, sel: dict | None, pick: dict | None, skipped: dict | None = None) -> dict:
    """선정 기록. **안 고른 후보의 기사 id까지 남긴다** - 30·90일 뒤 후속 비교가 이걸 읽는다."""
    def brief(c):
        return {"key": c["key"], "title": c["items"][0].get("title", "") if c.get("items") else "",
                "n": c.get("n"), "item_ids": c.get("item_ids") or [x["id"] for x in c.get("items", [])],
                "titles": [x.get("title", "") for x in c.get("items", [])[:6]]}
    why = {r["i"]: r["why"] for r in ((sel or {}).get("rejected") or [])}
    out = {"n": len(cands), "by": "intern" if sel and not sel.get("only_one") else "code",
           "chosen": brief(pick) if pick else None,
           "reason_ko": (sel or {}).get("reason_ko", ""), "reason_en": (sel or {}).get("reason_en", ""),
           "issue": (sel or {}).get("issue") or {},
           "rejected": [dict(brief(c), why=why.get(i, "")) for i, c in enumerate(cands) if pick is None or c["key"] != pick["key"]]}
    if skipped:
        out["skipped_news"] = brief(skipped)
    return out


def io_piece(lang: str, slug: str) -> str:
    fm, body = publish.parse_piece(config.CONTENT_DIR / lang / f"{slug}.md")
    return body.strip()


if __name__ == "__main__":
    sys.exit(main())
