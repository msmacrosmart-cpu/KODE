#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tira do perfil EMBARCADO os addons de terceiros que o Kodi inicia sozinho.

CAUSA (medida no emulador de projetor)
--------------------------------------
O `kodi.log` do projetor mostrava, em todo boot:

    [COLOR limegreen][B]Open[/B][/COLOR]Wizard: [First Run] Skipping Save Data
    [plugin.video.youtube] ModuleNotFoundError: youtube_plugin.kodion.exceptions

O Kodi inicia os addons de SERVICO de tudo que esta instalado durante o
`CServiceManager::InitStageTwo`, ANTES de qualquer Python do app rodar (a
limpeza do service.py acontece ~12 s depois). Limpar depois e tarde: o erro na
tela ja apareceu. A origem e o perfil que o APK instala no primeiro arranque,
que trazia `plugin.video.youtube`, `plugin.program.openwizard`,
`plugin.audio.mp3streams`, `service.subtitles.legendei` e cinco repositorios de
terceiros (heranca da base do Brazuca Play).

O QUE ESTE SCRIPT FAZ
---------------------
1. tira esses addons de `assets/smarted/profile/addons/`;
2. refaz `assets/smarted/profile-manifest.txt`;
3. grava o novo pin de 64 hex no Java do bootstrap
   (`ProfileDirectoryBootstrap.java`), que e recompilado logo depois por
   `tools/kodi/recompilar-bootstrap.py`.

POR QUE O DEX DO APP NAO E PATCHADO
-----------------------------------
O pin mora no dex. Trocar bytes no `classes4.dex` (codigo do app) deixa o ART
recusar o arquivo. Experimento controlado, tres variaveis, no emulador:

    A = perfil limpo + pin trocado no classes4 -> app MORRE
        java.lang.NoClassDefFoundError: Failed resolution of: Lsmartedtv/full/XBMCJsonRPC
        Caused by: java.lang.ClassNotFoundException: smartedtv.full.XBMCJsonRPC
    D = perfil limpo + classes4 intacto        -> app vivo, Home carrega
    C = tudo intacto                           -> app vivo

