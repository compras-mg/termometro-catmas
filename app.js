'use strict';
const $=id=>document.getElementById(id),names={item_material:'Item de material',item_servico:'Item de serviço',material:'Material',servico:'Serviço',alteracao:'Solicitação de alteração'};
const num=x=>new Intl.NumberFormat('pt-BR',{maximumFractionDigits:1}).format(x);
let data;
function indicator(){const s=data.tipos[$('type').value],p=Math.round(s.probabilidade_no_prazo*100);$('prob').textContent=p+'%';$('late').textContent=(100-p)+'%';$('deadline').textContent=s.prazo+' dias úteis';$('needle').style.transform=`rotate(${p*1.8-90}deg)`;$('gaugeTitle').textContent=`Estimativa experimental: ${p}% no prazo e ${100-p}% de atraso`;$('queue').textContent=s.fila;$('allQueue').textContent=data.total_fila;$('capacity').textContent=num(s.capacidade)+' / dia útil';$('loadDays').textContent=s.dias_carga===null?'Indisponível':num(s.dias_carga);const level=s.dias_carga===null?3:s.dias_carga<=s.prazo/2?0:s.dias_carga<=s.prazo?1:2;$('flag').style.color=['#4e8b76','#ac7c17','#b34e47','#77827b'][level];$('loadLabel').textContent=['Carga baixa','Atenção à carga','Carga elevada','Sem estimativa'][level];$('loadDesc').textContent=['A fila equivale a até metade do prazo de referência, no ritmo recente.','A fila equivale a mais de metade do prazo, no ritmo recente.','A fila supera o prazo de referência, no ritmo recente.','Não há respostas suficientes na janela para calcular a carga.'][level];}
function chart(){
 const months=['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez'];
 const keys=Object.keys(data.mensal).filter(k=>k>='2023-01'&&k<=data.referencia.slice(0,7)).sort();
 const rows=[];
 if(keys.length){let [year,month]=keys[0].split('-').map(Number);const last=keys[keys.length-1];while(true){const key=year+'-'+String(month).padStart(2,'0');if(key>last)break;const v=data.mensal[key];rows.push({key,m:months[month-1]+'/'+year,a:v?.primeiros_envios||0,b:v?.reenvios||0,available:!!v});if(++month===13){month=1;year++}}}
 const max=Math.max(1,...rows.map(r=>r.a+r.b));
 $('chart').replaceChildren();
 const table=document.createElement('table');
 table.innerHTML='<thead><tr><th>Mês</th><th>Primeiros envios</th><th>Reenvios</th><th>Total</th></tr></thead>';
 const tbody=document.createElement('tbody');
 rows.forEach(r=>{
  const col=document.createElement('div'),total=r.a+r.b,partial=r.key===data.referencia.slice(0,7);
  col.className='barcol';col.title=r.available?r.m+': '+r.a+' primeiros envios e '+r.b+' reenvios'+(partial?' (mês incompleto)':''):r.m+': sem dados';
  col.innerHTML='<span class="count">'+(r.available?num(total):'—')+'</span><div class="bar" style="height:'+total/max*190+'px"><div class="again" style="height:'+(total?r.b/total*100:0)+'%"></div><div class="first" style="height:'+(total?r.a/total*100:0)+'%"></div></div><span class="month">'+r.m+(partial?'*':'')+'</span>';
  $('chart').append(col);
  const tr=document.createElement('tr');
  [r.m+(partial?'*':''),r.available?r.a:'—',r.available?r.b:'—',r.available?total:'—'].forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td)});
  tbody.append(tr);
 });
 table.append(tbody);$('table').replaceChildren(table);
 requestAnimationFrame(()=>{$('chartScroll').scrollLeft=$('chartScroll').scrollWidth});
}
function lookup(e){e.preventDefault();let code=$('number').value.trim().replace(/^0+(?=\d)/,'');const rows=data.consulta.filter(r=>r.numero.replace(/^0+(?=\d)/,'')===code);$('answer').replaceChildren();if(!rows.length){$('answer').textContent='Não localizado nesta extração. Confira o número. Rascunhos, demandas recentes ou ainda não sincronizadas podem não aparecer.';return}rows.forEach(r=>{const box=document.createElement('article');box.className='result';let h=document.createElement('h3');h.textContent=`${names[r.tipo]} · ${r.numero}`;box.append(h);let p=document.createElement('p');p.textContent='Situação no cadastro: '+r.situacao;box.append(p);p=document.createElement('p');p.textContent=r.divergencia?'O cadastro e o histórico divergem. A quantidade de demandas anteriores não está disponível com segurança para esta proposta.':r.fila?`${r.anteriores} demandas na fila entraram antes deste ciclo, sendo ${r.anteriores_tipo} do mesmo tipo.`:r.pausado?'Fora da fila enquanto está em edição pelo demandante.':'Este ciclo não está aguardando resposta da equipe.';box.append(p);p=document.createElement('p');const d=r.entrada.slice(0,10).split('-').reverse().join('/');p.textContent=`Ciclo ${r.ciclo} · Entrada em ${d}. Contagem reconstruída pelo histórico; o cadastro pode divergir.`;p.className='small';box.append(p);$('answer').append(box)})}
fetch('./dados.json.gz').then(async r=>{if(!r.ok)throw Error('Dados indisponíveis');const stream=r.body.pipeThrough(new DecompressionStream('gzip'));return JSON.parse(await new Response(stream).text())}).then(d=>{data=d;const [day,hour]=d.referencia.split('T');$('reference').textContent='Último evento observado: '+day.split('-').reverse().join('/')+' às '+hour.slice(0,5)+' · não é tempo real';indicator();chart();$('type').addEventListener('change',indicator);$('form').addEventListener('submit',lookup)}).catch(()=>{$('reference').textContent='Não foi possível carregar os dados. Recarregue a página.';$('form').addEventListener('submit',e=>e.preventDefault());$('type').disabled=true;});
