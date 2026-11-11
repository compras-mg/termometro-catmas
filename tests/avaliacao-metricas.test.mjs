import {strict as assert} from 'node:assert';
import {resumo,selecionar,grupos,validar,csv} from '../avaliacao-metricas.mjs';
const base={numero:'123',tipo:'material',entrada:'2026-01-10',origem:'retrospectiva',probabilidade:.85};
const rows=[{...base,id:'a',realizado:1,resultado:'no_prazo',erro_brier:.0225},
 {...base,id:'b',realizado:0,resultado:'fora_prazo',erro_brier:.7225},
 {...base,id:'c',realizado:null,resultado:'aberto_indeterminado',erro_brier:null}];
const s=resumo(rows);assert.equal(s.n,2);assert.equal(s.pendentes,1);assert.equal(s.realizado,.5);assert.equal(s.previsto,.85);assert.ok(Math.abs(s.brier-.3725)<1e-12);
assert.equal(resumo([rows[2]]).brier,null);assert.equal(selecionar(rows,{origem:'retrospectiva',inicio:'2026-02-01'}).length,0);
assert.equal(selecionar(rows,{origem:'registrada_sem_resultado'}).length,0);
assert.equal(grupos(rows,r=>r.tipo)[0][1].n,2);
assert.equal(validar({schema_version:1,referencia:'2026-01-20',registros:rows}).registros.length,3);
assert.throws(()=>validar({schema_version:1,referencia:'2026-01-20',registros:[{...rows[0],erro_brier:.5}]}));
assert.ok(csv(rows).includes('"0.85"'));assert.ok(csv([{...base,numero:'=1+1'}]).includes("'=1+1"));
console.log('Métricas: Brier, denominadores, pendentes, filtros, validação e CSV conferidos.');
