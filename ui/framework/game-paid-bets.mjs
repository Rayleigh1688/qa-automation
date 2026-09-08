import {requireBusinessResponse} from './business-response.mjs';

// Reuse the live UI session in memory: a separate password login invalidates it.
export function liveBetReader(page, baseURL) {
  let headers;
  page.on('request',request=>{
    if(new URL(request.url()).origin===new URL(baseURL).origin && request.headers().t) headers=request.headers();
  });
  return async () => {
    if(!headers?.t || !headers.d) throw new Error('No authenticated UI request observed for bet reconciliation');
    const rows=[];
    for(let pageNumber=1;pageNumber<=10;pageNumber++) {
      const response=await page.context().request.get(`/member/game/bet/list?page_size=100&time_flag=0&page=${pageNumber}`,{headers:{t:headers.t,d:headers.d,lang:headers.lang||'en_US'}});
      const {data}=await requireBusinessResponse(response);
      if(data?.t===0 && data.d===null) return [];
      if(!Array.isArray(data?.d)) throw new Error('Bet history shape changed');
      rows.push(...data.d);
      if(rows.length>=Number(data.t)) return rows;
      if(!data.d.length) break;
    }
    throw new Error('Bet history pagination incomplete');
  };
}
export function verifyPaidDelta(rows, baseline, expected, amount) {
  const ids=new Set(baseline.map(row=>String(row.id)));
  const delta=rows.filter(row=>!ids.has(String(row.id)));
  const paid=delta.filter(row=>Number(row.bet_amount)>0);
  if(paid.length>expected || paid.some(row=>Number(row.bet_amount)!==amount)) throw new Error('Unexpected paid bet count or amount; stop without retry');
  return {accepted:paid.length===expected && delta.every(row=>row.status===1),paidBetRecords:paid.length,zeroBetRecords:delta.length-paid.length};
}
