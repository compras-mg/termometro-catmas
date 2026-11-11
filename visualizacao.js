(()=>{
 const all=document.getElementById('viewAll'),single=document.getElementById('viewSingle'),choice=document.getElementById('kindChoice'),select=document.getElementById('gaugeKind'),dashboard=document.getElementById('gaugeDashboard'),cards=[...dashboard.querySelectorAll('[data-kind]')];
 const read=k=>{try{return localStorage.getItem(k)}catch{return null}},write=(k,v)=>{try{localStorage.setItem(k,v)}catch{}};
 const saved=read('catmas.gauge.view');
 let mode=['all','single'].includes(saved)?saved:matchMedia('(max-width: 799px)').matches?'single':'all';
 const kind=read('catmas.gauge.kind');if([...select.options].some(o=>o.value===kind))select.value=kind;
 function render(){const one=mode==='single';all.setAttribute('aria-pressed',String(!one));single.setAttribute('aria-pressed',String(one));choice.hidden=!one;dashboard.classList.toggle('single-view',one);cards.forEach(c=>{c.hidden=one&&c.dataset.kind!==select.value})}
 all.addEventListener('click',()=>{mode='all';write('catmas.gauge.view',mode);render()});
 single.addEventListener('click',()=>{mode='single';write('catmas.gauge.view',mode);render()});
 select.addEventListener('change',()=>{write('catmas.gauge.kind',select.value);render()});render();
})();