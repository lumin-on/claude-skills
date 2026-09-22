// 메인 Agent 조율: 4청크 A/B 결과 → 04-final.json + 03-coordination-log.json
// A/B 원본 파일은 수정하지 않는다. 모든 변경은 아래 결정표에 근거하고 로그로 남긴다.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const rd = p => fs.readFileSync(path.join(here, p), 'utf8');
const src = rd('work/normalized.txt').split('\n');
const lineText = id => src[Number(id.slice(1)) - 1] ?? '';
const q = (line, quote) => { // 메인이 인용을 추가할 때 원문 대조 강제
  if (!lineText(line).includes(quote)) throw new Error(`quote mismatch: ${line} | ${quote}`);
  return { line, quote };
};

const A = {}, B = {};
for (const k of ['c1', 'c2', 'c3', 'c4']) {
  A[k] = JSON.parse(rd(`chunks/${k}-analyst-output.json`));
  B[k] = JSON.parse(rd(`chunks/${k}-reviewer-output.json`));
}
const topics = Object.values(A).flatMap(a => a.topics.map(t => JSON.parse(JSON.stringify(t))));
const reviews = Object.fromEntries(Object.values(B).flatMap(r => r.reviews.map(x => [x.topic_id, x])));
const T = Object.fromEntries(topics.map(t => [t.id, t]));
const log = [];
const SCHEMA_NOTE = "B가 제안한 '추정'·'잠정' 계열 값은 agent 정의의 certainty 허용값(확정/판단 보류) 밖이라 '판단 보류'로 매핑했다. 지적의 실질은 채택.";

const set = (id, { status, certainty, owner, deadline, conclusion, evidence, counter, unknowns, assumptions, next_check, decision, why }) => {
  const t = T[id]; const ch = [];
  if (status !== undefined && t.status !== status) { ch.push(`status ${t.status}→${status}`); t.status = status; }
  if (certainty && t.certainty !== certainty) { ch.push(`certainty ${t.certainty}→${certainty}`); t.certainty = certainty; }
  if (owner !== undefined) { ch.push(`owner ${t.owner}→${owner}`); t.owner = owner; }
  if (deadline !== undefined) { ch.push(`deadline ${t.deadline}→${deadline}`); t.deadline = deadline; }
  if (conclusion) { t.conclusion += ' ' + conclusion; ch.push('conclusion 보강'); }
  for (const [arr, key] of [[evidence, 'evidence'], [counter, 'counter_evidence']]) {
    if (arr) { for (const e of arr) if (!t[key].some(x => x.line === e.line && x.quote === e.quote)) t[key].push(e); ch.push(`${key} 추가`); }
  }
  for (const [arr, key] of [[unknowns, 'unknowns'], [assumptions, 'assumptions']]) {
    if (arr) { for (const u of arr) if (!t[key].includes(u)) t[key].push(u); ch.push(`${key} 추가`); }
  }
  if (next_check) { t.next_check = next_check; ch.push('next_check'); }
  log.push({ topic_id: id, decision, reason: why, changes: ch });
};

// ── 1. B revise 7건에 대한 메인 결정 ──────────────────────────────
set('c1-T02', { decision: 'B 채택', why: 'B: L00004 날짜 헤더로 "이번 주 금요일"을 2026-10-09로 특정 가능. 메인이 원문 확인 후 채택.', deadline: '2026-10-09(금) — L00004 날짜 헤더 기준 산출값, 원문에 날짜 자체는 없음', assumptions: ['L00004의 날짜 헤더가 이후 메시지의 발화일을 가리킨다고 봄'], evidence: [q('L00004', '2026년 10월 5일 월요일')] });

set('c1-T03', { decision: 'B 채택(중요)', why: 'B가 원문 자체의 모순을 발견: L00017에서 10/24가 토요일이면 10/17도 토요일이라 L00023의 "10월 17일 금요일"은 요일이 어긋난다. 메인이 달력 확인 — 2026-10-05가 월요일이면 10/16이 금요일, 10/17이 토요일로 B 지적이 맞다. 합성 대화 작성 시 들어간 오류이나, 실제 대화에도 흔한 유형이라 고치지 않고 사람 확인 사항으로 남긴다.', certainty: '판단 보류', deadline: '10월 17일(원문 표기 "금요일"과 불일치 — L00017 기준 10/17은 토요일. 10/16(금) 또는 10/17(토) 중 확정 필요)', conclusion: '[메인] 원문에 날짜·요일 표기 불일치가 있어 마감일을 단정하지 않는다.', counter: [q('L00017', '10월 24일 토요일만 비어 있다고 합니다')], unknowns: ['입금 마감이 10/16(금)인지 10/17(토)인지 — 사람 확인 필요'] });

