"""Testes do Vikings Repo: download no build e registro no primeiro boot.

Cobrem dois pontos que, se falharem, deixam o app sem o add-on de video:

* ``tools/kodi/fetch-vikings-repo.py`` — o zip baixado precisa ter um unico
  add-on ``repository.*`` na raiz, com id igual ao da pasta; e a extracao tem
  de sair em ``DEST/<id>/`` para o ``build-release-apk.py`` recolher;
* ``repository.py`` (dentro do ``service.smarted.bootstrap``) — extrair do
  payload, habilitar por JSON-RPC e pedir ``InstallAddon`` quando o plugin
  estiver ausente.
"""
import importlib.util
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap'

sys.path.insert(0, str(BOOTSTRAP))
try:
    import repository  # noqa: E402  (depende do sys.path acima)
finally:
    sys.path.pop(0)

spec = importlib.util.spec_from_file_location(
    'fetch_vikings', ROOT / 'tools' / 'kodi' / 'fetch-vikings-repo.py')
fetch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch)

ADDON_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<addon id="{id}" version="1.0.2" name="Vikings Repositorio" provider-name="Vikings">
  <extension point="xbmc.addon.repository" name="Vikings">
    <dir minversion="19.0.0">
      <info compressed="false">https://vkodi.net/repo/addons.xml</info>
      <checksum>https://vkodi.net/repo/addons.xml.md5</checksum>
      <datadir zip="true">https://vkodi.net/repo/zips/</datadir>
    </dir>
  </extension>
