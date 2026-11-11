import {validar,resumo} from './avaliacao-metricas.mjs?v=2';
const number=document.getElementById('performance-number'),context=document.getElementById('performance-context');
const fmt=n=>new Intl.NumberFormat('pt-BR',{maximumFractionDigits:1}).format(n);
fetch('./acompanhamento.json.gz',{cache:'no-store'}).then(async r=>{
 if(!r.ok)throw Error('Dados indisponíveis');
 const data=validar(JSON.parse(await new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).text()));
 const today=new Intl.DateTimeFormat('sv-SE',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
 const d=new Date(today.slice(0,7)+'-01T12:00:00Z');d.setUTCMonth(d.getUTCMonth()-1);const month=d.toISOString().slice(0,7);
 const rows=data.registros.filter(r=>r.origem==='retrospectiva'&&r.entrada.slice(0,7)===month),s=resumo(rows);
 const label=new Intl.DateTimeFormat('pt-BR',{month:'long',year:'numeric',timeZone:'UTC'}).format(d);
 document.getElementById('performance-title').textContent='Atendimento em '+label;
 if(!s.n){number.textContent='Ainda não há resultados avaliáveis para este mês.';context.textContent=fmt(s.pendentes)+' ciclos pendentes de avaliação.';return;}
 number.textContent=fmt(s.realizado*100)+'% atendidos no prazo · '+fmt(s.previsto*100)+'% previstos';
 context.textContent=fmt(Math.round(s.realizado*s.n))+' de '+fmt(s.n)+' ciclos atendidos no prazo; '+fmt(s.previsto*s.n)+' esperados. Avaliação retrospectiva pelo mês de entrada. '+fmt(s.pendentes)+' pendentes e '+fmt(s.excluidos)+' excluídos ficam fora da comparação.';
}).catch(()=>{number.textContent='Resumo temporariamente indisponível.';context.textContent='Consulte o detalhamento no painel Previsto × realizado.';});
