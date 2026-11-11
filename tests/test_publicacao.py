import gzip
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_acompanhamento import sample

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'pipeline'))
import atualizar


def git(path,*args):
    return subprocess.check_output(['git',*args],cwd=path,stderr=subprocess.DEVNULL).decode().strip()


def snapshot():
    kinds=['item_material','item_servico','material','servico','alteracao']
    return {'referencia':'2026-11-04T12:00:00','total_fila':0,'pausadas':0,
            'tipos':{k:{'probabilidade_no_prazo':.85,'probabilidade_atraso':.15,'fila':0} for k in kinds},
            'mensal':{'2026-11':{}},'consulta':[{'numero':'123','tipo':'item_material','situacao':'Aprovada',
             'divergencia':False,'fila':False,'pausado':False,'entrada':'2026-11-01T10:00:00','ciclo':1,
             'anteriores':None,'anteriores_tipo':None}]}


class PublicationTests(unittest.TestCase):
    def test_atomic_publication_preserves_site_and_forecast(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);remote=root/'remote.git';seed=root/'seed';seed.mkdir()
            git(root,'init','--bare',str(remote));git(seed,'init','-b','main')
            (seed/'index.html').write_text('preserve me')
            data=snapshot();blob=gzip.compress(json.dumps(data).encode(),mtime=0)
            (seed/'dados.json.gz').write_bytes(blob)
            git(seed,'add','.');git(seed,'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','Seed')
            git(seed,'remote','add','origin',str(remote));git(seed,'push','origin','main')
            with patch.object(atualizar,'REPO',str(remote)):
                def run(name,candidate):
                    folder=root/name;folder.mkdir();(folder/'dados.json.gz').write_bytes(blob)
                    (folder/'acompanhamento-candidato.json').write_text(json.dumps(candidate))
                    return folder,atualizar.publish(folder,data)
                first,result=run('first',sample())
                self.assertTrue(result['alterado'])
                second,result=run('second',sample('no_prazo',.1))
                out=json.loads(gzip.decompress((second/'publicacao/acompanhamento.json.gz').read_bytes()))
                self.assertEqual(out['registros'][0]['probabilidade'],.85)
                self.assertAlmostEqual(out['registros'][0]['erro_brier'],.0225)
                self.assertEqual((second/'publicacao/index.html').read_text(),'preserve me')
                _,result=run('third',sample('no_prazo',.1))
                self.assertFalse(result['alterado'])

    def test_installation_and_idempotence(self):
        spec=importlib.util.spec_from_file_location('installer',ROOT/'pipeline/INSTALAR-ACOMPANHAMENTO.py')
        installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);package=root/'package';target=root/'target';package.mkdir();target.mkdir()
            before={'atualizar.py':'', 'extracao_base.py':''}
            (target/'atualizar.py').write_text('print("old")\n')
            (target/'extracao_base.py').write_text('from contextlib import contextmanager\n@contextmanager\ndef execution_lock(path):\n yield\n')
            import hashlib
            before={k:hashlib.sha256((target/k).read_bytes()).hexdigest() for k in before}
            after=dict(before)
            for name in ['atualizar.py','acompanhamento.py']:
                (package/name).write_text('print("new")\n')
                after[name]=hashlib.sha256((package/name).read_bytes()).hexdigest()
            (package/'integridade-anterior.json').write_text(json.dumps(before))
            (package/'integridade.json').write_text(json.dumps(after))
            (target/'integridade.json').write_text(json.dumps(before))
            with patch.object(installer,'__file__',str(package/'install.py')):
                installer.install(target);installer.install(target)
                self.assertEqual(json.loads((target/'integridade.json').read_text()),after)
                self.assertEqual(len(list(target.glob('backup-acompanhamento-*'))),1)


if __name__=='__main__':unittest.main()
