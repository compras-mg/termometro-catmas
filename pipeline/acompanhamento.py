"""Previsoes imutaveis por ciclo e resultados revisaveis; sem dados pessoais."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

MODEL_SHA = '131c7324c0cd78d8258c5df5ff5e8b964d0bf5a7fc7f96c646e70acd420db479'
EVALUATION_START = '2026-01-01'  # Posterior ao treino e calibracao documentados.
KINDS = {'item_material', 'item_servico', 'material', 'servico', 'alteracao'}
RULE_VERSION = 'catmas-prazo-v1'
FROZEN = ('id', 'numero', 'tipo', 'ciclo', 'entrada', 'prazo', 'probabilidade',
          'modelo', 'atributos_sha256', 'registrada_em', 'referencia_inicial', 'origem')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode()).hexdigest()


def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line]


def score(p, y):
    if type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError('Probabilidade invalida')
    if y is not None and (type(y) is not int or y not in (0, 1)):
        raise ValueError('Resultado nao binario')
    return None if y is None else (p - y) ** 2


def candidates(run, package):
    """Usa atributos NA ENTRADA; nunca a probabilidade atual do cartao."""
    import joblib
    from prever import prever
    run, package = Path(run), Path(package)
    model = package / 'modelo.joblib'
    model_sha = hashlib.sha256(model.read_bytes()).hexdigest()
    if model_sha != MODEL_SHA:
        raise ValueError('Modelo novo exige revisar corte temporal da avaliacao')
    bundle = joblib.load(model)
    return build_candidates(
        jsonl(run / 'ciclos/ciclos.jsonl'), jsonl(run / 'marcos/base_marcos.jsonl'),
        jsonl(run / 'indicadores/atributos_na_entrada.jsonl'),
        jsonl(run / 'indicadores/resultados.jsonl'),
        json.loads((run / 'indicadores/resumo.json').read_text(encoding='utf-8'))['corte_observado'],
        list(bundle['features']), lambda rows: prever(bundle, rows),
        datetime.now(timezone.utc).isoformat(), model_sha)


def unique(rows, key):
    result = {r[key]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Identificadores duplicados: ' + key)
    return result


def build_candidates(cycles, demands, features, outcomes, reference, feature_names,
                     predict, recorded_at, model_sha=MODEL_SHA):
    cs, rs = unique(cycles, 'ciclo_id'), unique(demands, 'chave')
    fs, ys = unique(features, 'ciclo_id'), unique(outcomes, 'ciclo_id')
    if set(cs) != set(fs) or set(cs) != set(ys):
        raise ValueError('Ciclos, atributos e resultados nao correspondem')
    eligible = [c for c in cycles if c['entrada'] >= EVALUATION_START]
    inputs = [{k: fs[c['ciclo_id']][k] for k in feature_names} for c in eligible]
    predictions = predict(inputs) if inputs else []
    if len(predictions) != len(eligible):
        raise ValueError('Predicoes incompletas')
    records = []
    for c, attrs, pred in zip(eligible, inputs, predictions):
        r, y = rs[c['demanda']], ys[c['ciclo_id']]
        kind = 'alteracao' if c['familia'] == 'alteracao' else c['tipo']
        p = pred['probabilidade_no_prazo']
        target = y['alvo_no_prazo']
        status = y['resultado']
        if status not in {'no_prazo', 'fora_prazo', 'aberto_atrasado', 'aberto_indeterminado',
                          'retirado_sem_resposta', 'resposta_inferida_na_geracao'}:
            raise ValueError('Resultado desconhecido')
        if 'resposta_durante_pausa_sem_reenvio_registrado' in c.get('alertas', []):
            status, target = 'revisao_necessaria', None
        records.append({
            'id': digest([c['demanda'], c['entrada'], c['evento_entrada']]),
            'numero': str(r['codigo']), 'tipo': kind, 'ciclo': c['numero_ciclo'],
            'entrada': c['entrada'], 'prazo': c['prazo_referencia_dias_uteis'],
            'probabilidade': p, 'modelo': model_sha, 'atributos_sha256': digest(attrs),
            'registrada_em': recorded_at, 'referencia_inicial': reference,
            'origem': 'registrada_sem_resultado' if status == 'aberto_indeterminado' else 'retrospectiva',
            'resultado': status, 'realizado': target, 'resposta_em': y['resposta_em'],
            'dias_consumidos': y['dias_uteis_equivalentes'], 'erro_brier': score(p, target),
            'atributos_revisados': False, 'resultado_revisado': False,
            'ausente_na_extracao': False,
        })
    result = {'schema_version': 1, 'regra': RULE_VERSION, 'inicio_avaliacao': EVALUATION_START,
              'referencia': reference, 'gerado_em': recorded_at, 'registros': records}
    validate(result)
    return result


def merge(current, previous=None):
    """Conserva a primeira previsao PUBLICADA; atualiza somente a apuracao."""
    validate(current)
    if not previous:
        return current
    validate(previous)
    if current['regra'] != previous['regra'] or current['referencia'] < previous['referencia']:
        raise ValueError('Regra alterada ou referencia regrediu')
    old = unique(previous['registros'], 'id')
    result = {k: v for k, v in current.items() if k != 'registros'}
    result['registros'] = []
    seen = set()
    for candidate in current['registros']:
        row = dict(candidate)
        prior = old.get(row['id'])
        if prior:
            if any(row[k] != prior[k] for k in ('numero', 'tipo', 'entrada', 'prazo')):
                raise ValueError('Identidade ou prazo do ciclo mudou')
            row['atributos_revisados'] = (prior['atributos_revisados'] or
                                         row['atributos_sha256'] != prior['atributos_sha256'])
            row['resultado_revisado'] = (prior['resultado_revisado'] or
                                        prior['realizado'] is not None and prior['realizado'] != row['realizado'])
            for k in FROZEN:
                row[k] = prior[k]
            row['erro_brier'] = score(row['probabilidade'], row['realizado'])
        seen.add(row['id'])
        result['registros'].append(row)
    # Nao apagar previsoes se um ciclo desaparecer por revisao da origem.
    for key, row in old.items():
        if key not in seen:
            result['registros'].append({**row, 'ausente_na_extracao': True,
                'resultado': 'ausente_na_extracao', 'realizado': None,
                'erro_brier': None, 'resultado_revisado': True})
    validate(result)
    return result


def validate(data):
    if set(data) != {'schema_version', 'regra', 'inicio_avaliacao', 'referencia', 'gerado_em', 'registros'}:
        raise ValueError('Campos publicos inesperados no acompanhamento')
    if data['schema_version'] != 1 or data['regra'] != RULE_VERSION:
        raise ValueError('Versao de acompanhamento desconhecida')
    datetime.fromisoformat(data['referencia'])
    unique(data['registros'], 'id')
    expected = set(FROZEN) | {'resultado', 'realizado', 'resposta_em', 'dias_consumidos',
                             'erro_brier', 'atributos_revisados', 'resultado_revisado', 'ausente_na_extracao'}
    for r in data['registros']:
        if set(r) != expected or r['tipo'] not in KINDS or not r['numero'].isdigit():
            raise ValueError('Registro publico inesperado')
        if r['origem'] not in {'registrada_sem_resultado', 'retrospectiva'}:
            raise ValueError('Origem da previsao invalida')
        expected_y = {'no_prazo': 1, 'fora_prazo': 0, 'aberto_atrasado': 0}.get(r['resultado'])
        if r['realizado'] != expected_y:
            raise ValueError('Resultado e alvo divergentes')
        error = score(r['probabilidade'], r['realizado'])
        if (error is None) != (r['erro_brier'] is None) or error is not None and not math.isclose(error, r['erro_brier'], abs_tol=1e-12):
            raise ValueError('Erro Brier divergente')


def summary(rows):
    evaluated = [r for r in rows if r['realizado'] is not None]
    n = len(evaluated)
    return {'total': len(rows), 'avaliados': n,
            'pendentes': sum(r['resultado'] == 'aberto_indeterminado' for r in rows),
            'excluidos': sum(r['realizado'] is None and r['resultado'] != 'aberto_indeterminado' for r in rows),
            'brier': sum(r['erro_brier'] for r in evaluated) / n if n else None,
            'previsto': sum(r['probabilidade'] for r in evaluated) / n if n else None,
            'realizado': sum(r['realizado'] for r in evaluated) / n if n else None}
