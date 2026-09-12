#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate analysis.json against stats.json before rendering.

The reading is done by a model and varies from run to run; this check pins the *shape* of the result so
every report has the same sections filled to the same depth: a 5-8 bullet summary, a digest for every day,
threads with dated flows and a status from the fixed taxonomy, a check point for anything still open,
and profiles for the people who matter. Hard errors block rendering; warnings are printed.

Usage:
  python check_analysis.py --data work --analysis analysis.json
"""
import argparse, json, os, re, sys

STATUS = {"done", "assigned", "open", "drop", "info"}


def check(A, S):
    errors, warns = [], []
    for k in ("title", "summary", "speakers", "daily", "groups", "threads"):
        if k not in A:
            errors.append(f"필수 키 없음: {k}")
    if errors:
        return errors, warns

    n = len(A["summary"])
    if not 5 <= n <= 8:
        warns.append(f"summary는 5~8개가 기준인데 {n}개")
    for i, s in enumerate(A["summary"]):
        if len(re.sub(r"<[^>]+>", "", s)) < 40:
            warns.append(f"summary[{i}]가 너무 짧음 ({len(s)}자)")

    stat_speakers = list(S.get("speakers", {}).keys())
    bots = set(S.get("bots", []))
    prof_names = [p.get("name") for p in A["speakers"]]
    for p in A["speakers"]:
        for k in ("name", "role", "profile"):
            if not p.get(k):
                errors.append(f"speakers[{p.get('name','?')}]에 {k} 없음")
        if p.get("name") not in S.get("speakers", {}):
            errors.append(f"speakers[{p.get('name')}]가 stats.json 화자 목록에 없음 (이름 정확히 일치해야 함)")
        if len(re.sub(r"<[^>]+>", "", p.get("profile", ""))) < 80:
            warns.append(f"speakers[{p.get('name')}] profile이 80자 미만 — 무엇을 가져오고 누구에게 어떻게 반응하는지, 근거 인용을 넣을 것")
    if len(stat_speakers) <= 8:
        for s in stat_speakers:
            if s not in prof_names and s not in bots:
                warns.append(f"소규모 방인데 화자 '{s}' 프로필이 없음")
    else:
        top = [s for s in S.get("speakers_order", [])[:5] if s not in bots]
        for s in top:
            if s not in prof_names:
                warns.append(f"상위 화자 '{s}' 프로필이 없음 (오픈채팅은 상위 5~8명 + 운영자 프로필)")

    days = S.get("days", [])
    have = {d.get("date") for d in A["daily"]}
    for d in days:
        if d not in have:
            errors.append(f"daily에 {d} 다이제스트 없음 (모든 날짜 필요)")
    for d in A["daily"]:
        if d.get("date") not in days:
            warns.append(f"daily의 {d.get('date')}는 대화가 없는 날")
        if len(re.sub(r"<[^>]+>", "", d.get("digest", ""))) < 20:
            warns.append(f"daily[{d.get('date')}] digest가 너무 짧음")

    gids = [g.get("id") for g in A["groups"]]
    if len(gids) != len(set(gids)):
        errors.append("groups id 중복")
    if not 2 <= len(gids) <= 8:
        warns.append(f"groups는 사업·영역 단위로 2~8개가 기준인데 {len(gids)}개")
    for g in A["groups"]:
        if not g.get("title"):
            errors.append(f"group {g.get('id')}에 title 없음")

    T = A["threads"]
    if not 3 <= len(T) <= 40:
        warns.append(f"threads {len(T)}개 — 하루짜리 잡담은 daily로 내리고, 같은 실체는 하나로 병합했는지 확인")
    for i, t in enumerate(T):
        tag = f"threads[{i}] '{t.get('title','?')[:30]}'"
        for k in ("title", "group", "status", "flow"):
            if not t.get(k):
                errors.append(f"{tag}에 {k} 없음")
        if t.get("status") not in STATUS:
            errors.append(f"{tag} status '{t.get('status')}'는 {sorted(STATUS)} 중 하나여야 함")
        if t.get("group") not in gids:
            errors.append(f"{tag} group '{t.get('group')}'가 groups에 없음")
        flow = re.sub(r"<[^>]+>", "", t.get("flow", ""))
        if t.get("status") != "info" and len(flow) < 120:
            warns.append(f"{tag} flow가 120자 미만 — 날짜 태그로 5~10문장")
        if "→" not in flow and "->" not in flow:
            warns.append(f"{tag} flow에 흐름 표시(→)가 없음")
        if not re.search(r"\d{1,2}/\d{1,2}", flow):
            warns.append(f"{tag} flow에 날짜 태그(예: 8/21)가 없음")
        if t.get("status") in ("open", "assigned", "drop") and not t.get("next"):
            warns.append(f"{tag} status={t['status']}인데 next(확인 포인트) 없음")
        if t.get("status") == "done" and not t.get("end"):
            warns.append(f"{tag} status=done인데 end(결말·근거) 없음")
        if "→" not in t.get("title", "") and ":" not in t.get("title", ""):
            warns.append(f"{tag} 제목은 '실체: 변화 → 변화' 꼴이 기준")
    if T and not any(t.get("status") in ("drop", "assigned", "open") for t in T):
        warns.append("열려 있거나 사라진 스레드가 하나도 없음 — 무응답 질문·미이행 약속을 놓쳤는지 확인")

    for g in A.get("glossary", []):
        if not g.get("term") or not g.get("desc"):
            errors.append("glossary 항목에 term/desc 없음")
    notes = " ".join(A.get("notes", []))
    if "화자" not in notes and "파싱" not in notes:
        warns.append("notes에 파싱·화자 집계 각주 한 줄을 넣을 것")
    if not re.search(r"비밀번호|민감|노출|개인정보", notes):
        warns.append("notes에 민감정보 처리(옮기지 않음) 문구가 없음")
    return errors, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True); ap.add_argument("--analysis", required=True)
    a = ap.parse_args()
    S = json.load(open(os.path.join(a.data, "stats.json"), encoding="utf-8"))
    A = json.load(open(a.analysis, encoding="utf-8"))
    errors, warns = check(A, S)
    for w in warns: print("WARN ", w)
    for e in errors: print("ERROR", e)
    print(f"check: {len(errors)} errors, {len(warns)} warnings — threads {len(A.get('threads', []))}, daily {len(A.get('daily', []))}/{len(S.get('days', []))}, speakers {len(A.get('speakers', []))}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
