# -*- coding: utf-8 -*-
"""Finalizacao: UM APK universal (sem arquivo separado de TV).

O que estes testes protegem, e por que cada um importa:

1. a receita de build monta o APK UMA vez - se alguem reintroduzir a segunda
   montagem, o arquivo de TV volta a ser gerado e publicado;
2. o APK NAO leva `assets/smartedtv-variante.txt` - esse marcador forca a
   variante e faria a TV se comportar como celular (AdMob, que nao funciona em
   Android TV). Sem o marcador, quem decide e o aparelho (`e_tv()`);
3. o workflow publica SO `SMARTEDTV-universal.apk` e apaga qualquer
   `SMARTEDTV-tv.apk` que tenha sobrado;
4. a pasta do Dropbox e uma so (`SMARTEDTV UNIVERSAL`) com `SMARTEDTV.apk`.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'smartedtv' / 'release' / 'build.sh'
SMOKE = ROOT / 'smartedtv' / 'release' / 'install-smoke.sh'
FLUXO = ROOT / '.github' / 'workflows' / 'smartedtv-universal.yml'
VIP = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap' / 'vip.py'
VARIANTE = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap' / 'variante.py'


class BuildUnicoTest(unittest.TestCase):
    def setUp(self):
        self.build = BUILD.read_text(encoding='utf-8')

    def test_monta_uma_vez_so(self):
        chamadas = re.findall(r'^montar\s+\S+', self.build, re.M)
        self.assertEqual(len(chamadas), 1, chamadas)

    def test_nao_gera_o_apk_de_tv(self):
        self.assertNotIn('SMARTEDTV-tv.apk', self.build)
        self.assertNotIn('final_tv', self.build)

    def test_nao_grava_marcador_de_variante(self):
        # o marcador so pode ser CITADO na trava que falha se ele existir
        self.assertNotIn('--variante "', self.build)
        self.assertNotIn("--variante mobile", self.build)
        self.assertNotIn("--variante tv", self.build)
        self.assertIn('smartedtv-variante.txt', self.build)  # a trava

    def test_trava_o_marcador_no_apk_assinado(self):
        self.assertIn('tem marcador de variante', self.build)

    def test_mantem_a_receita_que_funcionava(self):
        for etapa in ('atualizar-apk-v17.py', 'ajustar-versao-apk.py',
                      'align-apk.py', 'apksigner" sign',
                      'smartedtv/release/verify.py',
                      'simular-boot-tela-entrada.py'):
            self.assertIn(etapa, self.build, etapa)


class PublicacaoUnicaTest(unittest.TestCase):
    def setUp(self):
        self.fluxo = FLUXO.read_text(encoding='utf-8')

    def test_publica_so_o_universal(self):
        criacao = [linha for linha in self.fluxo.splitlines()
                   if 'gh release create' in linha]
        self.assertEqual(len(criacao), 1, criacao)
        self.assertIn('"$apk"', criacao[0])
        self.assertNotIn('apk_tv', criacao[0])

    def test_nao_publica_arquivo_de_tv(self):
        self.assertNotIn('apk_tv=build', self.fluxo)
        self.assertIn('rm -f build/universal/SMARTEDTV-tv.apk', self.fluxo)

    def test_notas_nao_prometem_dois_apks(self):
        self.assertNotIn('dois APKs', self.fluxo)
        self.assertNotIn('SHA-256 (TV)', self.fluxo)

    def test_smoke_instala_um_apk(self):
        smoke = SMOKE.read_text(encoding='utf-8')
        instalacoes = re.findall(r'^install .*SMARTEDTV-\S+', smoke, re.M)
        self.assertEqual(instalacoes, ['install -r "$work/SMARTEDTV-universal.apk"'],
                         instalacoes)


class DropboxUnicoTest(unittest.TestCase):
    def test_pasta_universal(self):
        texto = VIP.read_text(encoding='utf-8')
        self.assertIn("PASTA_NOME_UNIVERSAL = 'SMARTEDTV UNIVERSAL'", texto)
        self.assertIn('/scl/fo/0f1ux2r4p8mooqyeswy0y/', texto)

    def test_nome_do_arquivo_no_dropbox(self):
        self.assertIn("APK_NOME = 'SMARTEDTV.apk'",
                      VIP.read_text(encoding='utf-8'))

    def test_variante_aponta_para_a_mesma_pasta(self):
        texto = VARIANTE.read_text(encoding='utf-8')
        self.assertIn("PASTA_UNIVERSAL = 'SMARTEDTV UNIVERSAL'", texto)
        self.assertNotIn("PASTA_MOBILE = 'SMARTEDTV-MOBILE'", texto)
        self.assertNotIn("PASTA_TV = 'SMARTEDTV-ON'", texto)


class AtualizacaoNoDropboxTest(unittest.TestCase):
    """O APK universal nao tem marcador: o download nao pode recusa-lo."""

    def test_apk_sem_marcador_e_aceito(self):
        fonte = VIP.read_text(encoding='utf-8')
        trecho = fonte[fonte.index('def apk_serve_para_esta_versao'):
                       fonte.index('def _apk_mais_novo_que_o_instalado')]
        self.assertIn('APK universal', trecho)
        # a recusa por "sem marcador" na TV nao pode voltar
        self.assertNotIn('recusado na versao', trecho)


class ReservaNoGithubTest(unittest.TestCase):
    """Um APK so: a release do GitHub serve de reserva para os dois aparelhos."""

    def test_github_nao_e_bloqueado_na_tv(self):
        fonte = VIP.read_text(encoding='utf-8')
        trecho = fonte[fonte.index('if APK_GITHUB'):fonte.index("motivo = '; '.join")]
        self.assertNotIn('not eh_tv()', trecho)
        self.assertIn('APK UNIVERSAL', trecho)


class DeteccaoPreservadaTest(unittest.TestCase):
    """O APK universal depende do e_tv(): ele nao pode ter sido simplificado."""

    def test_e_tv_continua_decidindo_pelo_aparelho(self):
        texto = VARIANTE.read_text(encoding='utf-8')
        self.assertIn('def e_tv()', texto)
        self.assertIn('System.Platform.Android.TV', texto)
        self.assertIn('MARCAS_TV', texto)

    def test_sem_marcador_a_deteccao_do_aparelho_manda(self):
        texto = VARIANTE.read_text(encoding='utf-8')
        trecho = texto[texto.index('def variante():'):texto.index('def motivo():')]
        self.assertIn('variante_do_aparelho', trecho)


if __name__ == '__main__':
    unittest.main()
