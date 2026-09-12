#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render the discussion-analysis HTML report from stats.json (parser) + analysis.json (your reading).

Usage:
  python build_report.py --data work --analysis analysis.json --out report.html [--anonymize] [--title "..."]
"""
import argparse, html, json, os, re

STATUS = {"done": ("st-done", "해결·결정"), "assigned": ("st-assigned", "담당 지정"), "open": ("st-open", "진행 중"),
          "drop": ("st-drop", "흐지부지"), "info": ("st-info", "정보공유")}
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
PALETTE_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]
e = html.escape


def anonymize(A, S):
    names = []
    profiled = {sp["name"] for sp in A.get("speakers", [])}
    extra = [{"name": s, "aliases": []} for s in S["speakers_order"] if s not in profiled]
    for i, sp in enumerate(A.get("speakers", []) + extra):
        label = f"화자{chr(65 + i)}" if i < 26 else f"화자{i + 1}"
        names.append((sp["name"], label))
        for al in sorted(sp.get("aliases", []), key=len, reverse=True):
            names.append((al, label))
        sp["name"], sp["aliases"] = label, []
    names.sort(key=lambda x: -len(x[0]))
    def sub(text):
        for src, dst in names:
            text = text.replace(src, dst)
        return text
    def walk(o):
        if isinstance(o, str): return sub(o)
        if isinstance(o, list): return [walk(x) for x in o]
        if isinstance(o, dict): return {k: (v if k in ("name", "aliases") else walk(v)) for k, v in o.items()}
        return o
    A2 = walk(A)
    mp = {src: dst for src, dst in names if src in S["speakers"]}
    S["speakers"] = {mp.get(k, k): v for k, v in S["speakers"].items()}
    S["speakers_order"] = [mp.get(k, k) for k in S["speakers_order"]]
    S["per_day"] = {d: {mp.get(k, k): v for k, v in c.items()} for d, c in S["per_day"].items()}
    return A2, S


def daily_chart(S, colors, peak_digest):
    days = S["days"]; sp = S["speakers_order"]
    W, H = 960, 260; L, R, T, B = 44, 16, 18, 40
    n = len(days); slot = (W - L - R) / n; bw = min(22, slot * 0.64)
    maxv = max(sum(S["per_day"][d].values()) for d in days) or 1
    step = 10 ** max(0, len(str(maxv)) - 1); step = step if maxv / step >= 3 else step / 2
    top = (int(maxv // step) + 1) * step; ph = H - T - B
    y = lambda v: T + ph - v / top * ph
    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="일자별 메시지 수">']
    t = 0
    while t <= top:
        out.append(f'<line x1="{L}" x2="{W-R}" y1="{y(t):.1f}" y2="{y(t):.1f}" class="grid"/><text x="{L-6}" y="{y(t)+4:.1f}" class="tick" text-anchor="end">{int(t)}</text>')
        t += step
    peak = max(days, key=lambda d: sum(S["per_day"][d].values()))
    for i, d in enumerate(days):
        vals = [S["per_day"][d].get(s, 0) for s in sp]; x = L + slot * i + (slot - bw) / 2; acc = 0
        tip = f"{d} · {sum(vals)}건 — " + ", ".join(f"{s} {v}" for s, v in zip(sp, vals) if v)
        for j, (s, v) in enumerate(zip(sp, vals)):
            if v <= 0: continue
            y0, y1 = y(acc + v), y(acc); last = all(vv == 0 for vv in vals[j + 1:])
            if last and (y1 - y0) > 5:
                out.append(f'<path d="M{x:.1f},{y1:.1f} V{y0+4:.1f} a4,4 0 0 1 4,-4 H{x+bw-4:.1f} a4,4 0 0 1 4,4 V{y1:.1f} Z" fill="{colors[s]}" data-tip="{e(tip)}"/>')
            else:
                out.append(f'<rect x="{x:.1f}" y="{y0:.1f}" width="{bw:.1f}" height="{max(0, y1-y0-(2 if acc else 0)):.1f}" fill="{colors[s]}" data-tip="{e(tip)}"/>')
            acc += v
        mm, dd = d[5:7].lstrip("0"), d[8:10].lstrip("0")
        lab = f"{mm}/{dd}" if (i == 0 or d[5:7] != days[i-1][5:7]) else dd
        out.append(f'<text x="{x+bw/2:.1f}" y="{H-B+15}" class="tick" text-anchor="middle">{lab}</text>')
        if d == peak:
            out.append(f'<text x="{x+bw/2:.1f}" y="{y(sum(vals))-7:.1f}" class="lab" text-anchor="middle">{sum(vals)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True); ap.add_argument("--analysis", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--anonymize", action="store_true"); ap.add_argument("--title")
    ap.add_argument("--pdf", action="store_true", help="also print a PDF next to the HTML (needs Edge/Chrome)")
    ap.add_argument("--browser", help="path to msedge/chrome for --pdf")
    ap.add_argument("--force", action="store_true", help="render even if check_analysis reports errors")
    a = ap.parse_args()
    S = json.load(open(os.path.join(a.data, "stats.json"), encoding="utf-8"))
    A = json.load(open(a.analysis, encoding="utf-8"))
    # shape check first: same sections, same depth, every run
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from check_analysis import check
    errors, warns = check(A, S)
    for w in warns: print("WARN ", w)
    for err in errors: print("ERROR", err)
    if errors and not a.force:
        print(f"analysis.json에 오류 {len(errors)}건 — 고친 뒤 다시 실행 (--force로 무시 가능)"); sys.exit(1)
    if a.anonymize: A, S = anonymize(A, S)
    all_speakers = S["speakers_order"]
    TOPK = 8
    # open chats have dozens of speakers: chart/cards show the top ones, the rest fold into "그 외"
    if len(all_speakers) > TOPK:
        main_sp = all_speakers[:TOPK - 1]; rest = all_speakers[TOPK - 1:]
        rest_label = f"그 외 {len(rest)}명"
        for d, c in S["per_day"].items():
            r = sum(c.pop(s, 0) for s in rest)
            if r: c[rest_label] = r
        rest_stat = {"msgs": sum(S["speakers"][s]["msgs"] for s in rest), "share": round(sum(S["speakers"][s]["share"] for s in rest), 1),
                     "avg_len": 0, "photo": sum(S["speakers"][s]["photo"] for s in rest), "links": sum(S["speakers"][s]["links"] for s in rest),
                     "file": sum(S["speakers"][s]["file"] for s in rest), "top_hours": []}
        S["speakers"][rest_label] = rest_stat
        sp_order = main_sp + [rest_label]
    else:
        sp_order = all_speakers; rest_label = None
    colors = {s: f"var(--s{i+1})" for i, s in enumerate(sp_order)}
    if rest_label: colors[rest_label] = "var(--muted)"
    title = a.title or A.get("title") or "대화 논의 분석"
    days = S["days"]; n_days = len(days)
    stt = {k: 0 for k in STATUS}
    for t in A["threads"]: stt[t["status"]] = stt.get(t["status"], 0) + 1
    speakers_by_name = {s["name"]: s for s in A.get("speakers", [])}
    daily_map = {d["date"]: d["digest"] for d in A.get("daily", [])}
    groups = A.get("groups") or [{"id": g, "title": g} for g in dict.fromkeys(t["group"] for t in A["threads"])]

    def badge(t):
        cls, lab = STATUS.get(t["status"], ("st-info", t["status"]))
        return f'<span class="status {cls}">{e(t.get("status_label") or lab)}</span>'

    def thread_card(t):
        nxt = f'<p class="tnext"><b>확인 포인트</b> {t["next"]}</p>' if t.get("next") else ""
        return f"""<article class="topic" id="t{A['threads'].index(t)}"><header><h4>{e(t['title'])}</h4>{badge(t)}</header>
