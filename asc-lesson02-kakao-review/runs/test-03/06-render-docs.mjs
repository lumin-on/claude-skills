// 03-coordination.md + 06-final-report.md 생성
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const rd = p => fs.readFileSync(path.join(here, p), 'utf8');
const final = JSON.parse(rd('04-final.json'));
const logj = JSON.parse(rd('03-coordination-log.json'));
const plan = JSON.parse(rd('work/plan.json'));
const byId = Object.fromEntries(final.topics.map(t => [t.id, t]));
const dec = {}; for (const d of logj.decisions) (dec[d.topic_id] ||= []).push(d);
const cite = a => a.map(e => `${e.line} “${e.quote}”`).join('; ') || '없음';
const A = {}; for (const k of ['c1', 'c2', 'c3', 'c4']) for (const t of JSON.parse(rd(`chunks/${k}-analyst-output.json`)).topics) A[t.id] = t;
const esc = s => String(s).replace(/\|/g, '｜');

// ── 조율 기록 ──
const kinds = logj.decisions.reduce((m, d) => (m[d.decision] = (m[d.decision] || 0) + 1, m), {});
let co = `# 메인 Agent 조율 기록 (runs/test-03)

- 입력: examples/synthetic-chat-long.txt — 합성 대화 132줄, 5,861토큰, 2026-10-05~10-09 (실제 인물·기관 아님)
- 청킹: \`scripts/chunk_by_tokens.py\`(tiktoken) 예산 2,000토큰 → 4청크, 커버리지 완전
- 실행: 청크마다 A(kakao-agenda-analyst) → 저장·검증 → B(kakao-evidence-reviewer). 청크끼리는 동시, A→B는 순차
- A 안건 29개 · B verdict accept 22 / revise 7 / hold 0 · 누락 안건 0
- 메인 결정 ${logj.decisions.length}건

## 이번 실행에서 달라진 것 (오픈소스 도입 효과)

| 항목 | 이전(runs/test-02, 실제 대화 11,341줄) | 이번(runs/test-03, 새 파이프라인) |
|---|---|---|
| 청크 분할 | 글자 수 눈대중, 마지막 줄 1개 누락 | tiktoken 토큰 예산, 커버리지 완전 |
| 인용 줄 번호 | 1,214건 중 **16건 드리프트**(1.3%) | 101건 중 **0건** |
| Subagent 파일 읽기 | offset/limit 분할 읽기(드리프트 원인) | 전원 tool_uses 1회, 한 번에 읽음 |
| 스키마 위반 | status 오타 2건을 사람이 발견 | ajv가 0건 확인(위반 시 JSON Pointer로 위치 표시) |
| 검증 시점 | 보고서 작성 후 수동 | A 직후·B 직후·최종 3회 자동 관문 |

## 조율 원칙
1. **상태값은 agent 정의의 5개 + null만 사용.** B가 제안한 '추정'·'잠정' 계열은 허용값 밖이라 '판단 보류'로 매핑하고 지적의 실질만 채택했다(test-01·test-02와 동일 원칙).
2. **청크 간 연결은 메인 책임.** B는 자기 청크만 보므로, 앞 청크의 "이후 청크 확인 필요"가 뒤 청크에서 해소되는지 메인이 원문으로 확인하고 상태를 갱신했다(${logj.decisions.filter(d => d.decision.includes('청크 간')).length}건).
3. **인용 추가 시 원문 대조 강제.** 조율 스크립트의 \`q(line, quote)\`가 원문에 없는 인용을 넣으면 빌드를 중단시킨다.
4. **억지 합의 없음.** 원문 자체의 모순은 사람 확인 사항으로 남겼다.

## 검토자가 잡아낸 것 중 주목할 점
**c1-T03 — 원문의 날짜·요일 불일치.** L00017에서 10월 24일이 토요일이면 10월 17일도 토요일인데, L00023은 "10월 17일 금요일"이라고 적는다. 메인이 달력으로 확인한 결과 2026-10-05가 월요일이면 10/16이 금요일, 10/17이 토요일로 검토자 지적이 맞다. **합성 대화를 만들 때 들어간 오류지만 실제 단톡방에도 흔한 유형이라 고치지 않고 그대로 두고 사람 확인 사항으로 남겼다.** 분석자는 원문을 그대로 옮겼을 뿐이므로 분석 실패가 아니라, 검토 단계가 실제로 작동한다는 증거다.

그 밖에 B는 c4-T04(강사 소개 "반영하겠습니다"를 완료로 분류)와 c4-T06(무기한 보류를 해결·결정으로 분류)에서 담당 지정과 완료의 혼동을 잡아냈고, 둘 다 채택했다.

## 결정 종류
| 결정 | 건수 |
|---|---|
${Object.entries(kinds).map(([k, v]) => `| ${esc(k)} | ${v} |`).join('\n')}

## 사람이 확인할 사항
1. **입금 마감이 10/16(금)인지 10/17(토)인지** — 원문 표기 불일치(c1-T03).
2. 강사 성함이 원문에 한 번도 나오지 않는다 — 홍보물·교통비 지급에 필요(c3-T03, B 지적).
3. 강사 소개가 인쇄본에 실제 반영됐는지(c4-T04) — 발주 시점까지 확인 발언 없음.
4. 간식 담당자·예산(c3-T05), 사진 촬영 담당자(c4-T12), 뒤풀이 장소(c4-T06) 미정.
5. 간식 "50명 기준"과 소강당 수용 60명의 인원 기준 차이가 조정된 적 없음(B c3 지적).

## 안건별 결정표
| ID | 청크 | A 상태 → 최종 | B | 메인 결정 | 이유(요약) |
|---|---|---|---|---|---|
`;
for (const t of final.topics) {
  const a = A[t.id], ds = dec[t.id] || [];
  const from = `${a.status ?? 'null'}/${a.certainty}`, to = `${t.status ?? 'null'}/${t.certainty}`;
  co += `| ${t.id} | ${t.chunk} | ${from === to ? to : from + ' → ' + to} | ${t.review?.verdict ?? '-'} | ${esc([...new Set(ds.map(d => d.decision))].join(', '))} | ${esc(ds.map(d => d.reason).join(' / ').slice(0, 200))} |\n`;
}
co += '\n전체 이유 원문은 03-coordination-log.json 참조.\n';
fs.writeFileSync(path.join(here, '03-coordination.md'), co);