Por isso o pin muda por COMPILACAO do bootstrap (dex separado, classes3.dex, que
`home-carrossel-emulator.yml` tambem recompila) e nunca por edicao de bytes.
"""
from __future__ import print_function

import hashlib
import io
import os
import re
import sys
import zipfile

PERFIL = 'assets/smarted/profile/'
MANIFESTO = 'assets/smarted/profile-manifest.txt'
DEX_DO_BOOTSTRAP = 'classes3.dex'
ORIGEM_DO_PIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'android', 'src', 'org', 'smartedtv', 'bootstrap',
                             'ProfileDirectoryBootstrap.java')
_HEX64 = re.compile(r'\b[0-9a-f]{64}\b')

# Addons de terceiros que vieram no perfil embarcado (evidencia: kodi.log do
# projetor e Addons33.db do perfil). Nenhum e usado pelo app.
ADDONS_DE_TERCEIROS = (
    'One.repo',
    'plugin.audio.mp3streams',
    'plugin.program.openwizard',
    'plugin.program.openwizard2',
    'plugin.program.super.favourites',
    'plugin.video.openwizard',
    'plugin.video.youtube',
    'repository.alado.tv',
    'repository.elementumorg',
    'repository.nostr-oneplay',
    'repository.openwizard',
    'repository.redwizard',
    'repository.resolveurl',
    'repository.streamxtv.matrix',
    'script.module.bingie',
    'service.subtitles.legendei',
    'skin.bingie',
    'vkkodi.repo',
)

# Addons que o motor do Kodi exige: NUNCA saem (sem eles o CAddonMgr nao inicia
# e a Home fica sem dados).
PROTEGIDOS = (
    'audioencoder.kodi.builtin.',
    'game.controller.',
    'inputstream.',
    'kodi.binary.',
    'kodi.resource',
    'metadata.',
    'plugin.video.BrazucaPlay.Matrix',
    'plugin.video.smarted',
    'repository.xbmc.org',
    'resource.',
    'screensaver.xbmc.builtin.',
    'script.module.',
    'script.smartedtv.',
    'service.smarted.',
    'skin.',
    'vfs.',
    'webinterface.',
    'xbmc.',
)


def addons_do_perfil(nomes):
    achados = set()
    for nome in nomes:
        if not nome.startswith(PERFIL + 'addons/'):
            continue
        partes = nome[len(PERFIL):].split('/')
        if len(partes) > 2 and partes[1]:
            achados.add(partes[1])
    return achados


def protegido(addon):
    return any(addon == p or addon.startswith(p) for p in PROTEGIDOS)


def planejar(apk):
    """(arquivos_a_remover, addons_removidos, addons_mantidos)."""
    with zipfile.ZipFile(apk) as z:
        nomes = set(z.namelist())
    if MANIFESTO not in nomes:
        raise SystemExit('APK sem perfil embarcado (%s)' % MANIFESTO)
    addons = addons_do_perfil(nomes)
    remover = set(a for a in addons if a in ADDONS_DE_TERCEIROS and not protegido(a))
    arquivos = set()
    for nome in nomes:
        if not nome.startswith(PERFIL + 'addons/'):
            continue
        partes = nome[len(PERFIL):].split('/')
        if len(partes) > 1 and partes[1] in remover:
            arquivos.add(nome)
    return arquivos, remover, sorted(addons - remover)


def manifesto_de(arquivos):
    """Manifesto no formato do bootstrap: sha256\\tbytes\\tcaminho."""
    linhas = []
    for caminho in sorted(arquivos):
        if not caminho:
            continue
        dados = arquivos[caminho]
        linhas.append('%s\t%d\t%s' % (hashlib.sha256(dados).hexdigest(),
                                      len(dados), caminho))
    return ('\n'.join(linhas) + '\n').encode('utf-8')


def pin_publicado(origem=None):
    """Pin de 64 hex que o bootstrap confere (lido do Java)."""
    caminho = origem or ORIGEM_DO_PIN
    try:
        with io.open(caminho, encoding='utf-8') as arquivo:
            achados = _HEX64.findall(arquivo.read())
    except IOError:
        return None
    return achados[0] if achados else None


def gravar_pin_na_origem(pin_novo, origem=None):
    caminho = origem or ORIGEM_DO_PIN
    antigo = pin_publicado(caminho)
    if antigo == pin_novo:
        return False
    with io.open(caminho, encoding='utf-8') as arquivo:
        texto = arquivo.read()
    if antigo is None or antigo not in texto:
        raise SystemExit('pin %s nao esta em %s' % (antigo, caminho))
    with io.open(caminho, 'w', encoding='utf-8') as arquivo:
        arquivo.write(texto.replace(antigo, pin_novo))
    return True


def pin_do_dex(apk, dex=DEX_DO_BOOTSTRAP):
    """Pin lido do dex do bootstrap dentro do APK (fonte da verdade do aparelho)."""
    with zipfile.ZipFile(apk) as z:
        if dex not in z.namelist():
            return None
        return _pin_no_texto(z.read(dex).decode('latin-1'))


def _pin_no_texto(texto):
    achados = set(_HEX64.findall(texto))
    return achados.pop() if len(achados) == 1 else None


def executar(apk_entrada, apk_saida, origem=None, escrever_origem=True):
    """Remove os addons de terceiros do perfil e atualiza o pin do bootstrap."""
    arquivos, removidos, mantidos = planejar(apk_entrada)
    with zipfile.ZipFile(apk_entrada) as z:
        nomes = z.namelist()
        perfil_novo = {}
        for nome in nomes:
            if not nome.startswith(PERFIL) or nome == MANIFESTO or nome in arquivos:
                continue
            perfil_novo[nome[len(PERFIL):]] = z.read(nome)
        manifesto = manifesto_de(perfil_novo)
        with zipfile.ZipFile(apk_saida, 'w', allowZip64=True) as saida:
            for item in z.infolist():
                if item.is_dir() or item.filename in arquivos:
                    continue
                dados = manifesto if item.filename == MANIFESTO else z.read(item)
                info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                info.compress_type = item.compress_type
                info.external_attr = item.external_attr
                info.comment = item.comment
                saida.writestr(info, dados)
    pin = hashlib.sha256(manifesto).hexdigest()
    mudou = False
    if escrever_origem:
        mudou = gravar_pin_na_origem(pin, origem)
    return {
        'removidos': sorted(removidos),
        'mantidos': mantidos,
        'arquivos_removidos': len(arquivos),
        'pin': pin,
        'pin_atualizado_na_origem': mudou,
    }


def conferir(apk, origem=None):
    """APK final: perfil sem terceiro, manifesto batendo e dex com o pin certo."""
    problemas = []
    with zipfile.ZipFile(apk) as z:
        nomes = set(z.namelist())
        if MANIFESTO not in nomes:
            raise SystemExit('sem %s' % MANIFESTO)
        manifesto = z.read(MANIFESTO)
        pin_manifesto = hashlib.sha256(manifesto).hexdigest()
        pin_dex = _pin_no_texto(z.read(DEX_DO_BOOTSTRAP).decode('latin-1')
                                if DEX_DO_BOOTSTRAP in nomes else '')
        if pin_dex is None:
            problemas.append('pin nao encontrado no %s' % DEX_DO_BOOTSTRAP)
        elif pin_dex != pin_manifesto:
            problemas.append('pin do dex (%s) != sha256 do manifesto (%s)'
                             % (pin_dex, pin_manifesto))
        esperado = pin_publicado(origem)
        if esperado and esperado != pin_manifesto:
            problemas.append('Java do bootstrap com pin %s' % esperado)
        sobrando = sorted(a for a in addons_do_perfil(nomes) if a in ADDONS_DE_TERCEIROS)
        if sobrando:
            problemas.append('addon de terceiro no perfil: %s' % ', '.join(sobrando))
        for linha in manifesto.decode('utf-8').splitlines():
            if not linha.strip():
                continue
            partes = linha.split('\t')
            if len(partes) != 3:
                problemas.append('linha invalida no manifesto: %r' % linha[:40])
                continue
            sha, tamanho, caminho = partes
            completo = PERFIL + caminho
            if completo not in nomes:
                problemas.append('manifesto cita arquivo ausente: %s' % caminho)
                continue
            dados = z.read(completo)
            if hashlib.sha256(dados).hexdigest() != sha or str(len(dados)) != tamanho:
                problemas.append('arquivo nao bate com o manifesto: %s' % caminho)
    if problemas:
        raise SystemExit('perfil embarcado: ' + '; '.join(problemas))
    return True


def main(argv):
    if len(argv) >= 3 and argv[1] == '--conferir':
        conferir(argv[2])
        print('perfil embarcado conferido: sem addon de terceiro, manifesto e pin '
              'do dex batendo')
        return 0
    if len(argv) < 3:
        print(__doc__)
        return 2
    resultado = executar(argv[1], argv[2])
    print('addons de terceiros retirados do perfil: %s'
          % (', '.join(resultado['removidos']) or 'nenhum'))
    print('addons que ficam no perfil (%d): %s'
          % (len(resultado['mantidos']), ', '.join(resultado['mantidos'])))
    print('arquivos removidos: %d' % resultado['arquivos_removidos'])
    print('pin novo do perfil: %s' % resultado['pin'])
    if resultado['pin_atualizado_na_origem']:
        print('pin gravado no bootstrap Java (recompilar-bootstrap.py gera o dex)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