<p class="tmeta">{e(t.get('span',''))} · 주도 {e(t.get('lead',''))} · 참여 {e(t.get('participants',''))}</p>
<p>{t['flow']}</p>{('<p class="tend"><b>결말</b> ' + t['end'] + '</p>') if t.get('end') else ''}{nxt}</article>"""

    groups_html = []
    for g in groups:
        ts = [t for t in A["threads"] if t["group"] == g["id"]]
        if not ts: continue
        groups_html.append(f'<div class="group"><h3>{e(g["title"])} <span class="muted">{len(ts)}</span></h3>' +
                           (f'<p class="gdesc">{g["desc"]}</p>' if g.get("desc") else "") + "".join(thread_card(t) for t in ts) + "</div>")

    open_rows = [t for t in A["threads"] if t["status"] in ("assigned", "open", "drop")]
    open_rows.sort(key=lambda t: ["drop", "assigned", "open"].index(t["status"]))
    open_html = "".join(f"<tr><td>{badge(t)}</td><td><a href='#t{A['threads'].index(t)}'>{e(t['title'])}</a></td><td>{e(t.get('lead',''))}</td><td>{t.get('next') or t.get('end','')}</td></tr>" for t in open_rows)

    speaker_cards = []
    for s in sp_order:
        v = S["speakers"][s]; prof = speakers_by_name.get(s, {})
        hrs = "·".join(f"{h}시" for h in v["top_hours"])
        bot = " <span class='role'>(봇)</span>" if s in S.get("bots", []) else ""
        stat = (f"{v['msgs']:,}건 ({v['share']}%) · 평균 {v['avg_len']}자 · 사진 {v['photo']} · 링크 {v['links']} · 파일 {v['file']}" + (f" · 주 활동 {hrs}" if hrs else ""))
        speaker_cards.append(f"""<div class="card sp"><h3><span class="sw" style="background:{colors[s]}"></span>{e(s)}{bot} <span class="role">{e(prof.get('role',''))}</span></h3>