set('c1-T04', { decision: 'B 취지 채택·certainty는 스키마로 매핑', why: 'B: "여쭤볼까 하는데"는 확약이 아닌 의향 표명이라 certainty 확정은 과함. B가 제안한 "추정"은 허용값 밖. ' + SCHEMA_NOTE, certainty: '판단 보류', conclusion: '[메인] 진행자A의 연락은 확약이 아니라 의향 표명(L00025)이고 연락 기한이 없다. 참여자D의 연락처 전달은 작년 강사 회신 결과에 종속된 미결 사항.', unknowns: ['강사 섭외 마감 시한이 정해진 적 없음'] });

set('c2-T03', { decision: 'B 채택', why: 'B: L00035 날짜 헤더로 "금요일"을 2026-10-09로 특정 가능. 채택.', deadline: '금요일(2026-10-09, L00035 날짜 헤더 기준)', evidence: [q('L00035', '2026년 10월 6일 화요일')], unknowns: ['L00044 "예정대로"가 가리키는 최초 합의 시점은 c1에서 확인됨(L00012)'] });

set('c2-T04', { decision: 'B 취지 채택·certainty는 스키마로 매핑', why: 'B: 원문이 "최대한"·"일단"이라는 잠정 표현인데 certainty 확정은 분석자 자신의 counter_evidence와 모순. B의 "잠정/추정" 제안은 허용값 밖. ' + SCHEMA_NOTE, certainty: '판단 보류', conclusion: '[메인] 10/24 날짜와 10/17 입금 마감 모두 대체 장소 확보에 종속된 잠정 유지이며, 확보 실패 시 재검토 여지가 남아 있었다.', next_check: '장소 확정 실패 시 입금 마감 재공지 필요 여부 — c4-T07에서 유지 확정됨' });

set('c4-T04', { decision: 'B 채택', why: 'B: "반영하겠습니다"는 의사표시일 뿐이고, 인쇄 발주 발언(L00111)·발주 보고(L00120) 어디에도 강사 소개 반영 확인이 없다. 담당 지정과 완료의 혼동. 메인이 원문 재확인 후 채택.', status: '담당 지정', conclusion: '[메인] 자료 전달은 완료(L00098~L00099)됐으나 홍보물 반영은 미확인. 인쇄 발주 시점까지 반영 확인 발언이 없다.', counter: [q('L00111', '그럼 홍보물에 장소랑 시간 넣고 인쇄 맡기겠습니다.')] });

set('c4-T06', { decision: 'B 채택', why: 'B: 담당자·기준 시점 없는 무기한 보류인데 해결·결정으로 분류돼 conclusion의 "보류 상태"와 모순. 채택.', status: '진행 중', conclusion: '[메인] 사전 예약 제안을 인원 확정 후로 미뤘을 뿐 담당자·기준 시점·예약 여부는 미정이다.' });

// ── 2. 청크 간 연결 (B는 자기 청크 밖을 보지 않으므로 메인이 원문으로 판단) ──
const X = 'B는 청크 밖을 보지 않으므로 메인이 이후 청크 원문으로 판단';
set('c1-T01', { decision: '청크 간 갱신(c2-T01)', why: X + ': 다음 날 가상센터 내부 행사로 예약이 취소됨(L00037). 완료 상태가 뒤집혔다.', status: '해결·결정', conclusion: '[메인/청크 간] 이 예약은 다음 날 취소됐다(L00037). 장소 안건의 최신 상태는 c4-T02(소강당 승인)를 참조.', counter: [q('L00037', '10월 24일에 내부 행사가 잡혀서 대강당 예약을 취소해야 한다고 합니다.')], next_check: '없음 — c2-T01에서 취소, c4-T02에서 대체 장소 확정' });

set('c1-T02', { decision: '청크 간 갱신(c4-T01)', why: X + ': c4-T01에서 시안 2개 제출·1안 선택 완료(L00092, L00096). 담당 지정 → 해결.', status: '해결·결정', conclusion: '[메인/청크 간] 시안은 10/8 제출됐고 1안으로 선택됐다(L00092, L00096).', evidence: [q('L00092', '홍보물 시안 두 개 만들었습니다.'), q('L00096', '그럼 첫 번째로 진행하겠습니다.')], next_check: '없음 — c4-T01에서 선택 완료' });

