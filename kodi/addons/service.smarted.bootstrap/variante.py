# -*- coding: utf-8 -*-
"""Qual versao do SMARTEDTV esta rodando: MOBILE (celular) ou TV (Android TV).

O app e o MESMO codigo; o que muda entre as duas versoes e um punhado de
decisoes. Este modulo e a UNICA fonte dessa verdade - nada de espalhar
``if tv`` pelo projeto:

``mobile``  celular/tablet, anuncia pelo AdMob que ja existe no APK.
``tv``      Android TV, projetor com Android TV, stick e TV box compativel:
            usa o anuncio de video (VAST) tocado pelo player do Kodi
            (ver ``ads_vast.py``).

Com o APK UNIVERSAL nao ha marcador embutido: a variante e decidida pelo
aparelho (``variante_do_aparelho``). As duas variantes consultam a MESMA pasta
do Dropbox (``SMARTEDTV UNIVERSAL``) e o mesmo arquivo ``SMARTEDTV.apk``.

Como o aparelho e reconhecido
-----------------------------
O pacote deste APK e o sinal mais forte e nao depende de idioma/nome do
aparelho. O ``tools/kodi/atualizar-apk-v17.py`` grava
``assets/smartedtv-variante.txt`` (``tv`` ou ``mobile``) dentro do APK; este
modulo le esse arquivo primeiro. Quando o arquivo nao existe (base antiga,
teste unitario, instalacao antiga) cai para o que o Kodi sabe do aparelho:

* ``System.Platform.Android.TV``  -> TV (o sinal oficial do leanback);
* ``System.Platform.Android.Mobile`` -> mobile;
* nome do aparelho com marcas conhecidas de TV/box/stick/projetor;
* por ultimo, altura de tela <= 720 linhas em Android -> TV.

Em qualquer duvida a resposta e ``mobile``: e a versao aprovada e funcionando,
entao um erro de deteccao nunca troca a experiencia de quem ja usa.
"""
from __future__ import absolute_import, unicode_literals

import os


def _xbmc():
    """Modulo ``xbmc`` lido NA HORA da chamada.

    Guardar a referencia do import deixava a decisao congelada no primeiro
    modulo que importou ``variante`` neste processo (nos testes, um stub de
    aparelho antigo). Em producao o ``xbmc`` do Kodi e sempre o mesmo, entao
    resolver por chamada nao custa nada.
    """
    import xbmc
    return xbmc

MOBILE = 'mobile'
TV = 'tv'

# Nome do arquivo que o build grava dentro do APK.
MARCADOR = 'smartedtv-variante.txt'

# Pasta do Dropbox: UMA so, para o APK universal.
#
# A separacao em SMARTEDTV-MOBILE / SMARTEDTV-ON existiu enquanto havia dois
# arquivos publicados. Com um unico APK (rodada de finalizacao) ha uma pasta e
# um nome de arquivo so - as duas constantes ficam apontando para o mesmo
# lugar para nao quebrar quem ja as le.
PASTA_UNIVERSAL = 'SMARTEDTV UNIVERSAL'
PASTA_MOBILE = PASTA_UNIVERSAL
PASTA_TV = PASTA_UNIVERSAL

# Pacotes das duas versoes.
PACOTE_MOBILE = 'smartedtv.full'
PACOTE_TV = 'smartedtv.tv'

# Marcas de aparelho de sala (o Kodi expoe o nome comercial em
# ``System.FriendlyName``; a comparacao e sem acento e em minusculas).
MARCAS_TV = (
    'android tv', 'google tv', 'chromecast', 'fire tv', 'firetv', 'fire stick',
    'firestick', 'nvidia shield', 'shield android', 'mi box', 'mibox',
    'mi tv', 'mitv', 'mi stick', 'tv box', 'tvbox', 'box tv', 'smart tv',
    'smarttv', 'apple tv', 'roku', 'matv', 'aosp on', 'adt-', 'atv',
    'projector', 'projetor', 'cinebeam', 'the freestyle', 'xgimi', 'wanbo',
    'byintek', 'magcubic', 'salange', 'yaber', 'vankyo', 'nebula', 'formovie',
    'jmgo', 'dangbei', 'hisense', 'tcl', 'philips tv', 'bravia', 'aquos',
)


