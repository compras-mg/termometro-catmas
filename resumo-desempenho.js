import {validar,resumo} from './avaliacao-metricas.mjs?v=2';
const number=document.getElementById('performance-number'),context=document.getElementById('performance-context');
const fmt=n=>new Intl.NumberFormat('pt-BR',{maximumFractionDigits:1}).format(n);
fetch('./acompanhamento.json.gz',{cache:'no-store'}).then(async r=>{
 if(!r.ok)throw Error('Dados indisponíveis');
 const data=validar(JSON.parse(await new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).text()));
 const today=new Intl.DateTimeFormat('sv-SE',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 const d=new Date(today+'T12:00:00Z');d.setUTCDate(d.getUTCDate()-29);const from=d.toISOString().slice(0,10);
 const rows=data.registros.filter(r=>r.entrada.slice(0,10)>=from&&r.entrada.slice(0,10)<=today),s=resumo(rows);
 const date=s=>s.slice(0,10).split('-').reverse().join('/');
 if(!s.n){number.textContent='Ainda não há resultados avaliáveis para estes 30 dias.';context.textContent=fmt(s.pendentes)+' ciclos pendentes de avaliação.';return;}
 for(const [key,value] of [['actual',s.realizado],['expected',s.previsto]]){
  document.getElementById('performance-'+key).textContent=fmt(value*100)+'%';
  document.getElementById('performance-'+key+'-bar').style.width=(value*100)+'%';
 }
 number.textContent=fmt(Math.round(s.realizado*s.n))+' de '+fmt(s.n)+' ciclos atendidos no prazo nos últimos 30 dias.';
 context.textContent='Entradas de '+date(from)+' a '+date(today)+'. Dados até '+date(data.referencia)+'. A quantidade estimada é de '+fmt(s.previsto*s.n)+' atendimentos no prazo. Inclui previsões reconstruídas retrospectivamente. '+fmt(s.pendentes)+' pendentes e '+fmt(s.excluidos)+' excluídos ficam fora da comparação. Cada reenvio após uma resposta inicia outro ciclo.';
}).catch(()=>{number.textContent='Resumo temporariamente indisponível.';context.textContent='Consulte o detalhamento na página de desempenho.';});