set('c1-T04', { decision: '청크 간 갱신(c3-T03)', why: X + ': c3-T03에서 참여자D가 섭외한 강사로 확정(L00075). 강사 섭외 스레드 종결.', status: '해결·결정', conclusion: '[메인/청크 간] 작년 강사는 선약으로 불가(L00052), 참여자D 지인이 10/24 가능해 확정됐다(L00075).', evidence: [q('L00075', '그럼 그분으로 확정하겠습니다.')], next_check: '강사 성함이 원문에 한 번도 나오지 않음(B c3 지적) — 사람 확인 필요' });

set('c1-T05', { decision: '청크 간 갱신(c4-T03)', why: X + ': c4-T03에서 100장 발주 완료(L00120). 담당 지정 → 해결.', status: '해결·결정', conclusion: '[메인/청크 간] 10/9 인쇄소에 100장 발주 완료(L00120).', evidence: [q('L00120', '인쇄소에 100장 주문했습니다. 다음 주 화요일에 나온다고 합니다.')], next_check: '다음 주 화요일 수령 여부' });

set('c2-T02', { decision: '청크 간 갱신(c3-T01, c4-T02)', why: X + ': 담당자B가 소강당을 찾아 신청(c3-T01)하고 10/9 승인됨(L00109). 대체 장소 물색 종결.', status: '해결·결정', conclusion: '[메인/청크 간] 담당자B가 가상문화센터 소강당을 확인·신청했고 10/9 승인돼 10/24 13~17시로 확정됐다(L00109).', evidence: [q('L00109', '소강당 승인 났습니다. 10월 24일 오후 1시부터 5시까지 확정입니다.')], next_check: '없음' });

set('c2-T03', { decision: '청크 간 갱신(c4-T01)', why: X + ': c4-T01에서 시안 제출·선택 완료. 담당 지정 → 해결.', status: '해결·결정', conclusion: '[메인/청크 간] 10/8 시안 2개 제출, 1안 선택(L00092, L00096). 비워둔 날짜·장소는 승인 후 채워 인쇄(L00111).', evidence: [q('L00096', '그럼 첫 번째로 진행하겠습니다.')], next_check: '없음' });

set('c2-T05', { decision: '청크 간 갱신(c3-T03)', why: X + ': 참여자D가 약속대로 다음 날 결과를 보고하고 강사가 확정됨(L00070, L00075).', status: '해결·결정', conclusion: '[메인/청크 간] 참여자D가 10/7에 결과를 보고했고 강사가 확정됐다(L00070, L00075). 기한 내 이행.', evidence: [q('L00070', '강사 건 말씀드립니다. 어제 연락드렸는데 10월 24일 가능하다고 하십니다.')], next_check: '없음' });

set('c3-T01', { decision: '청크 간 갱신(c4-T02)', why: X + ': c4-T02에서 승인 확인(L00109). 진행 중 → 해결.', status: '해결·결정', conclusion: '[메인/청크 간] 10/9 승인돼 10/24 오후 1~5시로 확정(L00109).', evidence: [q('L00109', '소강당 승인 났습니다.')], next_check: '없음' });

set('c3-T04', { decision: '청크 간 갱신(c4-T04)', why: X + ': c4-T04에서 참여자D가 전달하고 담당자C가 수령 확인(L00098~L00099). 전달 자체는 이행됨.', status: '해결·결정', conclusion: '[메인/청크 간] 10/8 전달 완료·수령 확인(L00098, L00099). 다만 홍보물 반영 여부는 c4-T04에서 미확인으로 남는다.', evidence: [q('L00098', '강사분 소개 정리해서 담당자C님께 보냈습니다.'), q('L00099', '받았습니다. 반영하겠습니다.')], next_check: '홍보물 반영 여부는 c4-T04 참조' });

set('c2-T04', { decision: '청크 간 갱신(c4-T07)', why: X + ': c4-T07에서 장소 확정 후 입금 마감 10/17 유지가 재확인됨(L00115). 잠정 → 확정.', certainty: '확정', conclusion: '[메인/청크 간] 장소가 확정된 뒤 10/9에 입금 마감 10/17 유지가 재확인됐다(L00115). 다만 c1-T03의 요일 불일치는 그대로 남는다.', evidence: [q('L00115', '장소가 확정됐으니 입금 마감도 다시 확인합시다. 10월 17일 금요일 그대로 갑니다.')] });

set('c3-T05', { decision: '청크 간 확인(미해소)', why: X + ': 간식 담당자·예산은 c4에서도 언급되지 않음. 진행 중 유지.', unknowns: ['c4까지 간식 담당자·예산 언급 없음'] });