def _condicao(consulta):
    try:
        return bool(_xbmc().getCondVisibility(consulta))
    except Exception:
        return False


def _info(rotulo):
    try:
        return (_xbmc().getInfoLabel(rotulo) or '').strip()
    except Exception:
        return ''


def _sem_acento(texto):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFKD', texto or '')
                   if not unicodedata.combining(c)).lower()


def _caminho_marcador():
    """``assets/smartedtv-variante.txt`` dentro do APK (special://xbmc).

    O APK entrega o arquivo no diretorio de assets do Kodi; o perfil semeado
    tambem pode copia-lo para ``userdata`` (``smartedtv-variante.txt``), o que
    continua valendo quando o assets nao esta acessivel pelo Python.
    """
    for base in ('special://xbmc', 'special://home', 'special://userdata',
                 'special://masterprofile'):
        try:
            import xbmcvfs
            caminho = xbmcvfs.translatePath(os.path.join(base, 'assets',
                                                         MARCADOR))
        except Exception:
            continue
        if caminho and os.path.isfile(caminho):
            return caminho
    return None


def variante_do_arquivo():
    """Variante gravada pelo build, ou None quando o arquivo nao existe."""
    caminho = _caminho_marcador()
    if not caminho:
        return None
    try:
        with open(caminho) as arquivo:
            texto = (arquivo.read() or '').strip().lower()
    except Exception:
        return None
    for valor in (TV, MOBILE):
        if texto.startswith(valor):
            return valor
    return None


def variante_do_aparelho():
    """(variante, motivo) usando somente o que o Kodi informa do aparelho."""
    if _condicao('System.Platform.Android.TV'):
        return TV, 'System.Platform.Android.TV'
    nome = _sem_acento(_info('System.FriendlyName'))
    for marca in MARCAS_TV:
        if marca in nome:
            return TV, 'nome do aparelho contem %r' % marca
    try:
        altura = int(float(_info('System.ScreenHeight') or 0))
    except Exception:
        altura = 0
    if altura and altura <= 720 and _condicao('System.Platform.Android'):
        return TV, 'tela de %d linhas (HD/HD Ready)' % altura
    # ``Android.Mobile`` fica por ULTIMO: em Android TV projetor/box o Kodi
    # tambem responde verdadeiro nessa condicao em algumas builds, e usar esse
    # sinal antes dos outros faria a TV ser tratada como celular.
    if _condicao('System.Platform.Android.Mobile'):
        return MOBILE, 'System.Platform.Android.Mobile'
    return MOBILE, 'sem sinal de TV; mantendo a versao mobile'


def variante():
    """``tv`` ou ``mobile``. Nunca levanta excecao."""
    do_arquivo = variante_do_arquivo()
    if do_arquivo:
        return do_arquivo
    try:
        return variante_do_aparelho()[0]
    except Exception:
        return MOBILE


def motivo():
    """Texto curto para o log: de onde saiu a decisao."""
    do_arquivo = variante_do_arquivo()
    if do_arquivo:
        return 'marcador do APK (%s)' % MARCADOR
    try:
        return variante_do_aparelho()[1]
    except Exception:
        return 'sem informacao; assumindo mobile'


def e_tv():
    return variante() == TV


def e_mobile():
    return variante() == MOBILE


def pacote():
    return PACOTE_TV if e_tv() else PACOTE_MOBILE


def pasta_dropbox():
    """Pasta do Dropbox desta versao (o contrato de atualizacao)."""
    return PASTA_TV if e_tv() else PASTA_MOBILE


def nome_do_app():
    return 'SMARTEDTV TV' if e_tv() else 'SMARTEDTV'


def resumo():
    """Linha unica para o log de boot (diagnostico sem adb)."""
    return 'variante=%s (%s), pasta=%s, pacote=%s' % (
        variante(), motivo(), pasta_dropbox(), pacote())
