"""Acrescenta comprovante de atualizacao sem substituir outras regras locais."""
from pathlib import Path
from datetime import datetime
import hashlib, json, shutil, ast, os
pasta=Path(os.environ['USERPROFILE'])/'OneDrive - CAMG/Documentos/CATMAS-Termometro'
arquivo=pasta/'atualizar.py'
manifesto=pasta/'integridade.json'
original=arquivo.read_text(encoding='utf-8-sig')
trocas=[
("    if content==old.read_bytes() and history.exists() and monitoring==history.read_bytes():\n        return {'commit':git('rev-parse','HEAD',cwd=checkout),'alterado':False}", "    write_json(checkout/'atualizacao.json', {\n        'atualizado_em': datetime.now(timezone.utc).isoformat(),\n        'referencia': data['referencia'],\n        'dados_sha256': hashlib.sha256(content).hexdigest(),\n        'ciclo': run.name,\n    })"),
("git('add','--','dados.json.gz','acompanhamento.json.gz',cwd=checkout)", "git('add','--','dados.json.gz','acompanhamento.json.gz','atualizacao.json',cwd=checkout)"),
("changed <= {'dados.json.gz','acompanhamento.json.gz'}", "changed <= {'dados.json.gz','acompanhamento.json.gz','atualizacao.json'}")
]
novo=original
for antes,depois in trocas:
    if novo.count(antes)!=1:
        raise SystemExit('Versao local diferente da esperada; nenhum arquivo alterado. Envie atualizar.py para adaptar o ajuste.')
    novo=novo.replace(antes,depois,1)
ast.parse(novo)
man_original=manifesto.read_bytes()
man=json.loads(man_original.decode('utf-8-sig'))
if 'atualizar.py' in man:
    if hashlib.sha256(arquivo.read_bytes()).hexdigest()!=man['atualizar.py']:
        raise SystemExit('Integridade local divergente; nenhum arquivo alterado.')
    man['atualizar.py']=hashlib.sha256(novo.encode('utf-8')).hexdigest()
backup=pasta/('backup-data-atualizacao-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
backup.mkdir()
shutil.copy2(arquivo,backup/arquivo.name)
shutil.copy2(manifesto,backup/manifesto.name)
try:
    arquivo.write_bytes(novo.encode('utf-8'))
    manifesto.write_text(json.dumps(man,ensure_ascii=False,indent=2),encoding='utf-8')
except Exception:
    shutil.copy2(backup/arquivo.name,arquivo)
    shutil.copy2(backup/manifesto.name,manifesto)
    raise
print('Instalado. Backup:',backup)
print('A proxima publicacao registrara o horario mesmo sem novos eventos.')
