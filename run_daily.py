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

from intern import config, llm, radar, brain, steps, publish, build_site, mail

MAX_REVIEW_ROUNDS = 2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=config.today_kst().strftime("%Y-%m-%d"))
    ap.add_argument("--send", action="store_true", help="Buttondown 실제 발송")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--hours", type=int, default=168, help="레이더 창(시간)")
    ap.add_argument("--no-brain", action="store_true")
    ap.add_argument("--rebuild", action="store_true", help="그날 로그의 판정·최종 원고로 발행물만 다시 만든다(LLM은 소재 요약·표기 정리만)")
    args = ap.parse_args()
    if args.rebuild:
        return rebuild(args)
    config.ensure_dirs()
    t0 = time.time()
    trace: dict = {"date": args.date, "steps": {}}
    print(f"== AI 인턴 1호 · {args.date} · model {config.MODEL_MAIN}")

    # ① 소재 읽기
    rows = radar.fetch_live(args.hours)
    clusters = radar.cluster(rows)
    pick = radar.pick_today(clusters, radar.used_keys())
    print(f"  [radar] 살아있는 행 {len(rows)} · 무리 {len(clusters)}")
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

    # ③ 판정
    j = steps.judge(cluster_text, pick, mats["text"])
    trace["judgment"] = j
    print(f"  [judge] {steps.header_line(j, 'ko')} · 레이더와 {'일치' if j.get('agrees') else '불일치: ' + str(j.get('disagree_reason'))[:60]} · 베팅 {'있음' if j.get('bet') else '없음'}")
    print(f"  [judge] 각도: {j['angle_ko'][:80]}")

    # ④ 집필 ko
    ko = steps.write_ko(cluster_text, j, mats["text"])
    trace["draft_ko_v1"] = ko
    print(f"  [write] ko v1 {len(ko)}자")

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
        rv = steps.review(ko, j); reviews.append(rv); rounds += 1
        print(f"  [review] {rounds}회차 {rv['verdict']} · {rv.get('one_line','')[:70]}")
        if rv["verdict"] == "pass":
            break
        last_issues = rv["issues"]
        if rounds >= MAX_REVIEW_ROUNDS:
            unresolved = True; break
        ko = steps.revise(ko, rv["issues"])
    trace["reviews"] = reviews
    # ⑥' 표기·인링크 정리 (검수 뒤, 논지는 안 건드린다)
    links = steps.link_sources(trace["cluster"]["items"], results)
    ko = steps.polish(ko, "ko", links)
    trace["draft_ko_final"] = ko

    # ④' 집필 en (검증된 ko를 딛고 따로 쓴다)
    en = steps.write_en(cluster_text, j, ko)
    en = steps.polish(en, "en", links)
    trace["draft_en_final"] = en
    outlets = [x.get("source") or "" for x in trace["cluster"]["items"]]
    last_issues_en = steps.issues_en(last_issues) if unresolved else []
    name_maps = {"ko": steps.name_map([ko, src_sum["ko"], " ".join(outlets)] + last_issues, "ko"),
                 "en": steps.name_map([en, src_sum["en"], " ".join(outlets)] + last_issues_en, "en")}
    trace["name_map"] = name_maps
    print(f"  [names] ko {len(name_maps['ko'])} · en {len(name_maps['en'])}")
    print(f"  [write] en {len(en.split())} words")

    trace["usage"] = dict(llm.USAGE)
    print(f"  [llm] calls {llm.USAGE['calls']} · in {llm.USAGE['input']} · out {llm.USAGE['output']} · search {llm.USAGE['search_uses']} · {time.time()-t0:.0f}s")
    if args.dry_run:
        print("\n" + "=" * 60 + "\n" + steps.header_line(j, "ko") + "\n# " + j["title_ko"] + "\n\n" + ko + "\n\n원리 · " + j["principle_ko"])
        return 0

    # ⑦ 발행·기록
    slug = publish.slugify(j.get("title_en", ""), args.date)
    meta = {"day": publish.day_number(args.date), "radar_tense": pick["radar_tense"], "claims_total": len(results),
            "claims_verified": verified, "review_rounds": rounds, "unresolved": unresolved, "last_issues": last_issues,
            "last_issues_en": last_issues_en,
            "sources": trace["cluster"]["urls"], "source_items": trace["cluster"]["items"], "source_summary": src_sum,
            "name_map": name_maps, "wiki": mats["wiki"], "lexicon": mats["lexicon"]}
    publish.record(args.date, slug, j, meta, ko, en, trace)
    publish.rule_candidates(last_issues if unresolved else [i for rv in reviews for i in rv.get("issues", [])], args.date)
    build_site.build()
    print(f"  [publish] content/ko/{slug}.md · content/en/{slug}.md · D+{meta['day']}")

    # 메일
    ko_md = io_piece("ko", slug); en_md = io_piece("en", slug)
    for lang, md in (("ko", ko_md), ("en", en_md)):
        title = j["title_ko"] if lang == "ko" else j["title_en"]
        mail.send_piece(lang, meta["day"], title, md, slug, send=args.send)
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
    ko = steps.polish(trace["draft_ko_final"], "ko", links)
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
    trace["usage_rebuild"] = dict(llm.USAGE)
    publish.record(args.date, slug, j, meta, ko, en, trace)
    build_site.build()
    print(f"  [rebuild] content/ko/{slug}.md · content/en/{slug}.md · D+{meta['day']}")
    for lang in ("ko", "en"):
        title = j["title_ko"] if lang == "ko" else j["title_en"]
        mail.send_piece(lang, meta["day"], title, io_piece(lang, slug), slug, send=args.send)
    return 0


def io_piece(lang: str, slug: str) -> str:
    fm, body = publish.parse_piece(config.CONTENT_DIR / lang / f"{slug}.md")
    return body.strip()


if __name__ == "__main__":
    sys.exit(main())