<p class="spstat">{stat}</p>{prof.get('profile','')}</div>""")
    # profiles written for people outside the top group still deserve a card
    for prof in A.get("speakers", []):
        if prof["name"] not in sp_order and prof["name"] in S["speakers"]:
            v = S["speakers"][prof["name"]]
            speaker_cards.append(f"""<div class="card sp"><h3><span class="sw" style="background:var(--muted)"></span>{e(prof['name'])} <span class="role">{e(prof.get('role',''))}</span></h3>
<p class="spstat">{v['msgs']:,}건 ({v['share']}%)</p>{prof.get('profile','')}</div>""")

    daily_rows = "".join(
        f"<tr><td class='dnum'>{d[5:].replace('-', '/').lstrip('0')}<span class='wk'>{['월','화','수','목','금','토','일'][__import__('datetime').date.fromisoformat(d).weekday()]}</span></td>"
        f"<td class='num'>{sum(S['per_day'][d].values())}</td><td>{daily_map.get(d, '<span class=muted>—</span>')}</td></tr>" for d in days)

    gloss = "".join(f"<tr><th scope='row'>{e(g['term'])}</th><td>{g['desc']}</td></tr>" for g in A.get("glossary", []))
    notes = "".join(f"<li>{n}</li>" for n in A.get("notes", []))
    legend = "".join(f'<span><i style="background:{colors[s]}"></i>{e(s)}</span>' for s in sp_order)
    status_line = "".join(f'<span class="status {STATUS[k][0]}">{STATUS[k][1]} {stt[k]}</span>' for k in ["done", "assigned", "open", "drop", "info"] if stt.get(k))
    n_all = len(all_speakers)
    sname = " · ".join(all_speakers) if n_all <= 6 else f"주요 {min(n_all, TOPK-1)}명: " + " · ".join(all_speakers[:TOPK-1])
    css_series = "".join(f"--s{i+1}:{c};" for i, c in enumerate(PALETTE[:len(sp_order)]))
    css_series_dark = "".join(f"--s{i+1}:{c};" for i, c in enumerate(PALETTE_DARK[:len(sp_order)]))

    page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Gowun+Dodum&family=IBM+Plex+Sans+KR:wght@400;500;600&display=swap">
<style>
:root{{color-scheme:light;--bg:#f4f5f8;--surface:#fff;--surface2:#eef0f5;--ink:#15181f;--ink2:#4d5563;--muted:#7d8594;--line:#e2e5ec;--line2:#cdd2dc;--accent:#3d4f8f;--accent-ink:#fff;--accent-soft:#e6e9f6;{css_series}--good:#0ca30c;--warn:#fab219;--crit:#d03b3b;
--fb:"IBM Plex Sans KR","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;--fd:"Gowun Dodum","IBM Plex Sans KR","Malgun Gothic",sans-serif}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{color-scheme:dark;--bg:#111318;--surface:#181b22;--surface2:#20242d;--ink:#f2f3f6;--ink2:#c2c7d1;--muted:#8b92a0;--line:#2a2f3a;--line2:#3a404d;--accent:#8fa0e6;--accent-ink:#0f1220;--accent-soft:#252b45;{css_series_dark}}}}}
:root[data-theme="dark"]{{color-scheme:dark;--bg:#111318;--surface:#181b22;--surface2:#20242d;--ink:#f2f3f6;--ink2:#c2c7d1;--muted:#8b92a0;--line:#2a2f3a;--line2:#3a404d;--accent:#8fa0e6;--accent-ink:#0f1220;--accent-soft:#252b45;{css_series_dark}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--fb);font-size:15.5px;line-height:1.65}}
a{{color:var(--accent)}}.wrap{{display:grid;grid-template-columns:210px minmax(0,1fr);gap:36px;max-width:1240px;margin:0 auto;padding:32px 28px 80px}}
@media (max-width:900px){{.wrap{{grid-template-columns:1fr;gap:12px;padding:20px 16px}}nav{{position:static!important}}}}
nav{{position:sticky;top:24px;align-self:start;font-size:13.5px;border-right:1px solid var(--line);padding-right:14px}}
nav .eyebrow{{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}}
nav a{{display:block;color:var(--ink2);text-decoration:none;padding:5px 0 5px 10px;border-left:2px solid transparent;margin-left:-11px}}nav a:hover{{color:var(--ink);border-left-color:var(--accent)}}nav a.sub{{font-size:12.5px;padding-left:22px;color:var(--muted)}}
h1{{font-family:var(--fd);font-weight:400;font-size:36px;line-height:1.2;margin:0 0 6px;text-wrap:balance}}.sub{{color:var(--ink2);margin:0 0 4px}}.src{{font-size:12.5px;color:var(--muted)}}
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:22px 0 6px}}.tile{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px 16px}}.tile .tl{{font-size:12px;color:var(--muted)}}.tile .tv{{font-size:28px;font-weight:600;line-height:1.15}}.tile .td{{font-size:12.5px;color:var(--ink2)}}
section{{margin-top:52px}}section>h2{{font-family:var(--fd);font-weight:400;font-size:26px;margin:0 0 4px;display:flex;align-items:baseline;gap:12px}}section>h2 .no{{font-size:13px;color:var(--muted)}}.lead{{color:var(--ink2);margin:0 0 18px;max-width:70ch}}
h3{{font-size:18px;font-weight:600;margin:30px 0 10px}}h4{{font-size:16px;font-weight:600;margin:0}}p{{max-width:74ch}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px 20px;margin:12px 0}}.card h3{{margin-top:0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}}
.sp .role{{font-size:13px;font-weight:500;color:var(--muted);margin-left:6px}}.sp .spstat{{font-size:12.5px;color:var(--muted);margin:-4px 0 8px}}.sp p{{margin:6px 0}}
.summary{{background:var(--surface);border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:0 10px 10px 0;padding:14px 22px;margin:14px 0}}.summary li{{margin:6px 0;max-width:80ch}}
.chart{{width:100%;height:auto;display:block}}.chart .grid{{stroke:var(--line)}}.chart .tick{{font-size:11.5px;fill:var(--muted)}}.chart .lab{{font-size:12px;fill:var(--ink2);font-weight:600}}.chart [data-tip]:hover{{opacity:.8}}
.legend{{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--ink2);margin:4px 0 10px}}.legend i{{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}}
.tablewrap{{overflow-x:auto;margin:10px 0}}table.data{{border-collapse:collapse;width:100%;font-size:14px;background:var(--surface);border:1px solid var(--line)}}table.data th,table.data td{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}table.data thead th{{font-size:12px;color:var(--muted);font-weight:500;background:var(--surface2)}}table.data tbody th{{font-weight:600;white-space:nowrap}}td.num{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--muted)}}td.dnum{{white-space:nowrap;font-weight:600}}.wk{{font-weight:400;color:var(--muted);font-size:12px;margin-left:4px}}
.sw{{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:7px;vertical-align:-1px}}.muted{{color:var(--muted);font-weight:400;font-size:14px}}
.group{{margin-top:26px}}.gdesc{{color:var(--ink2);margin:0 0 8px}}
.topic{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px 18px;margin:10px 0}}.topic header{{display:flex;align-items:center;gap:12px;flex-wrap:wrap}}.topic .tmeta{{font-size:13px;color:var(--muted);margin:4px 0 8px}}.topic p{{margin:6px 0}}.topic .tend,.topic .tnext{{font-size:14px;color:var(--ink2)}}
.status{{font-size:12px;padding:3px 9px;border-radius:99px;font-weight:500;white-space:nowrap}}.st-done{{background:color-mix(in srgb,var(--good) 16%,transparent)}}.st-open{{background:color-mix(in srgb,var(--warn) 22%,transparent)}}.st-drop{{background:color-mix(in srgb,var(--crit) 14%,transparent)}}.st-info{{background:var(--surface2);color:var(--ink2)}}.st-assigned{{background:var(--accent-soft)}}
.statusline{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:13.5px;margin:8px 0}}
footer{{margin-top:56px;font-size:12.5px;color:var(--muted);border-top:1px solid var(--line);padding-top:12px}}footer ul{{margin:6px 0;padding-left:18px}}
#tip{{position:fixed;pointer-events:none;background:var(--ink);color:var(--bg);font-size:12.5px;padding:6px 9px;border-radius:6px;opacity:0;z-index:9;max-width:320px}}
@media print{{
 @page{{size:A4;margin:14mm 13mm}}
 :root{{color-scheme:light;--bg:#f4f5f8;--surface:#fff;--surface2:#eef0f5;--ink:#15181f;--ink2:#4d5563;--muted:#7d8594;--line:#e2e5ec;--line2:#cdd2dc;--accent:#3d4f8f;--accent-ink:#fff;--accent-soft:#e6e9f6;{css_series}}}
 *{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
 html{{background:var(--bg)}}
 body{{font-size:11pt;line-height:1.5;background:var(--bg)}}
 .wrap{{display:block;max-width:none;padding:0;margin:0}}nav,#tip{{display:none!important}}
 h1{{font-size:24pt}}section{{margin-top:22pt}}section>h2{{font-size:17pt}}h3{{font-size:13pt;margin:16pt 0 6pt}}h4{{font-size:11.5pt}}
 .tiles{{grid-template-columns:repeat(4,1fr);gap:8px;margin:12pt 0 4pt}}.tile .tv{{font-size:18pt}}.tile{{padding:8px 12px}}
 .grid{{grid-template-columns:1fr 1fr;gap:10px}}
 .card,.topic,.tile,.summary,tr{{break-inside:avoid}}.group{{break-inside:auto}}section>h2,h3{{break-after:avoid}}
 .topic{{padding:10px 14px;margin:8px 0}}.topic p{{margin:4px 0;font-size:10.5pt}}.topic .tmeta{{font-size:9.5pt}}
 table.data{{font-size:9.5pt}}table.data th,table.data td{{padding:5px 7px}}
 .chart{{max-height:200px}}.status{{border:1px solid var(--line2)}}
 a{{color:inherit;text-decoration:none}}
 footer{{font-size:9pt}}
}}
</style></head><body><div id="tip"></div><div class="wrap">
<nav><div class="eyebrow">목차</div><a href="#s1">1. 한눈에 보기</a><a href="#s2">2. 화자와 역할</a><a href="#s3">3. 날짜별 논의</a><a href="#s4">4. 주제별 흐름과 결말</a>
{''.join(f'<a class="sub" href="#g{g["id"]}">{e(g["title"])}</a>' for g in groups if any(t["group"] == g["id"] for t in A["threads"]))}
<a href="#s5">5. 열려 있거나 사라진 것</a>{'<a href="#s6">6. 용어집</a>' if gloss else ''}</nav>
<main>
<header><h1>{e(title)}</h1><p class="sub">{A.get('subtitle','')}</p><div class="src">{e(A.get('room') or S.get('room',''))} · {S['period'][0]} ~ {S['period'][1]}</div>
<div class="tiles"><div class="tile"><span class="tl">기간</span><div class="tv">{n_days}일</div><span class="td">{S['period'][0]} → {S['period'][1]}</span></div>
<div class="tile"><span class="tl">화자</span><div class="tv">{n_all}명</div><span class="td">{e(sname)}</span></div>
<div class="tile"><span class="tl">메시지</span><div class="tv">{S['n_msgs']:,}</div><span class="td">하루 평균 {round(S['n_msgs']/max(1,n_days))}건 · 세션 {len(S['sessions'])}개</span></div>
<div class="tile"><span class="tl">스레드</span><div class="tv">{len(A['threads'])}</div><span class="td">해결 {stt.get('done',0)} · 진행/담당 {stt.get('open',0)+stt.get('assigned',0)} · 흐지부지 {stt.get('drop',0)}</span></div></div></header>

<section id="s1"><h2><span class="no">01</span>한눈에 보기</h2>
<div class="summary"><ul>{''.join(f'<li>{s}</li>' for s in A.get('summary', []))}</ul></div>
<div class="statusline"><b>스레드 {len(A['threads'])}개 상태</b>{status_line}</div></section>

<section id="s2"><h2><span class="no">02</span>화자와 역할</h2><p class="lead">발화량보다 '무엇을 가져오고 누구에게 어떻게 반응하는가'로 읽은 역할.</p>
<div class="grid">{''.join(speaker_cards)}</div></section>

<section id="s3"><h2><span class="no">03</span>날짜별 논의</h2><p class="lead">막대는 그날 오간 메시지 수, 표는 그날 실제로 논의된 것.</p>
{daily_chart(S, colors, daily_map)}<div class="legend">{legend}</div>
<div class="tablewrap"><table class="data"><thead><tr><th>날짜</th><th>건수</th><th>논의</th></tr></thead><tbody>{daily_rows}</tbody></table></div></section>

<section id="s4"><h2><span class="no">04</span>주제별 흐름과 결말</h2><p class="lead">같은 사안이 여러 날에 걸쳐 어떻게 시작되고 발전했는지, 누가 이어받았는지, 어떻게 끝났는지. 상태 배지: {status_line}</p>
{''.join(gh.replace('<div class="group">', f'<div class="group" id="g{g["id"]}">', 1) for gh, g in zip(groups_html, [g for g in groups if any(t["group"] == g["id"] for t in A["threads"])]))}</section>

<section id="s5"><h2><span class="no">05</span>열려 있거나 사라진 것</h2><p class="lead">담당만 정해졌거나, 진행 중이거나, 답 없이 사라진 스레드. 후속 확인이 필요한 목록이다.</p>
<div class="tablewrap"><table class="data"><thead><tr><th>상태</th><th>스레드</th><th>주도</th><th>확인 포인트 / 마지막 상태</th></tr></thead><tbody>{open_html or '<tr><td colspan=4 class=muted>없음</td></tr>'}</tbody></table></div></section>

{f'<section id="s6"><h2><span class="no">06</span>용어집</h2><div class="tablewrap"><table class="data"><thead><tr><th>이름</th><th>대화 맥락에서 파악한 것</th></tr></thead><tbody>{gloss}</tbody></table></div></section>' if gloss else ''}

<footer>{'<ul>' + notes + '</ul>' if notes else ''}세션 = 앞 메시지와 60분 이상 벌어지면 새 세션. 사진·파일은 표시만 남고 내용은 없음. 생성 {__import__('datetime').date.today().isoformat()}</footer>
</main></div>
<script>(function(){{var t=document.getElementById('tip');document.addEventListener('mousemove',function(ev){{var el=ev.target.closest&&ev.target.closest('[data-tip]');if(!el){{t.style.opacity=0;return}}t.textContent=el.getAttribute('data-tip');t.style.opacity=1;var x=ev.clientX+14,y=ev.clientY+14;if(x+t.offsetWidth>innerWidth-8)x=ev.clientX-t.offsetWidth-10;if(y+t.offsetHeight>innerHeight-8)y=ev.clientY-t.offsetHeight-10;t.style.left=x+'px';t.style.top=y+'px'}})}})();</script>
</body></html>"""
    with open(a.out, "w", encoding="utf-8") as f: f.write(page)
    print(f"wrote {a.out} ({len(page):,} bytes) — threads {len(A['threads'])}, days {n_days}, speakers {n_all}")
    if a.pdf:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from export_pdf import html_to_pdf
        pdf = html_to_pdf(a.out, os.path.splitext(a.out)[0] + ".pdf", a.browser)
        print(f"wrote {pdf} ({os.path.getsize(pdf):,} bytes)")


if __name__ == "__main__":
    main()
