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
    'firestick', 'fireos', 'aftm', 'aftt', 'afts', 'aftb', 'aftk', 'afth',
    'afte', 'aftn', 'nvidia shield', 'shield android', 'mi box', 'mibox',
    'mi tv', 'mitv', 'mi stick', 'mistick', 'mdz-', 'realme tv', 'izy play',
    'iziplay', 'mecool', 'aquario', 'stv-', 'tv box', 'tvbox', 'box tv',
    'smart tv', 'smarttv', 'apple tv', 'roku', 'matv', 'aosp on', 'adt-',
    'atv', 'projector', 'projetor', 'cinebeam', 'the freestyle', 'xgimi',
    'wanbo', 'byintek', 'magcubic', 'salange', 'yaber', 'vankyo', 'nebula',
    'formovie', 'jmgo', 'dangbei', 'hisense', 'tcl', 'philips tv', 'bravia',
    'aquos', 'hy300', 'h713', 'allwinner', 'sun8i', 'sun50i', 'h313', 'h616',
    'h618', 'droidlogic', 'amlogic', 'meson', 'gxbb', 'gxl', 'gxm', 'g12a',
    'g12b', 's905', 's912', 's922', 'p212', 'p281', 'q201', 'rk3128', 'rk322',
    'rk3318', 'rk3328', 'rk352', 'rk356', 'h96', 'x96', 'x88', 'a95x', 'hk1',
    't95', 'tx2', 'tx3', 'tx6', 'tx9', 'mxq', 'tanix', 'btv', 'htv', 'tigre',
    'vontar', 'transpeed', 'beelink', 'ugoos', 'zidoo', 'minix',
)

MARCAS_MOBILE = (
    'phone', 'celular', 'smartphone', 'tablet', 'sm-', 'moto ', 'moto g',
    'moto e', 'redmi', 'poco', 'galaxy', 'pixel', 'xiaomi', 'realme',
    'infinix', 'tecno',
)

_PROP_ARQUIVOS_PADRAO = (
    '/system/build.prop',
    '/vendor/build.prop',
    '/product/build.prop',
    '/odm/etc/build.prop',
)
_PERM_PASTAS_PADRAO = (
    '/system/etc/permissions',
    '/vendor/etc/permissions',
)
_CHAVES_PROP_APARELHO = (
    'ro.product.model', 'ro.product.vendor.model', 'ro.product.odm.model',
    'ro.product.device', 'ro.product.vendor.device', 'ro.product.board',
    'ro.board.platform', 'ro.hardware', 'ro.product.name',
    'ro.product.manufacturer', 'ro.product.brand',
)
_CARACTERISTICAS_TV = ('tv', 'television', 'tvbox', 'mbox', 'mbx', 'stb', 'leanback')
_PERMISSOES_TV = (
    'android.software.leanback.xml',
    'android.hardware.type.television.xml',
    'com.amazon.feature.television.xml',
)
_PERMISSOES_TOQUE = (
    'android.hardware.touchscreen.xml',
    'handheld_core_hardware.xml',
    'tablet_core_hardware.xml',
)
_CACHE_SISTEMA = {}


def _ler_props_android(arquivos=None):
    """Le build.prop diretamente com open() puro (zero subprocess)."""
    usar_cache = arquivos is None
    if usar_cache and 'props' in _CACHE_SISTEMA:
        return _CACHE_SISTEMA['props']
    props = {}
    for caminho in (arquivos if arquivos is not None else _PROP_ARQUIVOS_PADRAO):
        try:
            if not os.path.isfile(caminho):
                continue
            with open(caminho, 'r', encoding='utf-8', errors='replace') as fh:
                for linha in fh:
                    linha = linha.strip()
                    if not linha or linha.startswith('#') or '=' not in linha:
                        continue
                    chave, valor = linha.split('=', 1)
                    chave = chave.strip().lower()
                    valor = valor.strip()
                    if chave and valor and chave not in props:
                        props[chave] = valor
        except Exception:
            continue
    if usar_cache:
        _CACHE_SISTEMA['props'] = props
    return props


def _sinais_sistema_android(arquivos_prop=None, pastas_perm=None):
    """Inspeciona permissoes e build.prop do Android para TV Stick e TV Box.

    Retorna ``(TV/MOBILE/None, motivo)``. Em host de teste (sem /system Android)
    devolve ``(None, '')`` para nao interferir nos stubs do Kodi.
    """
    pastas = pastas_perm if pastas_perm is not None else _PERM_PASTAS_PADRAO
    pastas_existentes = [p for p in pastas if p and os.path.isdir(p)]
    for pasta in pastas_existentes:
        for arq in _PERMISSOES_TV:
            if os.path.isfile(os.path.join(pasta, arq)):
                return TV, 'permissao de sistema %s' % arq

    props = _ler_props_android(arquivos_prop)
    if props:
        carac = _sem_acento(props.get('ro.build.characteristics', ''))
        tokens_carac = [t.strip() for t in carac.split(',') if t.strip()]
        for tok in tokens_carac:
            if tok in _CARACTERISTICAS_TV:
                return TV, 'ro.build.characteristics=%s' % tok

        if props.get('ro.build.version.fireos'):
            return TV, 'Fire OS detectado (TV Stick/Fire TV)'

        fab = _sem_acento(props.get('ro.product.manufacturer', '') + ' ' +
                          props.get('ro.product.brand', ''))
        modelo = _sem_acento(props.get('ro.product.model', ''))
        if 'amazon' in fab and modelo.startswith('aft'):
            return TV, 'Amazon Fire TV Stick (%s)' % modelo

        resumo_hw = _sem_acento(' '.join(
            props.get(k, '') for k in _CHAVES_PROP_APARELHO if props.get(k)
        ))
        # Verifica marcas de TV Box/Stick ANTES de marcas genericas como xiaomi/realme
        for marca in MARCAS_TV:
            if marca in resumo_hw:
                return TV, 'hardware Android contem %r' % marca
        for marca in MARCAS_MOBILE:
            if marca in resumo_hw:
                return MOBILE, 'hardware Android contem %r' % marca

    # TV Box AOSP sem Leanback e sem tela touch fisica
    if pastas_existentes:
        tem_toque = any(
            os.path.isfile(os.path.join(pasta, arq))
            for pasta in pastas_existentes
            for arq in _PERMISSOES_TOQUE
        )
        if not tem_toque:
            return TV, 'Android sem touchscreen fisico (TV Box/Stick)'

    return None, ''


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
    """(variante, motivo) usando o que o Kodi e o sistema Android informam."""
    if _condicao('System.Platform.Android.TV'):
        return TV, 'System.Platform.Android.TV'
    nome = _sem_acento(_info('System.FriendlyName'))
    for marca in MARCAS_TV:
        if marca in nome:
            return TV, 'nome do aparelho contem %r' % marca
    for marca in MARCAS_MOBILE:
        if marca in nome:
            return MOBILE, 'nome do aparelho contem %r' % marca
    if _condicao('System.Platform.Android') or _condicao('System.Platform.Android.Mobile'):
        sinal_sis, motivo_sis = _sinais_sistema_android()
        if sinal_sis in (TV, MOBILE):
            return sinal_sis, motivo_sis
    if _condicao('System.Platform.Android.Mobile'):
        return MOBILE, 'System.Platform.Android.Mobile'
    try:
        altura = int(float(_info('System.ScreenHeight') or 0))
    except Exception:
        altura = 0
    if altura and altura <= 720 and _condicao('System.Platform.Android'):
        return TV, 'tela de %d linhas (HD/HD Ready)' % altura
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