</addon>
'''


def zip_bytes(addon_id, extra=()):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        z.writestr('%s/addon.xml' % addon_id, ADDON_XML.format(id=addon_id))
        z.writestr('%s/icon.png' % addon_id, b'\x89PNG')
        for nome in extra:
            z.writestr(nome, b'x')
    return buffer.getvalue()


class FetchVikingsTest(unittest.TestCase):
    def test_aceita_zip_com_um_repositorio(self):
        addon_id, arquivos = fetch.abrir_addon_repositorio(zip_bytes('repository.vikings'))
        self.assertEqual(addon_id, 'repository.vikings')
        self.assertIn('addon.xml', arquivos)
        self.assertIn('icon.png', arquivos)

    def test_recusa_zip_de_addon_comum(self):
        with self.assertRaises(SystemExit):
            fetch.abrir_addon_repositorio(zip_bytes('plugin.video.algo'))

    def test_aceita_o_repositorio_do_github_do_time_vikings(self):
        # o zip oficial da pasta ``vkkodi.repo`` termina em ``.repo``, nao em
        # ``repository.`` — os dois formatos sao repositorio do Kodi
        addon_id, arquivos = fetch.abrir_addon_repositorio(zip_bytes('vkkodi.repo'))
        self.assertEqual(addon_id, 'vkkodi.repo')
        self.assertIn('addon.xml', arquivos)

    def test_url_principal_e_do_github(self):
        self.assertIn('github.com/vikingsbuild/vikings.repo', fetch.VIKINGS_GITHUB)
        self.assertEqual(fetch.URLS_PADRAO[0], fetch.VIKINGS_GITHUB)

    def test_recusa_pasta_divergente_do_id(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as z:
            z.writestr('outra-pasta/addon.xml', ADDON_XML.format(id='repository.vikings'))
        with self.assertRaises(SystemExit):
            fetch.abrir_addon_repositorio(buffer.getvalue())

    def test_extrai_no_formato_do_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / 'extra'
            addon_id, arquivos = fetch.abrir_addon_repositorio(
                zip_bytes('repository.vikings'))
            pasta = fetch.extrair(destino, addon_id, arquivos)
            self.assertEqual(pasta, destino / 'repository.vikings')
            self.assertTrue(addon_id, (pasta / 'addon.xml').is_file())
            # o build-release-apk.py exige id == nome da pasta
            self.assertEqual(pasta.name, addon_id)

    def test_lista_as_fontes_do_addon(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / 'extra'
            addon_id, arquivos = fetch.abrir_addon_repositorio(
                zip_bytes('repository.vikings'))
            pasta = fetch.extrair(destino, addon_id, arquivos)
            texto = (pasta / 'addon.xml').read_text()
            self.assertIn('xbmc.addon.repository', texto)
            self.assertIn('vkodi.net/repo', texto)


class BootstrapRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / '.kodi'
        self.addons = self.home / 'addons'
        self.addons.mkdir(parents=True)
        self.payload = Path(self.tmp.name) / 'payload'
        self.payload.mkdir()

    def escrever_payload(self, addon_id='repository.vikings'):
        nome = addon_id + '.zip' if addon_id.startswith('repository.') else addon_id + '-3.00.zip'
        (self.payload / nome).write_bytes(zip_bytes(addon_id))

    def test_extrai_repositorio_do_payload(self):
        self.escrever_payload()
        log = []
        instalados = repository.extrair_payload(str(self.home), str(self.payload), log.append)
        self.assertEqual(instalados, ['repository.vikings'])
        self.assertTrue((self.addons / 'repository.vikings' / 'addon.xml').is_file())
        self.assertTrue(repository.instalado(home=str(self.home)))
        self.assertTrue(any('INSTALADO' in linha for linha in log))

    def test_extrai_o_vkkodi_repo_do_github(self):
        self.escrever_payload('vkkodi.repo')
        instalados = repository.extrair_payload(str(self.home), str(self.payload), None)
        self.assertEqual(instalados, ['vkkodi.repo'])
        self.assertIn('vkkodi.repo', repository.repos_instalados([str(self.addons)]))

    def test_sem_payload_nao_inventa_repositorio(self):
        log = []
        self.assertEqual(repository.extrair_payload(str(self.home), str(self.payload), log.append), [])
        self.assertFalse(repository.instalado(home=str(self.home)))

    def test_habilitar_usa_jsonrpc(self):
        chamadas = []

        def jsonrpc(metodo, params):
            chamadas.append((metodo, params))
            return {'result': 'OK'}

        falhas = repository.habilitar(['repository.vikings'], jsonrpc, None)
        self.assertEqual(falhas, [])
        self.assertEqual(chamadas[0][0], 'Addons.SetAddonEnabled')
        self.assertEqual(chamadas[0][1]['addonid'], 'repository.vikings')

    def test_ensure_repository_instala_e_habilita(self):
        self.escrever_payload()
        executados = []

        def jsonrpc(metodo, params=None):
            if metodo == 'Addons.GetAddonDetails':
                return {'result': {'addon': {'addonid': repository.PLUGIN_ID}}}
            return {'result': 'OK'}

        relatorio = repository.ensure_repository(
            str(self.home), str(self.payload), [],
            jsonrpc=jsonrpc, execute=executados.append, log=None)
        self.assertTrue(relatorio['instalado'])
        self.assertEqual(relatorio['habilitado'], ['repository.vikings'])
        self.assertTrue(relatorio['plugin'])
        self.assertIn('InstallAddon(%s)' % repository.PLUGIN_ID, executados)

    def test_plugin_ja_instalado_nao_e_reinstalado(self):
        self.escrever_payload()
        (self.addons / repository.PLUGIN_ID).mkdir()
        (self.addons / repository.PLUGIN_ID / 'addon.xml').write_text('<addon id="x"/>')
        executados = []
        relatorio = repository.ensure_repository(
            str(self.home), str(self.payload), [],
            jsonrpc=lambda metodo, params=None: {'result': 'OK'},
            execute=executados.append)
        self.assertTrue(relatorio['plugin'])
        self.assertNotIn('InstallAddon(%s)' % repository.PLUGIN_ID, executados)

    def test_repositorio_de_sistema_conta_como_instalado(self):
        sistema = Path(self.tmp.name) / 'sistema'
        (sistema / 'vkkodi.repo').mkdir(parents=True)
        (sistema / 'vkkodi.repo' / 'addon.xml').write_text('<addon id="vkkodi.repo"/>')
        self.assertTrue(repository.instalado([str(sistema)], home=str(self.home)))


class PayloadPacotesTest(unittest.TestCase):
    """O zip do add-on de video embarcado no build vira fonte de reparo."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.payload = Path(self.tmp.name) / 'payload'
        self.payload.mkdir()
        self.packages = Path(self.tmp.name) / '.kodi' / 'addons' / 'packages'

    def test_importa_zip_do_addon_de_video(self):
        (self.payload / 'plugin.video.BrazucaPlay.Matrix-2.1.4.zip').write_bytes(
            zip_bytes('plugin.video.BrazucaPlay.Matrix'))
        log = []
        copiados = repository.repair.importar_pacotes_do_payload(
            str(self.payload), str(self.packages), log.append)
        self.assertEqual(copiados, ['plugin.video.BrazucaPlay.Matrix'])
        self.assertTrue((self.packages / 'plugin.video.BrazucaPlay.Matrix-2.1.4.zip').is_file())
        self.assertTrue(any('PACOTE' in linha for linha in log))

    def test_ignora_zip_sem_addon_xml(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as z:
            z.writestr('cloudrequest/requests_toolbelt/__init__.py', b'x')
        (self.payload / 'cloudrequest-py3.zip').write_bytes(buffer.getvalue())
        self.assertEqual(repository.repair.importar_pacotes_do_payload(
            str(self.payload), str(self.packages), None), [])

    def test_ignora_nome_que_nao_combina_com_o_id(self):
        (self.payload / 'outro.addon-1.0.zip').write_bytes(zip_bytes('plugin.video.BrazucaPlay.Matrix'))
        self.assertEqual(repository.repair.importar_pacotes_do_payload(
            str(self.payload), str(self.packages), None), [])

    def test_nao_copia_repositorio_para_a_pasta_de_pacotes(self):
        (self.payload / 'repository.vikings.zip').write_bytes(zip_bytes('repository.vikings'))
        self.assertEqual(repository.repair.importar_pacotes_do_payload(
            str(self.payload), str(self.packages), None), [])


if __name__ == '__main__':
    unittest.main()
