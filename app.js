'use strict';
const $=id=>document.getElementById(id),names={item_material:'Item de material',item_servico:'Item de serviço',material:'Material',servico:'Serviço',alteracao:'Solicitação de alteração'};
const num=x=>new Intl.NumberFormat('pt-BR',{maximumFractionDigits:1}).format(x);
let data;
function indicator(){
 $('allQueue').textContent=num(data.total_fila);
 document.querySelectorAll('.gaugecard[data-kind]').forEach(card=>{
  const kind=card.dataset.kind,s=data.tipos[kind],field=name=>card.querySelector('[data-field="'+name+'"]');
  if(!s){field('loadLabel').textContent='Dados indisponíveis';return;}
  const available=Number.isFinite(s.probabilidade_no_prazo),p=available?Math.round(s.probabilidade_no_prazo*100):null;
  field('prob').textContent=available?p+'%':'—';
  field('deadline').textContent=s.prazo+' dias úteis';
  field('needle').setAttribute('visibility',available?'visible':'hidden');
  if(available)field('needle').style.transform='rotate('+(p*1.8-90)+'deg)';
  card.querySelector('svg').setAttribute('aria-label',names[kind]+(available?': estimativa experimental de '+p+'% de resposta em até '+s.prazo+' dias úteis':': probabilidade indisponível'));
  field('queue').textContent=num(s.fila);
  field('capacity').textContent=Number.isFinite(s.capacidade)?num(s.capacidade):'Indisponível';
  field('loadDays').textContent=Number.isFinite(s.dias_carga)?num(s.dias_carga):'Indisponível';
  const level=!Number.isFinite(s.dias_carga)?3:s.dias_carga<=s.prazo/2?0:s.dias_carga<=s.prazo?1:2;
  field('loadStatus').dataset.level=level;
  field('loadLabel').textContent=['Carga baixa','Atenção à carga','Carga elevada','Sem estimativa'][level];
  field('loadDesc').textContent=['Até metade do prazo de referência, no ritmo recente.','Mais de metade do prazo de referência, no ritmo recente.','Acima do prazo de referência, no ritmo recente.','Sem respostas suficientes para estimar a carga.'][level];
 });
}
function lookup(e){e.preventDefault();let code=$('number').value.trim().replace(/^0+(?=\d)/,'');const rows=data.consulta.filter(r=>r.numero.replace(/^0+(?=\d)/,'')===code);$('answer').replaceChildren();if(!rows.length){$('answer').textContent='Não localizado nesta extração. Confira o número. Rascunhos, demandas recentes ou ainda não sincronizadas podem não aparecer.';return}rows.forEach(r=>{const box=document.createElement('article');box.className='result';let h=document.createElement('h3');h.textContent=`${names[r.tipo]} · ${r.numero}`;box.append(h);let p=document.createElement('p');p.textContent='Situação no cadastro: '+r.situacao;box.append(p);p=document.createElement('p');p.textContent=r.divergencia?'O cadastro e o histórico divergem. A quantidade de demandas anteriores não está disponível com segurança para esta proposta.':r.fila?`${r.anteriores} demandas na fila entraram antes deste ciclo, sendo ${r.anteriores_tipo} do mesmo tipo.`:r.pausado?'Fora da fila enquanto está em edição pelo demandante.':'Este ciclo não está aguardando resposta da equipe.';box.append(p);p=document.createElement('p');const d=r.entrada.slice(0,10).split('-').reverse().join('/');p.textContent=`Ciclo ${r.ciclo} · Entrada em ${d}. Contagem reconstruída pelo histórico; o cadastro pode divergir.`;p.className='small';box.append(p);$('answer').append(box)})}
fetch('./dados.json.gz').then(async r=>{if(!r.ok)throw Error('Dados indisponíveis');const stream=r.body.pipeThrough(new DecompressionStream('gzip'));return JSON.parse(await new Response(stream).text())}).then(d=>{data=d;const [day,hour]=d.referencia.split('T');$('reference').textContent='Último evento observado: '+day.split('-').reverse().join('/')+' às '+hour.slice(0,5)+' · não é tempo real';indicator();$('gaugeDashboard').setAttribute('aria-busy','false');$('form').querySelector('button').disabled=false;$('form').addEventListener('submit',lookup)}).catch(()=>{$('reference').textContent='Não foi possível carregar os dados. Recarregue a página.';$('gaugeDashboard').setAttribute('aria-busy','false');$('answer').textContent='Consulta indisponível enquanto os dados não forem carregados.';$('form').addEventListener('submit',e=>e.preventDefault());document.querySelectorAll('[data-field="loadLabel"]').forEach(el=>{el.textContent='Dados indisponíveis';});});

