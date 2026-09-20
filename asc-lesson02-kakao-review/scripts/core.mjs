export function numberLines(text) {
  return text.split('\n').map((line,i) => 'L'+String(i+1).padStart(3,'0')+' | '+line).join('\n');
}
export function validate(analyst, reviewer, final, source) {
  const errors=[]; let citations=0;
  const lines=source.split('\n');
  function walk(value) {
    if (!value || typeof value !== 'object') return;
    if ('line' in value || 'quote' in value) {
      citations++;
      if (!/^L\d{3,}$/.test(value.line || '')) errors.push('invalid line '+value.line);
      const row=lines[Number(String(value.line).replace('L',''))-1];
      if (!value.quote || !row || !row.includes(value.quote)) errors.push('quote mismatch '+value.line);
    }
    for (const child of Object.values(value)) if (typeof child==='object') walk(child);
  }
  const statuses=['해결·결정','담당 지정','진행 중','흐지부지','정보공유',null];
  for (const result of [analyst,final]) {
    if (!Array.isArray(result.topics) || !result.topics.length) errors.push('topics missing');
    const ids=new Set();
    for (const t of result.topics || []) {
      if (!t.id || ids.has(t.id)) errors.push('duplicate/missing topic id'); ids.add(t.id);
      for (const key of ['title','status','certainty','conclusion','evidence','assumptions','counter_evidence','unknowns','owner','deadline','next_check']) if (!(key in t)) errors.push('missing '+key+' '+t.id);
      if (!statuses.includes(t.status)) errors.push('invalid status '+t.id);
      if (!['확정','판단 보류'].includes(t.certainty)) errors.push('invalid certainty '+t.id);
      if (t.status===null && t.certainty!=='판단 보류') errors.push('null status must be held '+t.id);
      if (!Array.isArray(t.evidence) || !t.evidence.length) errors.push('evidence missing '+t.id);
      for (const k of ['assumptions','counter_evidence','unknowns']) if (!Array.isArray(t[k])) errors.push('invalid array '+k);
    }
  }
  if (!Array.isArray(reviewer.reviews)) errors.push('reviews missing');
  for (const t of analyst.topics || []) if (!(reviewer.reviews || []).some(r=>r.topic_id===t.id)) errors.push('unreviewed '+t.id);
  for (const r of reviewer.reviews || []) if (!['accept','revise','hold'].includes(r.verdict)) errors.push('invalid review '+r.topic_id);
  walk(analyst); walk(reviewer); walk(final);
  return {passed:errors.length===0,errors,citations_checked:citations,analyst_topics:analyst.topics?.length,reviewed_topics:reviewer.reviews?.length,final_topics:final.topics?.length};
}
export function render(final) {
  let out='# カ카오톡 안건 판단·검증 결과\n\n입력: examples/synthetic-chat.txt (합성 데이터). 근거 ID: examples/indexed-chat.txt.\n\n'+final.summary+'\n\n';
  for (const t of final.topics) {
    out+='## '+t.title+'\n\n- 상태: '+(t.status ?? '판단 보류')+'\n- 판단: '+t.conclusion+'\n- 담당: '+(t.owner ?? '미확정/해당 없음')+'\n- 기한: '+(t.deadline ?? '미확정/해당 없음')+'\n- 근거: '+t.evidence.map(e=>e.line+' “'+e.quote+'”').join('; ')+'\n- 모르는 점: '+(t.unknowns.join('; ') || '없음')+'\n- 다음 확인: '+t.next_check+'\n\n';
  }
  return out.replace('カ카오톡','카카오톡');
}
