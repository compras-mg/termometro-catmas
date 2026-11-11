import {resumo,selecionar,grupos,validar,csv} from './avaliacao-metricas.mjs?v=1';
const $=id=>document.getElementById(id),names={item_material:'Item de material',item_servico:'Item de serviço',material:'Material',servico:'Serviço',alteracao:'Solicitação de alteração'};
const labels={no_prazo:'1 · Resposta no prazo',fora_prazo:'0 · Resposta fora do prazo',aberto_atrasado:'0 · Prazo consumido, sem resposta',aberto_indeterminado:'Pendente',retirado_sem_resposta:'Excluído · retirada',resposta_inferida_na_geracao:'Excluído · resposta inferida',revisao_necessaria:'Excluído · revisar eventos',ausente_na_extracao:'Excluído · ausente na extração'};
const fmt=(n,d=1)=>n==null?'—':new Intl.NumberFormat('pt-BR',{minimumFractionDigits:d,maximumFractionDigits:d}).format(n),pct=n=>n==null?'—':fmt(n*100)+'%',date=s=>s?s.slice(0,10).split('-').reverse().join('/')+' '+s.slice(11,16):'—';
let dataset,selection=[],page=0;
function row(root,values){const tr=document.createElement('tr');values.forEach(value=>{const td=document.createElement('td');td.textContent=String(value??'—');tr.append(td)});root.append(tr);return tr;}
function empty(root,n,message='Nenhum ciclo nesta seleção.'){const tr=row(root,[message]);tr.firstChild.colSpan=n;tr.className='empty-row';}
function summaryRows(id,items,label=k=>k){const root=$(id);root.replaceChildren();items.forEach(([key,s])=>row(root,[label(key),s.n,s.pendentes,fmt(s.brier,4),pct(s.previsto),pct(s.realizado)]));if(!items.length)empty(root,6);}
function render(){
 const start=$('evalFrom').value,end=$('evalTo').value;
 const invalid=start&&end&&start>end;$('filterError').textContent=invalid?'A data inicial deve ser anterior ou igual à final.':'';
 const origin=$('evalOrigin').value;
 $('originNote').textContent=origin==='retrospectiva'?'Retrospectiva: previsões calculadas agora com os atributos reconstruídos na entrada. Não são previsões registradas naquele momento. Somente entradas após treino e calibração do modelo.':'Previsões congeladas na primeira publicação sem resultado observado. Podem ter sido registradas depois da entrada; o atraso da extração impede certificar antecedência em relação à resposta real.';
 selection=dataset&&!invalid?selecionar(dataset.registros,{origem:origin,tipo:$('evalType').value,inicio:start,fim:end}):[];
 const s=resumo(selection);$('metricBrier').textContent=fmt(s.brier,4);$('metricExpected').textContent=pct(s.previsto);$('metricActual').textContent=pct(s.realizado);
 $('metricGap').textContent=s.n?fmt((s.previsto-s.realizado)*100)+' p.p.':'—';$('metricCount').textContent=fmt(s.n,0);
 $('metricCoverage').textContent=fmt(s.pendentes,0)+' pendentes · '+fmt(s.excluidos,0)+' excluídos · '+fmt(s.total,0)+' ciclos';
 summaryRows('typeRows',grupos(selection,r=>r.tipo),(k)=>names[k]||k);
 summaryRows('monthRows',grupos(selection,r=>r.entrada.slice(0,7)).sort((a,b)=>b[0].localeCompare(a[0])),k=>k.slice(5)+'/'+k.slice(0,4));
 const root=$('calibrationRows');root.replaceChildren();
 const bins=grupos(selection.filter(r=>r.realizado!==null),r=>Math.min(9,Math.floor(r.probabilidade*10))).sort((a,b)=>a[0]-b[0]);
 for(const [b,v] of bins)row(root,[b*10+'% a '+(b+1)*10+'%'+(b===9?' (inclui 100%)':' (limite superior excluído)'),v.n,pct(v.previsto),pct(v.realizado),fmt((v.previsto-v.realizado)*100)+' p.p.']);
 if(!bins.length)empty(root,5,'Ainda não há resultados avaliáveis nesta seleção.');
 $('exportEvaluation').disabled=!selection.length;page=0;renderRecords();
}
function renderRecords(){
 const q=$('evalSearch').value.trim().replace(/^0+(?=\d)/,'');
 let rows=selection.filter(r=>!q||r.numero.replace(/^0+(?=\d)/,'')===q);
 rows.sort($('evalSort').value==='error'?(a,b)=>(b.erro_brier??-1)-(a.erro_brier??-1)||b.entrada.localeCompare(a.entrada):(a,b)=>b.entrada.localeCompare(a.entrada)||a.id.localeCompare(b.id));
 const pages=Math.max(1,Math.ceil(rows.length/25));page=Math.min(page,pages-1);
 const root=$('evaluationRows');root.replaceChildren();
 rows.slice(page*25,page*25+25).forEach(r=>{
  const tr=row(root,[r.numero+' / '+r.ciclo,names[r.tipo]||r.tipo,date(r.entrada),pct(r.probabilidade),labels[r.resultado]||'Excluído',fmt(r.erro_brier,4),date(r.resposta_em),r.prazo+' / '+fmt(r.dias_consumidos,2),date(r.registrada_em)+' UTC · '+r.modelo.slice(0,10)]);
  if(r.atributos_revisados||r.resultado_revisado){const note=document.createElement('small');note.className='result-note';note.textContent='Origem revisada; previsão original preservada.';tr.lastChild.append(note);}
 });
 if(!rows.length)empty(root,9);
 $('evalPage').textContent=rows.length?`${page+1} de ${pages} · ${fmt(rows.length,0)} ciclos`:'Nenhum ciclo';$('evalPrev').disabled=page===0;$('evalNext').disabled=page>=pages-1;
}
for(const id of ['evalOrigin','evalType','evalFrom','evalTo'])$(id).addEventListener('change',render);
for(const id of ['evalSearch','evalSort'])$(id).addEventListener(id==='evalSearch'?'input':'change',()=>{page=0;renderRecords()});
$('evalPrev').addEventListener('click',()=>{page--;renderRecords()});$('evalNext').addEventListener('click',()=>{page++;renderRecords()});
$('exportEvaluation').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([csv(selection)],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='catmas-previsto-realizado.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
render();
fetch('./acompanhamento.json.gz',{cache:'no-store'}).then(async response=>{
 if(response.status===404){$('monitorStatus').textContent='Acompanhamento preparado. A primeira carga será disponibilizada após instalar e executar a nova rotina de atualização.';return;}
 if(!response.ok)throw Error('Carga indisponível');
 dataset=validar(JSON.parse(await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).text()));
 $('evalFrom').value=dataset.inicio_avaliacao;$('evalTo').value=dataset.referencia.slice(0,10);
 $('monitorStatus').textContent='Resultados até '+date(dataset.referencia)+' · '+fmt(dataset.registros.length,0)+' ciclos registrados · fonte não é tempo real.';
 render();
}).catch(()=>{$('monitorStatus').textContent='Não foi possível carregar uma apuração válida. Nenhum indicador foi calculado. Recarregue a página.';dataset=null;render()});
