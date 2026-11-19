# -*- coding: utf-8 -*-
"""Addons: o reparo do perfil funciona de verdade e nao depende de sorte.

Contexto real: no projetor o servico morria no import (``ads_regra.py``
ausente do APK) e a Home abria sem conteudo. Depois de corrigir o APK, o que
o cliente chama de "addon nao carrega" tem OUTRA causa possivel, que e esta
aqui coberta: o perfil do aparelho (``addons/`` + ``addons/packages/``).
Quando o pacote nao esta la, o reparo tem de dizer exatamente qual addon
falta - nunca "sumir" com o erro - e repetir sem apagar nada do usuario.

Estes testes usam o modulo real (``repair``) sobre um perfil temporario com
zips de verdade, e o mesmo laço de tentativas do ``service.py``.
"""
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = os.path.join(RAIZ, 'kodi', 'addons', 'service.smarted.bootstrap')
sys.path.insert(0, ADDON)

import repair  # noqa: E402  (depois de ajustar o sys.path)

ADDON_XML = """<?xml version="1.0" encoding="UTF-8"?>
<addon id="%s" name="%s" version="%s" provider-name="teste">
  <requires>
    <import addon="xbmc.python" version="3.0.0"/>
%s  </requires>
  <extension point="xbmc.python.pluginsource" library="default.py">
    <provides>video</provides>
  </extension>
</addon>
"""


def _pacote(pasta, addon_id, versao='1.0.0', depende=(), arquivos=('default.py',)):
    """Cria o zip oficial do addon, como o Kodi espera em addons/packages."""
    os.makedirs(pasta, exist_ok=True)
    requires = ''.join('    <import addon="%s" version="1.0.0"/>\n' % d
                       for d in depende)
    with zipfile.ZipFile(os.path.join(pasta, '%s-%s.zip' % (addon_id, versao)),
                         'w') as z:
        z.writestr(addon_id + '/addon.xml',
                   ADDON_XML % (addon_id, addon_id, versao, requires))
        for nome in arquivos:
            z.writestr(addon_id + '/' + nome, '# %s\n' % nome)


class Perfil(object):
    """Perfil Kodi minimo: home/addons (instalados) e home/addons/packages."""

    def __init__(self):
        self.home = tempfile.mkdtemp()
        self.addons = os.path.join(self.home, 'addons')
        self.packages = os.path.join(self.addons, 'packages')
        os.makedirs(self.addons)
        os.makedirs(self.packages)

    def limpar(self):
        shutil.rmtree(self.home, ignore_errors=True)


class ReparoDoPerfilTest(unittest.TestCase):
    def setUp(self):
        self.perfil = Perfil()
        # pasta de payload do addon (cloudrequest); vazia e aceitavel aqui
        self.payload = tempfile.mkdtemp()

    def tearDown(self):
        self.perfil.limpar()
        shutil.rmtree(self.payload, ignore_errors=True)

    def test_instala_o_addon_e_as_dependencias_a_partir_dos_zips(self):
        _pacote(self.perfil.packages, repair.BRAZUCA_ID, depende=['script.module.six'])
        _pacote(self.perfil.packages, 'script.module.six')
        report = repair.repair_profile(self.perfil.home, self.payload)
        self.assertTrue(report['ok'], report)
        self.assertTrue(os.path.isdir(
            os.path.join(self.perfil.addons, repair.BRAZUCA_ID)))
        self.assertTrue(os.path.isfile(
            os.path.join(self.perfil.addons, repair.BRAZUCA_ID, 'default.py')))
        ok, motivo = repair.addon_status(self.perfil.addons, repair.BRAZUCA_ID)
        self.assertTrue(ok, motivo)

    def test_sem_pacote_o_reparo_diz_exatamente_o_que_falta(self):
        """Nunca esconder: o nome do addon ausente tem de aparecer."""
        report = repair.repair_profile(self.perfil.home, self.payload)
        self.assertFalse(report['ok'])
        self.assertIn(repair.BRAZUCA_ID, report['missing'])

    def test_segunda_passada_nao_quebra_nada(self):
        _pacote(self.perfil.packages, repair.BRAZUCA_ID)
        primeira = repair.repair_profile(self.perfil.home, self.payload)
        self.assertTrue(primeira['ok'], primeira)
        marca = os.path.join(self.perfil.addons, repair.BRAZUCA_ID, 'default.py')
        self.assertTrue(os.path.isfile(marca))
        segunda = repair.repair_profile(self.perfil.home, self.payload)
        self.assertTrue(segunda['ok'], segunda)
        self.assertTrue(os.path.isfile(marca), 'o reparo apagou o que instalou')

    def test_addon_ja_instalado_nao_e_tocado(self):
        _pacote(self.perfil.packages, repair.BRAZUCA_ID)
        destino = os.path.join(self.perfil.addons, repair.BRAZUCA_ID)
        os.makedirs(destino)
        with open(os.path.join(destino, 'addon.xml'), 'w', encoding='utf-8') as f:
            f.write(ADDON_XML % (repair.BRAZUCA_ID, repair.BRAZUCA_ID, '9.9.9', ''))
        with open(os.path.join(destino, 'default.py'), 'w', encoding='utf-8') as f:
            f.write('# versao do usuario\n')
        report = repair.repair_profile(self.perfil.home, self.payload)
        self.assertTrue(report['ok'], report)
        with open(os.path.join(destino, 'default.py'), encoding='utf-8') as f:
            self.assertIn('versao do usuario', f.read())

    def test_zip_corrompido_e_reportado_e_nao_derruba_o_reparo(self):
        caminho = os.path.join(self.perfil.packages,
                               '%s-1.0.0.zip' % repair.BRAZUCA_ID)
        with open(caminho, 'wb') as f:
            f.write(b'nao e um zip')
        report = repair.repair_profile(self.perfil.home, self.payload)
        self.assertFalse(report['ok'])
        self.assertTrue(report['missing'], 'falha silenciosa nao pode acontecer')

    def test_ciclo_de_tentativas_do_boot_termina_em_ok(self):
        """O laco do service.py (6 tentativas) chega em ok sem aparelho."""
        _pacote(self.perfil.packages, repair.BRAZUCA_ID, depende=['script.module.six'])
        _pacote(self.perfil.packages, 'script.module.six')
        tentativas = 0
        for tentativas in range(1, 7):
            report = repair.repair_profile(self.perfil.home, self.payload)
            if report['ok']:
                break
        self.assertTrue(report['ok'])
        self.assertEqual(tentativas, 1, 'o perfil ja estava ok na primeira passada')


if __name__ == '__main__':
    unittest.main()
