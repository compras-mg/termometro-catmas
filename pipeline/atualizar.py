# /// script
# requires-python = ">=3.12,<3.13"
# dependencies = ["impyla==0.24.0", "scikit-learn==1.8.0", "joblib==1.5.3", "numpy==2.3.5"]
# ///
"""Publica snapshot e acompanhamento no mesmo commit. Sem retreinar o modelo."""
import argparse, base64, contextlib, csv, gzip, hashlib, json, logging, math
import os, shutil, subprocess, sys, uuid, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = 'https://github.com/compras-mg/termometro-catmas.git'
PHASE = 'preparacao'

def write_json(path, data):
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)

def verify_package():
    manifest = json.loads((HERE/'integridade.json').read_text(encoding='utf-8'))
    for name, digest in manifest.items():
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest() != digest:
            raise ValueError('Pacote alterado ou incompleto: '+name)

def git(*args, cwd=None):
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='never')
    p = subprocess.run(['git', *args], cwd=cwd, env=env, capture_output=True, timeout=300)
    if p.returncode:
        raise RuntimeError('Git falhou. Confira instalacao, rede e autenticacao local; detalhes omitidos.')
    return p.stdout.decode('utf-8', errors='replace').strip()

def pack(folder, reports, target):
    write_json(folder/'resumo.json', {'status':'COMPLETO','arquivos':reports})
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for f in folder.iterdir():z.write(f, f.name)
    with zipfile.ZipFile(target) as z:
        if z.testzip():raise ValueError('ZIP invalido')

