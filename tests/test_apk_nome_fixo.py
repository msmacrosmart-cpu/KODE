# -*- coding: utf-8 -*-
"""O arquivo publicado no Dropbox tem NOME FIXO: SMARTEDTV.apk.

Quem mantem o app troca o conteudo por dentro e o link nunca muda. Estes
testes travam esse contrato e o que ele exige:

* o nome do arquivo e sempre `SMARTEDTV.apk` (nada de nome por versao);
* o link usado e o do Dropbox, com `rlkey` e `dl=1` (download direto);
* um arquivo publicado com a versao ANTIGA nao e instalado - o Android
  responde "Aplicativo nao instalado" e o usuario nao descobre a causa;
* download incompleto (pagina de erro do Dropbox com extensao .apk) e
  recusado antes de abrir o instalador;
* quando o link do Dropbox nao entrega o APK completo, cai para a release do
  GitHub em vez de abrir uma pagina de erro.
"""
import importlib.util
import os
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap' / 'vip.py'
RELEASE = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap' / 'smarted_release.py'
NOME_FIXO = 'SMARTEDTV.apk'


def carregar_vip():
    """Carrega vip.py com stubs de xbmc* e um filesystem local."""
    salvos = {n: sys.modules.get(n) for n in
              ('xbmc', 'xbmcgui', 'xbmcaddon', 'xbmcvfs')}
    xbmc = types.ModuleType('xbmc')
    xbmc.LOGINFO, xbmc.LOGWARNING, xbmc.LOGERROR = 1, 3, 4
    xbmc.LOGS = []
    xbmc.log = lambda msg, level=1: xbmc.LOGS.append((level, msg))
    xbmc.BUILTINS = []
    xbmc.executebuiltin = lambda cmd: xbmc.BUILTINS.append(cmd)
    xbmc.getCondVisibility = lambda cond: True

    xbmcgui = types.ModuleType('xbmcgui')
    xbmcgui.NOTIFICACOES = []

    class Dialog(object):
        def ok(self, *a):
            pass

        def notification(self, *a):
            xbmcgui.NOTIFICACOES.append(a)

        def yesno(self, *a):
            return False

    xbmcgui.Dialog = Dialog
    xbmcgui.NOTIFICATION_INFO, xbmcgui.NOTIFICATION_ERROR = 0, 1

    xbmcaddon = types.ModuleType('xbmcaddon')

    class Addon(object):
        def __init__(self, *a):
            pass

        def getAddonInfo(self, chave):
            return ''

    xbmcaddon.Addon = Addon

    xbmcvfs = types.ModuleType('xbmcvfs')
    xbmcvfs.translatePath = lambda p: p
    xbmcvfs.exists = os.path.exists
    xbmcvfs.mkdir = lambda p: os.makedirs(p, exist_ok=True)

    class File(object):
        def __init__(self, caminho, modo='r'):
            self.caminho, self.modo = caminho, modo

        def read(self, n=-1):
            return b''

        def write(self, dados):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    xbmcvfs.File = File

    sys.modules.update({'xbmc': xbmc, 'xbmcgui': xbmcgui,
                        'xbmcaddon': xbmcaddon, 'xbmcvfs': xbmcvfs})
    try:
        spec = importlib.util.spec_from_file_location('vip_nome_fixo', VIP)
        modulo = importlib.util.module_from_spec(spec)
        with __import__('unittest.mock', fromlist=['patch']).patch.object(
                sys, 'path', [str(VIP.parent)] + sys.path):
            spec.loader.exec_module(modulo)
    finally:
        for nome, antigo in salvos.items():
            if antigo is None:
                sys.modules.pop(nome, None)
            else:
                sys.modules[nome] = antigo
    return modulo, xbmc, xbmcgui


def apk_com_versao(caminho, nome, codigo):
    """APK minimo que carrega o descritor de versao, como o APK real."""
    with zipfile.ZipFile(caminho, 'w') as z:
        z.writestr('assets/addons/service.smarted.bootstrap/'
                   'smarted_release.py',
                   'VERSION_NAME="%s"\nVERSION_CODE=%d\n' % (nome, codigo))


