export function resumo(rows){
 const scored=rows.filter(r=>r.realizado===0||r.realizado===1),n=scored.length;
 const mean=fn=>n?scored.reduce((s,r)=>s+fn(r),0)/n:null;
 return {total:rows.length,n,pendentes:rows.filter(r=>r.resultado==='aberto_indeterminado').length,
  excluidos:rows.filter(r=>r.realizado==null&&r.resultado!=='aberto_indeterminado').length,
  brier:mean(r=>(r.probabilidade-r.realizado)**2),previsto:mean(r=>r.probabilidade),realizado:mean(r=>r.realizado)};
}
export function selecionar(rows,{origem,tipo='',inicio='',fim=''}){
 return rows.filter(r=>r.origem===origem&&(!tipo||r.tipo===tipo)&&(!inicio||r.entrada.slice(0,10)>=inicio)&&(!fim||r.entrada.slice(0,10)<=fim));
}
export function grupos(rows,key){const map=new Map();for(const r of rows){const k=key(r);if(!map.has(k))map.set(k,[]);map.get(k).push(r)}return [...map].map(([k,v])=>[k,resumo(v)]);}
export function validar(d){
 if(d?.schema_version!==1||!Array.isArray(d.registros)||typeof d.referencia!=='string')throw Error('Formato inválido');
 const ids=new Set();for(const r of d.registros){
  if(ids.has(r.id)||typeof r.probabilidade!=='number'||!Number.isFinite(r.probabilidade)||r.probabilidade<0||r.probabilidade>1||!['retrospectiva','registrada_sem_resultado'].includes(r.origem))throw Error('Previsão inválida');
  ids.add(r.id);const y=({no_prazo:1,fora_prazo:0,aberto_atrasado:0})[r.resultado]??null;
  if(r.realizado!==y||(y===null?r.erro_brier!==null:typeof r.erro_brier!=='number'||!Number.isFinite(r.erro_brier)||Math.abs(r.erro_brier-(r.probabilidade-y)**2)>1e-10))throw Error('Apuração inválida');
 }return d;
}
export function csv(rows){
 const fields=['numero','tipo','ciclo','entrada','prazo','probabilidade','realizado','erro_brier','resultado','resposta_em','dias_consumidos','origem','registrada_em','modelo','atributos_revisados','resultado_revisado'];
 const cell=v=>'"'+String(v??'').replace(/^[=+@\-]/,"'$&").replaceAll('"','""')+'"';
 return '\uFEFF'+[fields,...rows.map(r=>fields.map(k=>r[k]))].map(row=>row.map(cell).join(';')).join('\r\n');
}