def extract_batch(run):
    import extracao_base as b
    import extracao_extra as x
    from impala.dbapi import connect
    ca = os.getenv('IMPALA_CA_CERT')
    opts = dict(host=os.getenv('IMPALA_HOST','dlmg.prodemge.gov.br'),
        port=int(os.getenv('IMPALA_PORT','21051')), auth_mechanism='LDAP',
        user=b.access_value(('impala_user','impala-user')),
        password=b.access_value(('impala_user_senha','impala-password')),
        use_http_transport=False,use_ssl=True,verify_cert=bool(ca),timeout=120)
    if ca:opts['ca_cert']=ca
    raw=run/'origem';extra=run/'complemento';raw.mkdir();extra.mkdir()
    conn=connect(**opts)
    try:
        reports=[]
        # Derive both alteration files from a single query to prevent a race
        # between history and its status text. Proposal texts are unnecessary.
        for name,(table,cols) in b.QUERIES.items():
            if name=='historico_alteracoes':continue
            logging.info('Extraindo %s',name)
            reports.append(b.extract(conn,raw,name,table,cols))
        name='historico_alteracoes_complemento'
        sql,cols=x.QUERIES[name]
        logging.info('Extraindo historico de alteracoes')
        er=x.extract(conn,extra,name,sql,cols)
        source=extra/er['arquivo']
        cols_base=b.QUERIES['historico_alteracoes'][1].split()
        target=raw/'historico_alteracoes.csv'
        with source.open(encoding='utf-8',newline='') as f, target.open('w',encoding='utf-8',newline='') as out:
            writer=csv.DictWriter(out,fieldnames=cols_base);writer.writeheader();count=0
            for row in csv.DictReader(f):
                writer.writerow({k:row.get(k,'\\N') for k in cols_base});count+=1
        reports.append({'arquivo':target.name,'colunas':cols_base,'registros':count,
            'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
        # Retain only the status prefix, not free-text analyst messages.
        reduced=source.with_suffix('.reduced.csv')
        with source.open(encoding='utf-8',newline='') as f, reduced.open('w',encoding='utf-8',newline='') as out:
            reader=csv.DictReader(f);writer=csv.DictWriter(out,fieldnames=reader.fieldnames);writer.writeheader()
            for row in reader:
                row['texto_evento']=row['texto_evento'].split('Status da')[0].strip()
                writer.writerow(row)
        os.replace(reduced,source)
        er['sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
        pack(raw,reports,run/'base.zip');pack(extra,[er],run/'complemento.zip')
    finally:conn.close()
    return run/'base.zip',run/'complemento.zip'

def generate(run, base, extra):
    import preparar_base, ajustar_ciclos, preparar_indicadores
    preparar_base.run(base,extra,run/'marcos')
    source=run/'marcos/base_marcos.jsonl'
    expected=sum(json.loads((run/'marcos/validacao.json').read_text(encoding='utf-8'))['contagens'].values())
    with source.open(encoding='utf-8') as f:
        if sum(1 for _ in f)!=expected:raise ValueError('Base de marcos incompleta')
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    ajustar_ciclos.run(run/'marcos/base_marcos.jsonl',run/'ciclos')
    preparar_indicadores.run(run/'ciclos/ciclos.jsonl',run/'indicadores')
    result=subprocess.run([sys.executable,'-X','utf8',str(HERE/'gerar_snapshot.py'),str(run)],
        capture_output=True,timeout=600)
    if result.returncode:raise RuntimeError('Gerador de snapshot falhou; detalhes omitidos')
    if hashlib.sha256(source.read_bytes()).hexdigest()!=source_hash:raise ValueError('Base intermediaria alterada durante o calculo')
    data=json.loads((run/'dados.json').read_text(encoding='utf-8'))
    validate(data)
    blob=gzip.compress(json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode(),mtime=0)
    if json.loads(gzip.decompress(blob))!=data:raise ValueError('Compactacao inconsistente')
    (run/'dados.json.gz').write_bytes(blob)
    import acompanhamento
    write_json(run/'acompanhamento-candidato.json', acompanhamento.candidates(run, HERE))
    return data

def validate(d, previous=None):
    if set(d)!={'referencia','total_fila','pausadas','tipos','mensal','consulta'}:raise ValueError('Campos publicos inesperados')
    reference=datetime.fromisoformat(d['referencia'])
    # Source dates have no confirmed timezone; one-day tolerance avoids assigning one.
    if reference.replace(tzinfo=None)>datetime.now(timezone.utc).replace(tzinfo=None)+timedelta(days=1):raise ValueError('Referencia futura')
    kinds={'item_material','item_servico','material','servico','alteracao'}
    if set(d['tipos'])!=kinds or not d['consulta'] or not d['mensal']:raise ValueError('Snapshot incompleto')
    fields={'numero','tipo','situacao','divergencia','fila','pausado','entrada','ciclo','anteriores','anteriores_tipo'}
    for r in d['consulta']:
        if set(r)!=fields or r['tipo'] not in kinds or not str(r['numero']).isdigit():raise ValueError('Consulta invalida')
    if sum(bool(r['fila']) for r in d['consulta'])!=d['total_fila']:raise ValueError('Fila inconsistente')
    if sum(s['fila'] for s in d['tipos'].values())!=d['total_fila']:raise ValueError('Fila por tipo inconsistente')
    for s in d['tipos'].values():
        p=s['probabilidade_no_prazo'];q=s['probabilidade_atraso']
        if not 0<=p<=1 or not math.isclose(p+q,1):raise ValueError('Probabilidade invalida')
    if previous:
        if reference<datetime.fromisoformat(previous['referencia']):raise ValueError('Referencia regrediu')
        if len(d['consulta'])<len(previous['consulta'])*.95:raise ValueError('Queda superior a 5% exige revisao da extracao')

def publish(run,data):
    import acompanhamento
    checkout=run/'publicacao'
    git('clone','--depth','1','--branch','main',REPO,str(checkout))
    old=checkout/'dados.json.gz'
    previous=json.loads(gzip.decompress(old.read_bytes()))
    validate(data,previous)
    content=(run/'dados.json.gz').read_bytes()
    history=checkout/'acompanhamento.json.gz'
    prior=json.loads(gzip.decompress(history.read_bytes())) if history.exists() else None
    candidate=json.loads((run/'acompanhamento-candidato.json').read_text(encoding='utf-8'))
    if candidate['referencia'] != data['referencia']:
        raise ValueError('Acompanhamento e snapshot de referencias diferentes')
    merged=acompanhamento.merge(candidate,prior)
    # Mesma referencia e mesmos registros nao exigem novo commit apenas pelo horario.
    if prior and merged['referencia']==prior['referencia'] and merged['registros']==prior['registros']:
        merged['gerado_em']=prior['gerado_em']
    monitoring=gzip.compress(json.dumps(merged,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode(),mtime=0)
    if json.loads(gzip.decompress(monitoring)) != merged:
        raise ValueError('Compactacao do acompanhamento inconsistente')
    (run/'acompanhamento.json.gz').write_bytes(monitoring)
    if content==old.read_bytes() and history.exists() and monitoring==history.read_bytes():
        return {'commit':git('rev-parse','HEAD',cwd=checkout),'alterado':False}
    old.write_bytes(content)
    history.write_bytes(monitoring)
    git('add','--','dados.json.gz','acompanhamento.json.gz',cwd=checkout)
    changed=set(git('diff','--cached','--name-only',cwd=checkout).splitlines())
    if not changed or not changed <= {'dados.json.gz','acompanhamento.json.gz'}:
        raise ValueError('Publicacao fora do escopo')
    git('-c','user.name=Atualizacao CATMAS','-c','user.email=catmas-bot@users.noreply.github.com',
        'commit','-m','Atualiza snapshot CATMAS '+data['referencia'],cwd=checkout)
    commit=git('rev-parse','HEAD',cwd=checkout)
    git('push','origin','HEAD:main',cwd=checkout)
    # Push never forces: a concurrent edit rejects this batch and preserves the site.
    return {'commit':commit,'alterado':True}

def main():
    global PHASE
    parser=argparse.ArgumentParser()
    parser.add_argument('--publicar',action='store_true')
    parser.add_argument('--base',type=Path)
    parser.add_argument('--complemento',type=Path)
    args=parser.parse_args()
    if bool(args.base)!=bool(args.complemento):parser.error('Informe ambos os ZIPs')
    if args.base and args.publicar:parser.error('ZIPs de teste nao podem ser publicados')
    state=HERE/'estado';state.mkdir(exist_ok=True)
    from extracao_base import execution_lock
    with execution_lock(state/'execucao.lock'):
        run=state/('lote-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]);run.mkdir()
        logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s',
            handlers=[logging.FileHandler(run/'execucao.log',encoding='utf-8'),logging.StreamHandler()])
        try:
            verify_package()
            PHASE='extracao'
            if args.base:base,extra=args.base.resolve(),args.complemento.resolve()
            else:base,extra=extract_batch(run)
            PHASE='calculo'
            with (run/'calculo.log').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):
                data=generate(run,base,extra)
            result={'status':'VALIDADO','referencia':data['referencia'],'demandas':len(data['consulta']),
                'sha256':hashlib.sha256((run/'dados.json.gz').read_bytes()).hexdigest(),
                'fim':datetime.now(timezone.utc).isoformat(),'repositorio':REPO}
            if args.publicar:
                PHASE='publicacao';result.update(publish(run,data));result['status']='PUBLICADO'
                write_json(state/'ultima-publicacao.json',result)
            write_json(run/'resultado.json',result)
            logging.info('%s: %s demandas; referencia %s. Pasta: %s',result['status'],result['demandas'],data['referencia'],run)
            return 0
        except Exception as exc:
            write_json(run/'falha.json',{'etapa':PHASE,'tipo':type(exc).__name__})
            logging.error('Falha na etapa %s (%s). Ultima publicacao preservada. Pasta: %s',PHASE,type(exc).__name__,run)
            return 1

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print('Falha na preparacao ou outra execucao ativa: '+type(exc).__name__)
        sys.exit(1)