class NomeFixoTest(unittest.TestCase):
    def setUp(self):
        self.vip, self.xbmc, self.xbmcgui = carregar_vip()
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__('shutil').rmtree(self.tmp, True))

    def test_o_arquivo_publicado_tem_nome_fixo(self):
        self.assertEqual(self.vip.APK_NOME, NOME_FIXO)
        self.assertTrue(self.vip.APK.startswith('https://www.dropbox.com/scl/fi/'))
        self.assertIn('/' + NOME_FIXO + '?', self.vip.APK)

    def test_download_direto_no_dropbox(self):
        # dl=1 baixa o arquivo; dl=0 abriria a pagina do Dropbox
        self.assertIn('dl=1', self.vip.APK)
        self.assertNotIn('dl=0', self.vip.APK)
        # sem rlkey o link /scl/fi/ nao abre
        self.assertIn('rlkey=', self.vip.APK)

    def test_versao_lida_de_dentro_do_apk(self):
        caminho = self.tmp / 'novo.apk'
        apk_com_versao(caminho, '1.0.8', 2103080)
        self.assertEqual(self.vip.versao_do_apk(caminho), (2103080, '1.0.8'))

    def test_arquivo_que_nao_e_o_app_nao_tem_versao(self):
        caminho = self.tmp / 'pagina.apk'
        with zipfile.ZipFile(caminho, 'w') as z:
            z.writestr('index.html', '<html>erro</html>')
        self.assertEqual(self.vip.versao_do_apk(caminho), (None, None))

    def test_versao_antiga_nao_e_instalada(self):
        """O caso do Dropbox hoje: link entrega a v22 em vez do APK atual."""
        caminho = self.tmp / 'antigo.apk'
        apk_com_versao(caminho, '1.0.22', 2102999)
        self.assertFalse(self.vip._apk_mais_novo_que_o_instalado(caminho))

    def test_versao_igual_ou_maior_pode_instalar(self):
        atual = self.tmp / 'atual.apk'
        apk_com_versao(atual, self.vip.CURRENT_VERSION_NAME,
                       self.vip.CURRENT_VERSION_CODE)
        self.assertTrue(self.vip._apk_mais_novo_que_o_instalado(atual))
        novo = self.tmp / 'novo.apk'
        apk_com_versao(novo, '9.9.9', self.vip.CURRENT_VERSION_CODE + 1)
        self.assertTrue(self.vip._apk_mais_novo_que_o_instalado(novo))

    def test_download_incompleto_nao_chega_ao_instalador(self):
        caminho = self.tmp / 'curto.apk'
        apk_com_versao(caminho, '1.0.101', 2103087)      # poucos KB
        self.assertFalse(self.vip.instalar_apk_baixado(caminho))
        self.assertEqual(self.xbmc.BUILTINS, [])
        self.assertTrue(self.xbmcgui.NOTIFICACOES)

    def test_instalador_so_abre_com_apk_completo_e_mais_novo(self):
        caminho = self.tmp / 'completo.apk'
        with zipfile.ZipFile(caminho, 'w') as z:
            z.writestr('assets/addons/service.smarted.bootstrap/'
                       'smarted_release.py',
                       'VERSION_NAME="9.9.9"\nVERSION_CODE=%d\n'
                       % (self.vip.CURRENT_VERSION_CODE + 1))
            z.writestr('recheio.bin', b'\0' * (self.vip.APK_TAMANHO_MINIMO + 1))
        self.assertTrue(self.vip.instalar_apk_baixado(caminho))
        self.assertTrue(any('package-archive' in b for b in self.xbmc.BUILTINS))

    def test_link_do_dropbox_incompleto_cai_para_o_github(self):
        chamadas = []

        def cabecalhos(url):
            chamadas.append(url)
            if 'dropbox' in url:
                return (5000, self.vip.APK_NOME)
            return (287248566, 'SMARTEDTV-universal.apk')

        self.vip._cabecalhos_remotos = cabecalhos
        url, motivo = self.vip.resolver_apk_publicado()
        self.assertEqual(motivo, 'github')
        self.assertEqual(url, self.vip.APK_GITHUB)
        self.assertIn('github.com', url)

    def test_descobre_o_arquivo_pelo_nome_na_pasta(self):
        """Publicar = trocar o arquivo de nome fixo na pasta. O app acha o token.

        O Dropbox nao aceita "pasta/<nome>" direto na URL (cada arquivo tem o
        proprio token), entao o app le a pagina publica da pasta e pega o token
        do arquivo com o nome combinado. E isso que torna o NOME o contrato.
        """
        token = 'AK7fQutCVmMZBWlqKAt0p-g'
        html = ('<a href="/scl/fo/5w6yfp0tvee0xro2wh0m3/%s/SMARTEDTV.apk'
                '?rlkey=3b8m9dnw571waz7vs83n0vn17&dl=0">' % token)

        class Resposta(object):
            def read(self):
                return html.encode('utf-8')

        self.vip._urlopen_request = lambda: (
            lambda url, headers=None, timeout=None: Resposta(),
            lambda req, timeout=None: Resposta())
        url = self.vip.url_do_apk_por_nome()
        self.assertEqual(
            url, 'https://www.dropbox.com/scl/fo/5w6yfp0tvee0xro2wh0m3/%s/'
                 'SMARTEDTV.apk?rlkey=3b8m9dnw571waz7vs83n0vn17&dl=1'
                 % token)
        self.vip._cabecalhos_remotos = lambda u: (287248566,
                                                  'SMARTEDTV.apk')
        encontrada, motivo = self.vip.resolver_apk_publicado()
        self.assertEqual(motivo, 'dropbox-nome')
        self.assertEqual(encontrada, url)

    def test_pasta_sem_o_arquivo_cai_para_o_link_direto(self):
        class Resposta(object):
            def read(self):
                return b'<html>pasta vazia</html>'

        self.vip._urlopen_request = lambda: (
            lambda url, headers=None, timeout=None: Resposta(),
            lambda req, timeout=None: Resposta())
        self.assertIsNone(self.vip.url_do_apk_por_nome())
        self.vip._cabecalhos_remotos = lambda url: (287248566,
                                                    'SMARTEDTV.apk')
        url, motivo = self.vip.resolver_apk_publicado()
        self.assertEqual(motivo, 'dropbox')
        self.assertEqual(url, self.vip.APK)

    def test_link_de_outro_arquivo_do_dropbox_nao_e_usado(self):
        """O caso real: o link entrega SMARTEDTV-2atual.apk (v22, 242 MB).

        O tamanho engana (242 MB parece APK legitimo), mas o nome nao e o
        combinado. Como o usuario troca o conteudo do arquivo de nome fixo,
        aceitar outro nome seria instalar uma versao qualquer.
        """
        self.vip._cabecalhos_remotos = lambda url: (
            (242222254, 'SMARTEDTV-2atual.apk') if 'dropbox' in url
            else (287248566, 'SMARTEDTV-universal.apk'))
        url, motivo = self.vip.resolver_apk_publicado()
        # O motivo do descarte do Dropbox fica no log; o retorno diz de onde
        # veio o APK usado. O que importa: nao entregar o arquivo errado.
        self.assertEqual(url, self.vip.APK_GITHUB)
        self.assertEqual(motivo, 'github')

    def test_nome_do_arquivo_servido_e_conferido(self):
        """Qualquer nome diferente do combinado e recusado, mesmo se grande."""
        self.vip._cabecalhos_remotos = lambda url: (
            (242222254, 'SMARTEDTV22.apk') if 'dropbox' in url
            else (None, None))  # sem reserva: isola o veredito do Dropbox
        self.vip.APK_GITHUB = None
        url, motivo = self.vip.resolver_apk_publicado()
        self.assertIsNone(url)
        self.assertIn('SMARTEDTV22.apk', motivo)

    def test_sem_nenhum_apk_confiavel_nao_abre_nada(self):
        self.vip._cabecalhos_remotos = lambda url: (10, 'erro.html')
        self.vip.APK_GITHUB = None
        self.assertEqual(self.vip.resolver_apk_publicado()[0], None)
        self.xbmc.BUILTINS.clear()
        self.assertFalse(self.vip.open_apk_download())
        self.assertEqual(self.xbmc.BUILTINS, [])

    def test_baixar_apk_usa_o_link_resolvido(self):
        self.vip._cabecalhos_remotos = lambda url: (
            287248566, 'SMARTEDTV.apk')
        self.vip.url_do_apk_por_nome = lambda nome=None: None
        self.assertTrue(self.vip.open_apk_download())
        self.assertEqual(self.xbmc.BUILTINS,
                         ['StartAndroidActivity(,android.intent.action.VIEW,,%s)'
                          % self.vip.APK])

    def test_versao_do_apk_publicado_no_repositorio(self):
        """O descritor empacotado no APK e o mesmo do repositorio."""
        texto = RELEASE.read_text()
        import re
        nome = re.search(r'VERSION_NAME="([^"]+)"', texto).group(1)
        codigo = int(re.search(r'VERSION_CODE=(\d+)', texto).group(1))
        caminho = self.tmp / 'do_repo.apk'
        apk_com_versao(caminho, nome, codigo)
        self.assertEqual(self.vip.versao_do_apk(caminho), (codigo, nome))


if __name__ == '__main__':
    unittest.main()