set('c1-T03', { decision: '청크 간 갱신(c4-T08)', why: X + ': c4-T08에서 참가비 1만 원 유지가 재확인됨(L00118). 금액은 확정, 마감 요일 불일치만 미결.', conclusion: '[메인/청크 간] 10/9 참가비 1만 원 유지 재확인(L00118).', evidence: [q('L00118', '간식이랑 자료집 생각하면 1만 원도 빠듯합니다. 그대로 가죠.')] });

// ── 3. B unknowns/assumptions 병합 + 리뷰 메타 ──
for (const t of topics) {
  const r = reviews[t.id];
  if (!r) continue;
  for (const u of r.unknowns || []) if (!t.unknowns.includes(u)) t.unknowns.push(u);
  for (const a of r.assumptions || []) if (!t.assumptions.includes(a)) t.assumptions.push(a);
  t.review = { verdict: r.verdict, reason: r.reason, proposed_change: r.proposed_change ?? null };
  if (!log.some(l => l.topic_id === t.id)) log.push({ topic_id: t.id, decision: '채택', reason: 'B accept, 메인 이견 없음. B의 unknowns/assumptions만 병합.', changes: [] });
}

// ── 4. 스레드 ──
const threads = {
  '행사 장소': ['c1-T01', 'c2-T01', 'c2-T02', 'c3-T01', 'c3-T02', 'c4-T02'],
  '홍보물·인쇄': ['c1-T02', 'c1-T05', 'c2-T03', 'c2-T06', 'c4-T01', 'c4-T03', 'c4-T04', 'c4-T11'],
  '강사 섭외': ['c1-T04', 'c2-T05', 'c3-T03', 'c3-T04'],
  '참가비·신청·정원': ['c1-T03', 'c2-T04', 'c3-T06', 'c4-T07', 'c4-T08', 'c4-T10'],
  '행사 운영(간식·순서·뒤풀이·사진)': ['c3-T05', 'c4-T05', 'c4-T06', 'c4-T12'],
  '비용 정산': ['c4-T09'],
};
const threadOf = {}; for (const [k, ids] of Object.entries(threads)) for (const id of ids) threadOf[id] = k;
for (const t of topics) { t.chunk = t.id.split('-')[0]; t.thread = threadOf[t.id] || '미분류'; }

const statuses = ['해결·결정', '담당 지정', '진행 중', '흐지부지', '정보공유', null];
for (const t of topics) {
  if (!statuses.includes(t.status)) throw new Error('bad status ' + t.id);
  if (t.status === null && t.certainty !== '판단 보류') throw new Error('null must be held ' + t.id);
}
const cnt = k => topics.reduce((m, t) => (m[t[k] ?? 'null'] = (m[t[k] ?? 'null'] || 0) + 1, m), {});
const vcnt = Object.values(reviews).reduce((m, r) => (m[r.verdict] = (m[r.verdict] || 0) + 1, m), {});

const final = {
  run: 'runs/test-03',
  source: 'examples/synthetic-chat-long.txt (합성 데이터, 실제 인물·기관 아님)',
  indexed_source: 'runs/test-03/work/indexed.txt',
  chunks: 4,
  tools: {
    chunking: 'openai/tiktoken — scripts/chunk_by_tokens.py',
    citation_check: 'rapidfuzz/RapidFuzz — scripts/check_citations.py',
    schema_check: 'ajv-validator/ajv — scripts/validate_schema.mjs + schemas/*.json',
  },
  topics,
  threads,
  summary: `총 ${topics.length}개 안건. 상태: ${JSON.stringify(cnt('status'))}. 확신: ${JSON.stringify(cnt('certainty'))}. 검토 verdict: ${JSON.stringify(vcnt)}, 누락 안건 0. 메인이 청크 간 연결로 갱신한 안건 ${log.filter(l => l.decision.includes('청크 간')).length}건. 대화 종료(10/9) 시점 최신 상태: 장소는 가상문화센터 소강당 10/24 13~17시 확정, 강사 확정(성함 미기재), 홍보물 1안 100장 발주 완료, 참가비 1만 원·입금 마감 10/17 유지. 미결은 간식 담당자·예산, 사진 촬영 담당자, 뒤풀이 장소, 강사 소개의 홍보물 반영 여부, 그리고 입금 마감의 날짜·요일 표기 불일치다.`,
};
fs.writeFileSync(path.join(here, '04-final.json'), JSON.stringify(final, null, 2));
fs.writeFileSync(path.join(here, '03-coordination-log.json'), JSON.stringify({ generated_at: new Date().toISOString(), schema_note: SCHEMA_NOTE, decisions: log }, null, 2));
console.log('topics', topics.length, '| log', log.length, '| status', cnt('status'), '| verdict', vcnt);
