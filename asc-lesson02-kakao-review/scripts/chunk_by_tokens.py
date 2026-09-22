#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""카카오톡 내보내기 텍스트에 줄 ID를 붙이고 토큰 예산에 맞춰 청크로 나눈다.

왜 필요한가 (runs/test-02 에서 실제로 터진 문제):
  1. 파일 끝에 개행이 없으면 `wc -l` 이 마지막 줄을 세지 않아 원문 한 줄이
     어느 청크에도 들어가지 않았다. 여기서는 splitlines() 로 세어 누락을 막는다.
  2. 청크 크기를 글자 수로 눈대중해 Subagent 문맥 초과 위험을 감으로 관리했다.
     tiktoken 으로 실제 토큰을 세어 예산 안에서 자른다.

사용:
  python scripts/chunk_by_tokens.py <chat.txt> --out <dir> [--budget 25000] [--encoding-name cl100k_base]

출력:
  <dir>/indexed.txt          L00001 | 원문  (줄 ID 부여, 원문 무변조)
  <dir>/normalized.txt       CR 제거만 한 원문
  <dir>/chunks/cN-source.txt 청크별 줄 번호 원문
  <dir>/plan.json            청크 경계·토큰 수·커버리지 검사 결과
"""
import argparse
import json
import os
import re
import sys

DATE_HEADER = re.compile(r"^-{5,}\s*\d{4}년\s*\d{1,2}월\s*\d{1,2}일.*-{5,}\s*$")


def read_text(path, encodings=("utf-8-sig", "utf-8", "cp949", "euc-kr")):
    last = None
    for enc in encodings:
        try:
            with open(path, encoding=enc) as f:
                return f.read(), enc
        except UnicodeDecodeError as ex:
            last = ex
    raise SystemExit(f"디코딩 실패 {path}: {last}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("chat")
    ap.add_argument("--out", required=True)
    ap.add_argument("--budget", type=int, default=25000, help="청크당 최대 토큰")
    ap.add_argument("--encoding-name", default="cl100k_base")
    args = ap.parse_args()

    try:
        import tiktoken
    except ImportError:
        raise SystemExit("tiktoken 이 필요합니다: pip install tiktoken  (https://github.com/openai/tiktoken)")
    enc = tiktoken.get_encoding(args.encoding_name)

    raw, used_enc = read_text(args.chat)
    text = raw.replace("\r", "")
    # splitlines() 는 끝 개행 유무와 무관하게 실제 줄만 센다 → wc -l 누락 문제 해소
    lines = text.splitlines()
    n = len(lines)
    if n == 0:
        raise SystemExit("빈 파일")

    os.makedirs(os.path.join(args.out, "chunks"), exist_ok=True)
    width = max(5, len(str(n)))
    indexed = [f"L{str(i + 1).zfill(width)} | {ln}" for i, ln in enumerate(lines)]

    with open(os.path.join(args.out, "normalized.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(args.out, "indexed.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(indexed) + "\n")

    # 줄별 토큰 수 (줄 ID 접두어 포함 — Subagent 가 실제로 받는 형태)
    tok = [len(enc.encode(s)) for s in indexed]

    # 날짜 헤더를 자를 수 있는 지점으로 삼되, 예산을 넘으면 그 앞에서 끊는다.
    breakpoints = [i for i, ln in enumerate(lines) if DATE_HEADER.match(ln)]
    bset = set(breakpoints)

    chunks = []
    start = 0
    running = 0
    for i in range(n):
        # 날짜 경계이고, 지금까지 담은 양이 예산의 60% 를 넘었으면 여기서 끊는다
        if i > start and i in bset and running > args.budget * 0.6:
            chunks.append((start, i - 1, running))
            start, running = i, 0
        running += tok[i]
        if running > args.budget and i > start:
            # 예산 초과: 가능한 가장 가까운 앞쪽 날짜 경계로 후퇴, 없으면 여기서 절단
            back = [b for b in breakpoints if start < b <= i]
            cut = back[-1] if back else i
            chunks.append((start, cut - 1, sum(tok[start:cut])))
            start = cut
            running = sum(tok[start:i + 1])
    chunks.append((start, n - 1, sum(tok[start:n])))
    chunks = [c for c in chunks if c[0] <= c[1]]

    meta = []
    for idx, (a, b, t) in enumerate(chunks, 1):
        key = f"c{idx}"
        p = os.path.join(args.out, "chunks", f"{key}-source.txt")
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(indexed[a:b + 1]) + "\n")
        dates = [lines[i] for i in range(a, b + 1) if DATE_HEADER.match(lines[i])]
        meta.append({
            "chunk": key,
            "first_line": f"L{str(a + 1).zfill(width)}",
            "last_line": f"L{str(b + 1).zfill(width)}",
            "lines": b - a + 1,
            "tokens": t,
            "date_headers": len(dates),
            "file": p.replace("\\", "/"),
        })

    # 커버리지: 청크들이 1..n 을 빈틈·겹침 없이 덮는지 (test-02 의 마지막 줄 누락 재발 방지)
    covered, prev, gaps = 0, 0, []
    for m in meta:
        a = int(m["first_line"][1:])
        b = int(m["last_line"][1:])
        if a != prev + 1:
            gaps.append({"expected": prev + 1, "got": a})
        covered += b - a + 1
        prev = b
    if prev != n:
        gaps.append({"expected": n, "got": prev, "note": "마지막 줄 미포함"})

    plan = {
        "source": args.chat.replace("\\", "/"),
        "source_encoding": used_enc,
        "total_lines": n,
        "total_tokens": sum(tok),
        "line_id_width": width,
        "budget_tokens": args.budget,
        "encoding_name": args.encoding_name,
        "tool": "openai/tiktoken (https://github.com/openai/tiktoken)",
        "chunks": meta,
        "coverage": {"covered_lines": covered, "gaps": gaps, "complete": covered == n and not gaps},
    }
    with open(os.path.join(args.out, "plan.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(f"줄 {n} / 토큰 {sum(tok)} / 청크 {len(meta)} (예산 {args.budget})")
    for m in meta:
        print(f"  {m['chunk']}: {m['first_line']}-{m['last_line']}  {m['lines']:>5}줄  {m['tokens']:>6}토큰  날짜 {m['date_headers']}개")
    print("커버리지:", "완전" if plan["coverage"]["complete"] else f"불완전 {gaps}")
    return 0 if plan["coverage"]["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