// ── 최종 보고서 ──
const st = final.topics.reduce((m, t) => (m[t.status ?? 'null'] = (m[t.status ?? 'null'] || 0) + 1, m), {});
let rp = `# 카카오톡 안건 판단·검증 결과 (runs/test-03)

- 입력: examples/synthetic-chat-long.txt — 합성 대화 132줄, 2026-10-05(월)~10-09(금), 가상 인물 4명
- 근거 줄 ID: runs/test-03/work/indexed.txt (L00001~L00132)
- 파이프라인: tiktoken 청킹(4청크) → 분석 Subagent 4회 → ajv·RapidFuzz 검증 → 검토 Subagent 4회 → 검증 → 메인 조율 → 최종 검증
- 안건 ${final.topics.length}개 · 상태 ${Object.entries(st).map(([k, v]) => `${k} ${v}`).join(', ')}
- 검토 verdict: accept 22 / revise 7 / hold 0 · 누락 안건 0
- 검증: 스키마 위반 0 · 인용 대조 최종 118건 불일치 0

## 요약
${final.summary}

## 사용한 오픈소스
| 도구 | 블록 | 이번 실행에서 한 일 |
|---|---|---|
| [openai/tiktoken](https://github.com/openai/tiktoken) | 줄 번호·청크 분할 | 132줄 5,861토큰을 예산 2,000으로 4청크 분할, 커버리지 완전 확인 |
| [rapidfuzz/RapidFuzz](https://github.com/rapidfuzz/RapidFuzz) | 인용 검증 | 분석 101건·검토 88건·최종 118건 대조, 불일치 0 |
| [ajv-validator/ajv](https://github.com/ajv-validator/ajv) | 구조 검증 | 분석·검토·최종 9개 파일 검사, 위반 0 |

## 스레드별 최신 상태 (대화 종료 10/9 기준)

`;
for (const [th, ids] of Object.entries(final.threads)) {
  const ts = ids.map(i => byId[i]).filter(Boolean);
  rp += `### ${th}\n\n| ID | 안건 | 상태 | 확신 | 담당 | 기한 | B | 메인 |\n|---|---|---|---|---|---|---|---|\n`;
  for (const t of ts) {
    const ds = (dec[t.id] || []).map(d => d.decision);
    const md = ds.some(d => d.includes('청크 간')) ? '청크 간 갱신' : ds.some(d => d.startsWith('B')) ? 'B 채택' : '채택';
    rp += `| ${t.id} | ${esc(t.title)} | ${t.status ?? '판단 보류'} | ${t.certainty} | ${esc(t.owner ?? '—')} | ${esc(t.deadline ?? '—')} | ${t.review?.verdict ?? '—'} | ${md} |\n`;
  }
  rp += '\n';
}
rp += `## 사람이 확인할 사항
1. **입금 마감 10/16(금) vs 10/17(토)** — 원문의 날짜·요일 표기가 어긋난다(c1-T03). 검토 Subagent가 발견.
2. 강사 성함이 원문에 없음 — 홍보물·교통비 지급에 필요(c3-T03).
3. 강사 소개의 홍보물 반영 여부 미확인(c4-T04).
4. 미정: 간식 담당자·예산(c3-T05), 사진 촬영 담당자(c4-T12), 뒤풀이 장소(c4-T06).
5. 간식 "50명 기준"과 소강당 수용 60명의 기준 차이(c3-T05).

## 안건 상세

`;
for (const [th, ids] of Object.entries(final.threads)) {
  rp += `### ${th}\n\n`;
  for (const t of ids.map(i => byId[i]).filter(Boolean)) {
    const ds = dec[t.id] || [];
    rp += `#### ${t.id} ${t.title}

- 상태: ${t.status ?? '판단 보류'} / 확신: ${t.certainty}
- 판단: ${t.conclusion}
- 담당: ${t.owner ?? '미확정/해당 없음'} · 기한: ${t.deadline ?? '미확정/해당 없음'}
- 근거: ${cite(t.evidence)}
- 반대 근거: ${cite(t.counter_evidence)}
- 가정: ${t.assumptions.join('; ') || '없음'}
- 모르는 점: ${t.unknowns.join('; ') || '없음'}
- 다음 확인: ${t.next_check}
- 검토자 ${t.review?.verdict ?? '—'}: ${t.review?.reason ?? ''}
${t.review?.proposed_change ? `- 검토자 수정 제안: ${t.review.proposed_change}\n` : ''}- 메인: ${ds.map(d => `${d.decision} — ${d.reason}`).join(' / ') || '채택'}

`;
  }
}
rp += `## 기록
- 조율 상세: 03-coordination.md, 03-coordination-log.json
- 검증 결과: schema-check-*.json, citation-check-*.json
- A/B 실제 입력·응답: chunks/
- 이 보고서는 사람의 최종 검토 전 초안이며 외부 게시·발송·과제 제출을 하지 않았다.
`;
fs.writeFileSync(path.join(here, '06-final-report.md'), rp);
console.log('coordination', co.length, 'chars | report', rp.length, 'chars');
