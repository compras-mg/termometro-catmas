"""Instala apenas acompanhamento, atualizador e manifesto; preserva modelo e dados."""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


def install(target):
    package=Path(__file__).resolve().parent
    target=Path(target).resolve()
    if target==package:
        raise ValueError('Extraia o pacote em uma pasta separada da instalacao atual.')
    before=json.loads((package/'integridade-anterior.json').read_text(encoding='utf-8'))
    after=json.loads((package/'integridade.json').read_text(encoding='utf-8'))
    current=json.loads((target/'integridade.json').read_text(encoding='utf-8'))
    if current not in (before,after):
        raise ValueError('A instalacao mudou. Nenhum arquivo alterado; revisar a versao antes de instalar.')
    for name,sha in current.items():
        if hashlib.sha256((target/name).read_bytes()).hexdigest()!=sha:
            raise ValueError('Arquivo instalado diferente do manifesto: '+name)
    for name in ('atualizar.py','acompanhamento.py'):
        content=(package/name).read_bytes()
        if hashlib.sha256(content).hexdigest()!=after[name]:
            raise ValueError('Pacote incompleto ou alterado: '+name)
        compile(content,name,'exec')
    if current==after:
        print('Acompanhamento ja instalado e integridade conferida.');return
    spec=importlib.util.spec_from_file_location('extracao_instalada',target/'extracao_base.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    state=target/'estado';state.mkdir(exist_ok=True)
    with module.execution_lock(state/'execucao.lock'):
        # Revalidar sob a trava antes de substituir os arquivos.
        if json.loads((target/'integridade.json').read_text(encoding='utf-8'))!=before:
            raise ValueError('Instalacao mudou durante a verificacao.')
        for name,sha in before.items():
            if hashlib.sha256((target/name).read_bytes()).hexdigest()!=sha:
                raise ValueError('Arquivo mudou durante a verificacao: '+name)
        names=('atualizar.py','acompanhamento.py','integridade.json')
        backup=target/('backup-acompanhamento-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        backup.mkdir()
        existed={name:(target/name).exists() for name in names}
        for name in names:
            if existed[name]:shutil.copy2(target/name,backup/name)
        try:
            for name in names:
                tmp=target/(name+'.acompanhamento.tmp')
                tmp.write_bytes((package/name).read_bytes());os.replace(tmp,target/name)
            for name,sha in after.items():
                if hashlib.sha256((target/name).read_bytes()).hexdigest()!=sha:
                    raise ValueError('Conferencia final falhou: '+name)
        except BaseException:
            for name in names:
                if existed[name]:shutil.copy2(backup/name,target/name)
                elif (target/name).exists():(target/name).unlink()
            raise
    print('INSTALADO: acompanhamento de probabilidades. Backup:',backup)
    print('Modelo, consultas, credenciais e tarefa agendada preservados.')
    print('Execute atualizar.py --publicar para gerar e publicar a primeira avaliacao.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--destino',type=Path,default=Path.home()/'OneDrive - CAMG/Documentos/CATMAS-Termometro')
    args=parser.parse_args()
    try:install(args.destino)
    except Exception as exc:
        print('Instalacao interrompida:',str(exc));sys.exit(1)
