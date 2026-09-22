#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Subagent 결과의 {line, quote} 인용을 원문과 대조하고, 어긋난 인용의 올바른 줄을 찾아준다.

왜 필요한가 (runs/test-02 에서 실제로 터진 문제):
  분석 Subagent 인용 1,214건 중 16건에서 quote 는 원문에 있는데 줄 번호만
  1~70줄 어긋났다(Read 오프셋 드리프트). 당시에는 사람이 ±50줄을 훑고 grep 해서
  올바른 줄을 찾았다. RapidFuzz 로 그 탐색을 자동화한다.

사용:
  python scripts/check_citations.py --indexed <indexed.txt> --json <a.json> [--json <b.json> ...] \
      [--out report.json] [--min-score 80]

동작:
  1. quote 가 해당 줄의 부분 문자열이면 ok
  2. 아니면 전체 줄 중 quote 와 가장 비슷한 줄을 RapidFuzz 로 찾아 후보로 제시
     - partial_ratio: quote 가 줄의 일부일 때 잘 잡힌다
  3. 정확히 일치하는 줄이 딱 하나면 auto_fix 로 표시(적용은 사람/메인이 결정)

종료 코드: 불일치가 있으면 1
"""
import argparse
import json
import sys


def walk_citations(obj, path="$"):
    """중첩 구조 어디에 있든 {line, quote} 쌍을 모두 찾는다."""
    out = []
    if isinstance(obj, dict):
        if "line" in obj and "quote" in obj:
            out.append((path, obj))
        for k, v in obj.items():
            out.extend(walk_citations(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.extend(walk_citations(v, f"{path}[{i}]"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indexed", required=True, help="Lnnnnn | 본문 형식 파일")
    ap.add_argument("--json", action="append", required=True, help="검사할 JSON (여러 개 가능)")
    ap.add_argument("--out", default=None)
    ap.add_argument("--min-score", type=float, default=80.0)
    args = ap.parse_args()

    try:
        from rapidfuzz import fuzz, process
    except ImportError:
        raise SystemExit("rapidfuzz 가 필요합니다: pip install rapidfuzz  (https://github.com/rapidfuzz/RapidFuzz)")

    bodies, ids = [], []
    with open(args.indexed, encoding="utf-8") as f:
        for raw in f.read().splitlines():
            if " | " in raw:
                lid, body = raw.split(" | ", 1)
            else:
                lid, body = raw.strip(), ""
            ids.append(lid)
            bodies.append(body)
    index_of = {lid: i for i, lid in enumerate(ids)}

    checked = 0
    problems = []
    for jpath in args.json:
        with open(jpath, encoding="utf-8") as f:
            data = json.load(f)
        for where, cit in walk_citations(data):
            checked += 1
            lid, quote = str(cit.get("line", "")), cit.get("quote", "")
            i = index_of.get(lid)
            if i is not None and quote and quote in bodies[i]:
                continue

            # 1) 원문 전체에서 정확히 포함하는 줄
            exact = [ids[k] for k, b in enumerate(bodies) if quote and quote in b]
            # 2) RapidFuzz 최적 후보 (부분 일치 기준)
            best = process.extract(quote, bodies, scorer=fuzz.partial_ratio, limit=3) if quote else []
            cands = [{"line": ids[k], "score": round(sc, 1), "text": bodies[k][:90]} for _, sc, k in best if sc >= args.min_score]

            problems.append({
                "file": jpath.replace("\\", "/"),
                "where": where,
                "cited_line": lid,
                "cited_line_text": bodies[i][:90] if i is not None else "(범위 밖)",
                "quote": quote,
                "exact_matches": exact,
                "auto_fix": exact[0] if len(exact) == 1 else None,
                "fuzzy_candidates": cands,
            })

    report = {
        "indexed": args.indexed.replace("\\", "/"),
        "files": [p.replace("\\", "/") for p in args.json],
        "citations_checked": checked,
        "mismatches": len(problems),
        "auto_fixable": sum(1 for p in problems if p["auto_fix"]),
        "tool": "rapidfuzz/RapidFuzz (https://github.com/rapidfuzz/RapidFuzz)",
        "problems": problems,
    }
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"인용 {checked}건 검사 / 불일치 {len(problems)}건 / 자동 교정 가능 {report['auto_fixable']}건")
    for p in problems[:30]:
        fix = f" → {p['auto_fix']}" if p["auto_fix"] else ""
        print(f"  {p['cited_line']}{fix}  “{p['quote'][:45]}”")
        if not p["auto_fix"] and p["fuzzy_candidates"]:
            c = p["fuzzy_candidates"][0]
            print(f"      후보 {c['line']} (유사도 {c['score']}) {c['text'][:50]}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