let dailyData;
const svgNode=(name,attrs={},text)=>{const n=document.createElementNS('http://www.w3.org/2000/svg',name);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text!==undefined)n.textContent=text;return n};
function dailyCharts(){
 const period=Number($('loadPeriod').value),root=$('dailyCharts');root.replaceChildren();
 const table=document.createElement('table');table.innerHTML='<thead><tr><th>Tipo</th><th>Data</th><th>Fila</th><th>Respostas/dia útil</th><th>Dias de carga</th><th>Bandeira</th></tr></thead>';const body=document.createElement('tbody');
 Object.entries(dailyData.tipos).forEach(([kind,all])=>{
  const rows=period?all.slice(-period):all,deadline=['material','servico'].includes(kind)?5:3;
  const width=Math.max(900,(rows.length-1)*18+100),height=165,left=55,right=25,top=16,bottom=130;
  const max=Math.max(deadline*1.3,...rows.map(r=>r[3]??0))*1.05;
  const x=i=>left+i*(width-left-right)/Math.max(1,rows.length-1),y=v=>bottom-v/max*(bottom-top);
  const article=document.createElement('article');article.className='dailyrow';
  const heading=document.createElement('h3');heading.textContent=names[kind]+' · referência de '+deadline+' dias úteis';article.append(heading);
  const svg=svgNode('svg',{width,height,viewBox:'0 0 '+width+' '+height,role:'img','aria-label':'Evolução da carga: '+names[kind]});
  const defs=svgNode('defs'),gradient=svgNode('linearGradient',{id:'grad-'+kind,gradientUnits:'userSpaceOnUse',x1:0,x2:0,y1:bottom,y2:top});
  [[0,'#4e8b76'],[deadline/2/max,'#4e8b76'],[deadline/2/max,'#ac7c17'],[deadline/max,'#ac7c17'],[deadline/max,'#b34e47'],[1,'#b34e47']].forEach(([v,c])=>gradient.append(svgNode('stop',{offset:v,'stop-color':c})));defs.append(gradient);svg.append(defs);
  [0,deadline/2,deadline,max].forEach(v=>{svg.append(svgNode('line',{x1:left,x2:width-right,y1:y(v),y2:y(v),stroke:'#dce4de','stroke-dasharray':v?'4 5':'0'}));svg.append(svgNode('text',{x:left-8,y:y(v)+4,'text-anchor':'end',fill:'#65746d','font-size':10},num(v)))});
  let path='',connected=false;
  rows.forEach((r,i)=>{
   const v=r[3],state=v===null?'Sem estimativa':v<=deadline/2?'Baixa':v<=deadline?'Atenção':'Elevada';
   const date=r[0].split('-').reverse().join('/');
   if(v===null){connected=false;svg.append(svgNode('line',{x1:x(i),x2:x(i),y1:bottom-3,y2:bottom+3,stroke:'#88938d'}))}
   else {path+=(connected?'L':'M')+x(i)+','+y(v)+' ';connected=true;
    const point=svgNode('circle',{cx:x(i),cy:y(v),r:3,fill:v<=deadline/2?'#4e8b76':v<=deadline?'#ac7c17':'#b34e47'});point.append(svgNode('title',{},date+': '+num(v)+' dias de carga; '+r[1]+' demandas; '+num(r[2])+' respostas/dia útil; '+state));svg.append(point);
   }
   if(i===0||i===rows.length-1||i%7===0&&rows.length<=365||i%30===0&&rows.length>365)svg.append(svgNode('text',{x:x(i),y:153,'text-anchor':'middle',fill:'#65746d','font-size':10},r[0].slice(8)+'/'+r[0].slice(5,7)+(i===0||i===rows.length-1?'/'+r[0].slice(0,4):'')));
   const tr=document.createElement('tr');[names[kind],date,r[1],r[2]===null?'—':num(r[2]),v===null?'—':num(v),state].forEach(value=>{const td=document.createElement('td');td.textContent=value;tr.append(td)});body.append(tr);
  });
  svg.append(svgNode('path',{d:path,fill:'none',stroke:'url(#grad-'+kind+')','stroke-width':2,'pointer-events':'none'}));
  article.append(svg);const axis=svgNode('svg',{width:50,height,viewBox:'0 0 50 '+height,class:'dailyaxis','aria-hidden':'true'});[0,deadline/2,deadline,max].forEach(v=>axis.append(svgNode('text',{x:44,y:y(v)+4,'text-anchor':'end',fill:'#65746d','font-size':10},num(v))));article.append(axis);root.append(article);
 });
 table.append(body);$('dailyTable').replaceChildren(table);
 const [d,t]=dailyData.referencia.split('T');$('loadReference').textContent='Histórico até '+d.split('-').reverse().join('/')+' às '+t.slice(0,5)+' · último dia parcial';
 requestAnimationFrame(()=>{$('dailyScroll').scrollLeft=$('dailyScroll').scrollWidth});
}
if (!$('carga-historica').hidden) fetch('./carga-diaria.json').then(r=>{if(!r.ok)throw Error();return r.json()}).then(d=>{dailyData=d;dailyCharts();$('loadPeriod').addEventListener('change',dailyCharts)}).catch(()=>{$('loadReference').textContent='Não foi possível carregar o histórico diário.';$('loadPeriod').disabled=true});
