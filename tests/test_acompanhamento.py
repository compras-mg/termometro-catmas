import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipeline'))
import acompanhamento as a


def sample(result='aberto_indeterminado', p=.85):
    c={'ciclo_id':'P:1:1','demanda':'P:1','familia':'proposta','tipo':'item_material',
       'numero_ciclo':1,'entrada':'2026-11-01T10:00:00','evento_entrada':'10',
       'prazo_referencia_dias_uteis':3,'alertas':[]}
    f={'ciclo_id':c['ciclo_id'],'fila_total':20}
    y={'ciclo_id':c['ciclo_id'],'resultado':result,
       'alvo_no_prazo':{'no_prazo':1,'fora_prazo':0,'aberto_atrasado':0}.get(result),
       'resposta_em':'2026-11-03T10:00:00' if result in {'no_prazo','fora_prazo'} else None,
       'dias_uteis_equivalentes':1}
    return a.build_candidates([c],[{'chave':'P:1','codigo':'123'}],[f],[y],
        '2026-11-04T12:00:00',['fila_total'],lambda rows:[{'probabilidade_no_prazo':p} for _ in rows],
        '2026-11-04T15:00:00+00:00')


class MonitoringTests(unittest.TestCase):
    def test_binary_scores(self):
        self.assertAlmostEqual(a.score(.85,1),.0225)
        self.assertAlmostEqual(a.score(.85,0),.7225)
        self.assertIsNone(a.score(.85,None))

    def test_pending_not_failure(self):
        s=a.summary(sample()['registros'])
        self.assertEqual(s['pendentes'],1)
        self.assertEqual(s['avaliados'],0)
        self.assertIsNone(s['brier'])

    def test_late_open_is_zero(self):
        r=sample('aberto_atrasado')['registros'][0]
        self.assertEqual(r['realizado'],0)
        self.assertAlmostEqual(r['erro_brier'],.7225)

    def test_retired_and_inferred_excluded(self):
        for status in ['retirado_sem_resposta','resposta_inferida_na_geracao']:
            s=a.summary(sample(status)['registros'])
            self.assertEqual(s['excluidos'],1)
            self.assertIsNone(s['brier'])

    def test_freeze_original_probability_and_mode(self):
        old=sample();new=sample('no_prazo',.10)
        new['registros'][0]['registrada_em']='2026-11-05T15:00:00+00:00'
        r=a.merge(new,old)['registros'][0]
        self.assertEqual(r['probabilidade'],.85)
        self.assertEqual(r['origem'],'registrada_sem_resultado')
        self.assertEqual(r['registrada_em'],old['registros'][0]['registrada_em'])
        self.assertAlmostEqual(r['erro_brier'],.0225)

    def test_hindsight_explicit(self):
        self.assertEqual(sample('no_prazo')['registros'][0]['origem'],'retrospectiva')

    def test_revision_keeps_prediction(self):
        old=sample('no_prazo');new=sample('fora_prazo',.20)
        new['registros'][0]['atributos_sha256']='changed'
        r=a.merge(new,old)['registros'][0]
        self.assertTrue(r['resultado_revisado'])
        self.assertTrue(r['atributos_revisados'])
        self.assertAlmostEqual(r['erro_brier'],.7225)

    def test_absent_cycle_retained_but_not_scored(self):
        old=sample('no_prazo');current=sample();current['registros']=[]
        r=a.merge(current,old)['registros'][0]
        self.assertTrue(r['ausente_na_extracao'])
        self.assertIsNone(r['erro_brier'])

    def test_no_future_or_training_leak(self):
        c={'ciclo_id':'P:1:1','demanda':'P:1','familia':'proposta','tipo':'material',
           'numero_ciclo':1,'entrada':'2025-12-01T10:00:00','evento_entrada':'1',
           'prazo_referencia_dias_uteis':5,'alertas':[]}
        f={'ciclo_id':'P:1:1','fila_total':20,'alvo_no_prazo':1}
        y={'ciclo_id':'P:1:1','resultado':'no_prazo','alvo_no_prazo':1,
           'resposta_em':'2025-12-02T10:00:00','dias_uteis_equivalentes':1}
        def predict(rows):
            self.assertEqual(rows,[{'fila_total':20}])
            return [{'probabilidade_no_prazo':.85}]
        args=([c],[{'chave':'P:1','codigo':'123'}],[f],[y],'2026-11-04T12:00:00',
              ['fila_total'],predict,'2026-11-04T15:00:00+00:00')
        self.assertEqual(a.build_candidates(*args)['registros'],[])
        c['entrada']='2026-01-02T10:00:00'
        self.assertEqual(len(a.build_candidates(*args)['registros']),1)

    def test_invalid_probability_or_score_rejected(self):
        for p in [float('nan'),1.1,-.1,True]:
            with self.assertRaises(ValueError):a.score(p,1)
        d=sample('no_prazo');d['registros'][0]['erro_brier']=.99
        with self.assertRaises(ValueError):a.validate(d)

    def test_duplicate_and_regression_rejected(self):
        d=sample();d['registros']*=2
        with self.assertRaises(ValueError):a.validate(d)
        d=sample();d['referencia']='2026-01-01T00:00:00'
        with self.assertRaises(ValueError):a.merge(d,sample())

    def test_same_input_idempotent(self):
        d=sample('no_prazo')
        self.assertEqual(a.merge(copy.deepcopy(d),d),d)


if __name__=='__main__':unittest.main()
