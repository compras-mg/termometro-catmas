(()=>{
 const toggle=document.getElementById('showAll'),choice=document.getElementById('kindChoice'),select=document.getElementById('gaugeKind'),dashboard=document.getElementById('gaugeDashboard'),cards=[...dashboard.querySelectorAll('[data-kind]')];
 let kind;try{kind=localStorage.getItem('catmas.gauge.kind')}catch{}
 if([...select.options].some(o=>o.value===kind))select.value=kind;
 function render(){const one=!toggle.checked;choice.hidden=!one;dashboard.classList.toggle('single-view',one);cards.forEach(c=>{c.hidden=one&&c.dataset.kind!==select.value})}
 toggle.checked=false;toggle.addEventListener('change',render);
 select.addEventListener('change',()=>{try{localStorage.setItem('catmas.gauge.kind',select.value)}catch{}render()});render();
})();