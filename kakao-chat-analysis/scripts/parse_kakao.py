#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse a KakaoTalk chat export (PC / Android / iOS text formats).

Outputs into --out:
  messages.json      list of {id, ts, speaker, text, kind, urls, line}
  stats.json         per-speaker / per-day / per-hour aggregates, sessions, files, domains
  chunks/<date>.txt  one file per day, "#id [HH:MM] speaker: text" (for reading)
  chunks/index.txt   day list with counts + suggested sub-agent ranges

Usage:
  python parse_kakao.py chat.txt --out work [--gap 60] [--speakers A,B,C] [--encoding utf-8]
"""
import argparse, collections, json, os, re, statistics, sys
from datetime import datetime, timedelta
from urllib.parse import urlparse

PC_DATE = re.compile(r"^-+\s*(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일.*-+\s*$")
PC_MSG = re.compile(r"^\[([^\]]+)\] \[(오전|오후) (\d{1,2}):(\d{2})\] ?(.*)$")
AND_MSG = re.compile(r"^(\d{4})년 (\d{1,2})월 (\d{1,2})일 (오전|오후) (\d{1,2}):(\d{2}), (.+?) : (.*)$")
IOS_MSG = re.compile(r"^(\d{4})\. (\d{1,2})\. (\d{1,2})\. (오전|오후) (\d{1,2}):(\d{2}), (.+?) : (.*)$")
MOB_DATE = re.compile(r"^(\d{4})년 (\d{1,2})월 (\d{1,2})일 [월화수목금토일]요일\s*$")
SYSTEM_PAT = re.compile(r"(님이 들어왔습니다|님이 나갔습니다|님을 내보냈습니다|채팅방 관리자가|운영정책을 위반한 메시지)")


def read_text(path, enc):
    encs = [enc] if enc else ["utf-8-sig", "utf-8", "cp949", "euc-kr"]
    last = None
    for e in encs:
        try:
            with open(path, encoding=e) as f:
                return f.read().splitlines()
        except UnicodeDecodeError as ex:
            last = ex
    raise SystemExit(f"could not decode {path}: {last}")


def hour24(ampm, h):
    h = int(h) % 12
    return h + (12 if ampm == "오후" else 0)


def parse(lines):
    msgs, header = [], []
    cur_date = None
    fmt = None
    for ln, line in enumerate(lines, 1):
        s = line.rstrip("\r")
        m = PC_DATE.match(s)
        if m:
            cur_date = datetime(int(m[1]), int(m[2]), int(m[3])); fmt = fmt or "pc"; continue
        m = MOB_DATE.match(s)
        if m and fmt != "pc":
            cur_date = datetime(int(m[1]), int(m[2]), int(m[3])); continue
        m = PC_MSG.match(s)
        if m and cur_date:
            fmt = "pc"
            ts = cur_date.replace(hour=hour24(m[2], m[3]), minute=int(m[4]))
            msgs.append({"line": ln, "ts": ts, "speaker": m[1].strip(), "text": m[5]}); continue
        m = AND_MSG.match(s) or IOS_MSG.match(s)
        if m:
            fmt = fmt or "mobile"
            ts = datetime(int(m[1]), int(m[2]), int(m[3]), hour24(m[4], m[5]), int(m[6]))
            cur_date = ts.replace(hour=0, minute=0)
            msgs.append({"line": ln, "ts": ts, "speaker": m[7].strip(), "text": m[8]}); continue
        if msgs:
            msgs[-1]["text"] += "\n" + s
        else:
            header.append(s)
    return msgs, header, fmt


def kind_of(t):
    s = t.strip()
    if s in ("사진", "사진 1장") or re.fullmatch(r"사진 \d+장", s): return "photo"
    if s == "이모티콘": return "emoticon"
    if s == "동영상": return "video"
    if s.startswith("파일:"): return "file"
    if s == "음성메시지": return "voice"
    if "삭제된 메시지입니다" in s or "메시지가 삭제되었습니다" in s: return "deleted"
    if re.fullmatch(r"https?://\S+", s): return "link_only"
    if SYSTEM_PAT.search(s) and len(s) < 60: return "system"
    return "text"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out", required=True)
    ap.add_argument("--gap", type=int, default=60, help="minutes of silence that starts a new session")
    ap.add_argument("--speakers", help="comma-separated list to force the speaker set")
    ap.add_argument("--encoding")
    ap.add_argument("--range-size", type=int, default=900, help="target messages per sub-agent range")
    a = ap.parse_args()

    lines = read_text(a.src, a.encoding)
    msgs, header, fmt = parse(lines)
    if not msgs:
        raise SystemExit("no messages recognised — is this a KakaoTalk export? (PC / Android / iOS text)")

    counts = collections.Counter(m["speaker"] for m in msgs)
    if a.speakers:
        speakers = [s.strip() for s in a.speakers.split(",") if s.strip()]
    else:
        # every timestamped line is a real participant (pasted "[이름]" tags carry no timestamp),
        # so keep them all — open chats legitimately have dozens of one-message speakers
        speakers = [s for s, n in counts.most_common()]
    dropped = {s: n for s, n in counts.items() if s not in speakers}
    bots = [s for s in speakers if re.search(r"(봇|bot)$", s, re.I) or s in ("오픈채팅봇", "채팅봇")]
    msgs = [m for m in msgs if m["speaker"] in speakers]
    for i, m in enumerate(msgs):
        m["id"] = i
        m["kind"] = kind_of(m["text"])
        m["urls"] = re.findall(r"https?://\S+", m["text"])
        m["len"] = len(m["text"])

    os.makedirs(os.path.join(a.out, "chunks"), exist_ok=True)

    # ---- stats
    S = {"format": fmt, "room": header[0] if header else "", "n_msgs": len(msgs),
         "period": [msgs[0]["ts"].strftime("%Y-%m-%d"), msgs[-1]["ts"].strftime("%Y-%m-%d")],
         "speakers_order": speakers, "n_speakers": len(speakers), "bots": bots, "dropped_names": dropped,
         "system_msgs": sum(1 for m in msgs if m["kind"] == "system")}
    by = collections.defaultdict(list)
    for m in msgs: by[m["speaker"]].append(m)
    S["speakers"] = {}
    for sp in speakers:
        L = by[sp]; txt = [m for m in L if m["kind"] == "text"]
        hours = collections.Counter(m["ts"].hour for m in L)
        S["speakers"][sp] = {
            "msgs": len(L), "share": round(len(L) / len(msgs) * 100, 1),
            "chars": sum(m["len"] for m in txt),
            "avg_len": round(statistics.mean(m["len"] for m in txt), 1) if txt else 0,
            "photo": sum(m["kind"] == "photo" for m in L), "file": sum(m["kind"] == "file" for m in L),
            "links": sum(len(m["urls"]) for m in L), "deleted": sum(m["kind"] == "deleted" for m in L),
            "long_300": sum(m["len"] >= 300 for m in L),
            "active_days": len({m["ts"].date() for m in L}),
            "top_hours": [h for h, _ in hours.most_common(3)],
            "hours": [hours.get(h, 0) for h in range(24)],
        }
    per_day = collections.OrderedDict()
    for m in msgs:
        per_day.setdefault(m["ts"].strftime("%Y-%m-%d"), collections.Counter())[m["speaker"]] += 1
    S["per_day"] = {d: dict(c) for d, c in per_day.items()}
    S["days"] = list(per_day.keys())
    S["kinds"] = dict(collections.Counter(m["kind"] for m in msgs))

    sessions, cur = [], [msgs[0]]
    for p, q in zip(msgs, msgs[1:]):
        if q["ts"] - p["ts"] > timedelta(minutes=a.gap): sessions.append(cur); cur = [q]
        else: cur.append(q)
    sessions.append(cur)
    S["sessions"] = [{"start": s[0]["ts"].strftime("%m-%d %H:%M"), "end": s[-1]["ts"].strftime("%m-%d %H:%M"),
                      "n": len(s), "init": s[0]["speaker"], "who": dict(collections.Counter(m["speaker"] for m in s)),
                      "first_id": s[0]["id"], "last_id": s[-1]["id"]} for s in sessions]
    S["session_initiators"] = dict(collections.Counter(s[0]["speaker"] for s in sessions))
    S["files"] = [[m["ts"].strftime("%m-%d"), m["speaker"], m["text"].strip()[3:].strip().splitlines()[0]] for m in msgs if m["kind"] == "file"]
    dom = collections.Counter(urlparse(u).netloc.replace("www.", "") for m in msgs for u in m["urls"])
    S["domains"] = dom.most_common(20)
    S["mentions"] = dict(collections.Counter(f"{m['speaker']}->{x}" for m in msgs for x in re.findall(r"@(\S+)", m["text"]) if x in speakers))

    json.dump(S, open(os.path.join(a.out, "stats.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump([{**m, "ts": m["ts"].isoformat()} for m in msgs], open(os.path.join(a.out, "messages.json"), "w", encoding="utf-8"), ensure_ascii=False)

    # ---- chunks
    for d, c in per_day.items():
        L = [m for m in msgs if m["ts"].strftime("%Y-%m-%d") == d]
        with open(os.path.join(a.out, "chunks", f"{d}.txt"), "w", encoding="utf-8") as f:
            f.write(f"=== {d} ({len(L)} msgs) ===\n")
            for m in L:
                f.write(f"#{m['id']} [{m['ts'].strftime('%H:%M')}] {m['speaker']}: {m['text']}\n")
    # suggested ranges for sub-agents
    ranges, acc, start = [], 0, None
    for d, c in per_day.items():
        n = sum(c.values())
        if start is None: start = d
        acc += n
        if acc >= a.range_size:
            ranges.append((start, d, acc)); start, acc = None, 0
    if start is not None: ranges.append((start, list(per_day)[-1], acc))
    with open(os.path.join(a.out, "chunks", "index.txt"), "w", encoding="utf-8") as f:
        f.write("date       msgs  speakers\n")
        for d, c in per_day.items():
            f.write(f"{d}  {sum(c.values()):4d}  " + ", ".join(f"{s} {n}" for s, n in c.most_common()) + "\n")
        f.write(f"\ntotal {len(msgs)} msgs, {len(sessions)} sessions (gap {a.gap} min)\n")
        f.write(f"\nsuggested sub-agent ranges (~{a.range_size} msgs each):\n")
        for i, (s0, s1, n) in enumerate(ranges, 1):
            f.write(f"  part{i}: {s0} ~ {s1}  ({n} msgs)\n")

    # ---- console summary
    print(f"format: {fmt} | room: {S['room']}")
    print(f"messages: {len(msgs)} | period: {S['period'][0]} ~ {S['period'][1]} | days: {len(per_day)} | sessions: {len(sessions)}")
    top = speakers[:12]
    print(f"speakers: {len(speakers)} — " + ", ".join(f"{s} {counts[s]}" for s in top) + (f", … +{len(speakers)-12} more" if len(speakers) > 12 else ""))
    if bots: print("bots (kept in counts, ignore for roles): " + ", ".join(bots))
    if S["system_msgs"]: print(f"system messages (입장/퇴장 등): {S['system_msgs']}")
    if dropped: print("dropped by --speakers: " + ", ".join(f"{s} {n}" for s, n in dropped.items()))
    print("kinds: " + json.dumps(S["kinds"], ensure_ascii=False))
    print(f"suggested ranges: {len(ranges)} -> see {os.path.join(a.out, 'chunks', 'index.txt')}")


if __name__ == "__main__":
    main()
