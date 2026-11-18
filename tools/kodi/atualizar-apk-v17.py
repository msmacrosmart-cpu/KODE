#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Atualiza um APK SMARTEDTV ja publicado sem recompilar o Kodi.

Usado pelo pipeline rapido da v17: pega o APK universal da v16 (as duas ABIs
``arm64-v8a`` e ``armeabi-v7a`` ja estao assinadas no arquivo) e troca SOMENTE:

* ``assets/addons/script.smartedtv.welcome/`` -> versao do repositorio;
* ``service.smarted.bootstrap/{service,menu_smarted,performance,vip,smart_ads}.py``
  -> correcoes de tela preta, foco, projetor e update;
* ``assets/system/keymaps/zzz-smartedtv-voltar.xml`` -> keymap do repositorio
  (se existir);
* ``Startup.xml`` de TODAS as skins -> disparo da tela de entrada (o APK da
  v16 ainda tinha ``skin.novatv`` com o ``ReplaceWindow`` antigo).

Perfil semeado, banco de addons, natives libs (as duas ABIs), manifesto, fontes e
demais arquivos ficam byte a byte iguais. Assinatura antiga e removida; o
workflow assina de novo com a mesma chave.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDON_ID = 'script.smartedtv.welcome'
ADDON_DIR = ROOT / 'kodi' / 'addons' / ADDON_ID
ADDON_PREFIX = 'assets/addons/%s/' % ADDON_ID
SERVICO = 'assets/addons/service.smarted.bootstrap/'
MODULOS = ('service.py', 'menu_smarted.py', 'performance.py', 'vip.py',
           'smart_ads.py', 'ad_return.py', 'smarted_release.py', 'check.py', 'addon.xml')
KEYMAP_ORIGEM = ROOT / 'kodi' / 'keymaps' / 'smartedtv-voltar.xml'
KEYMAP_DESTINO = 'assets/system/keymaps/zzz-smartedtv-voltar.xml'
# O *ID embarcado* não é a origem: o monólito copia a Clássica para skin.novatv.
# A skin homônima da árvore Kodi usa outro vocabulário de IDs/fontes/texturas.
SKINS = ('skin.novatv', 'skin.smartedtv.classic')
SKIN_PREFIX = tuple('assets/addons/%s/' % skin for skin in SKINS)
CLASSICA = ROOT / 'kodi/skin.estilo.personalizado/xml'
SKIN_ARQUIVOS = {
    'assets/addons/%s/xml/%s' % (skin, nome): CLASSICA / nome
    for skin in SKINS
    for nome in ('Home.xml',)
}
SIG = re.compile(r'^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$', re.I)
STARTUP = re.compile(r'assets/addons/([^/]+)/xml/Startup\.xml$')
EXIGIDOS = (
    'AndroidManifest.xml',
    'classes.dex',
    'assets/system/addon-manifest.xml',
    'assets/addons/%s/default.py' % ADDON_ID,
    'lib/arm64-v8a/libkodi.so',
    'lib/armeabi-v7a/libkodi.so',
)


def dbg(msg):
    print('[V17] %s' % msg, flush=True)


def arquivos_do_addon():
    arquivos = {}
    for caminho in sorted(ADDON_DIR.rglob('*')):
        if not caminho.is_file() or '__pycache__' in caminho.parts or caminho.suffix == '.pyc':
            continue
        arquivos[ADDON_PREFIX + caminho.relative_to(ADDON_DIR).as_posix()] = caminho.read_bytes()
    for rel in ('addon.xml', 'default.py',
                'resources/skins/Default/1080i/DialogWelcome.xml',
                'resources/skins/Default/1080i/DialogWelcomeTV.xml',
                'resources/skins/Default/media/bg.png'):
        if ADDON_PREFIX + rel not in arquivos:
            raise SystemExit('addon incompleto: falta %s' % rel)
    return arquivos


def arquivos_do_servico():
    extras = {}
    for nome in MODULOS:
        caminho = ROOT / 'kodi' / 'addons' / 'service.smarted.bootstrap' / nome
        if not caminho.is_file():
            raise SystemExit('modulo do servico ausente: %s' % caminho)
        extras[SERVICO + nome] = caminho.read_bytes()
    if KEYMAP_ORIGEM.is_file():
        extras[KEYMAP_DESTINO] = KEYMAP_ORIGEM.read_bytes()
    return extras


STARTUP_ONLOAD = ('<onload>AlarmClock(smartedtv_entrada,'
                  'RunScript(script.smartedtv.welcome),00:00:00,silent)</onload>'
                  '\n\t<onload>RunScript(script.smartedtv.welcome,seguro=1)'
                  '</onload>'
                  '\n\t<onload>AlarmClock(smartedtv_home_seguro,'
                  'ActivateWindow(Home),00:00:30,silent)</onload>')


def patch_startup(dados):
    """Troca o salto direto para a Home pelo disparo da tela, em qualquer skin.

    O APK da v16 tinha skin.estuary ja corrigida, mas skin.novatv ainda com o
    ``ReplaceWindow($INFO[System.StartupWindow])`` antigo. O simulador (e o
    Kodi) abre a tela por todas as skins de Startup; por isso a correcao e
    aplicada em TODAS, nao so na skin ativa.
    """
    texto = dados.decode('utf-8')
    if 'smartedtv_entrada' in texto:
        if 'smartedtv_home_seguro' in texto:
            return dados
        novo = texto.replace('</window>',
                             '\t<onload>AlarmClock(smartedtv_home_seguro,'
                             'ActivateWindow(Home),00:00:30,silent)</onload>\n'
                             '</window>', 1)
        if novo == texto:
            return dados
        ET.fromstring(novo.encode('utf-8'))
        return novo.encode('utf-8')
    padroes = (
        r'<onload[^>]*>\s*ReplaceWindow\(\$INFO\[System\.StartupWindow\]\)\s*</onload>',
        r'<onload\s*/>\s*ReplaceWindow\(\$INFO\[System\.StartupWindow\]\)',
        r'ReplaceWindow\(\$INFO\[System\.StartupWindow\]\)',
    )
    for padrao in padroes:
        alvos = re.findall(padrao, texto, re.DOTALL)
        if len(alvos) == 1:
            novo = texto.replace(alvos[0], STARTUP_ONLOAD, 1)
            ET.fromstring(novo.encode('utf-8'))
            return novo.encode('utf-8')
    # Skin sem o ReplaceWindow antigo: injeta as duas acoes no inicio da janela.
    novo = re.sub(r'(<window[^>]*>)', r'\1' + STARTUP_ONLOAD, texto, count=1)
    if novo == texto:
        raise SystemExit('Startup.xml sem <window> para injetar a tela')
    ET.fromstring(novo.encode('utf-8'))
    return novo.encode('utf-8')


def mapa_da_skin():
    """Todos os arquivos da skin Classica, no caminho de cada skin do APK.

    ``skin.novatv`` é a skin ATIVA (o dex grava esse id no perfil) e
    ``skin.smartedtv.classic`` é a cópia visível em Aparência > Skin.
    """
    mapa = {}
    fonte = ROOT / 'kodi/skin.estilo.personalizado'
    if not fonte.is_dir():
        raise SystemExit('skin Classica ausente: %s' % fonte)
    for caminho in sorted(fonte.rglob('*')):
        if not caminho.is_file() or '__pycache__' in caminho.parts or caminho.suffix == '.pyc':
            continue
        rel = caminho.relative_to(fonte).as_posix()
        dados = caminho.read_bytes()
        for skin in SKINS:
            # O addon.xml precisa declarar o id da PASTA (Kodi recusa id diverge).
            if rel == 'addon.xml':
                dados = (caminho.read_text(encoding='utf-8')
                         .replace('id="skin.estilo.personalizado"', 'id="%s"' % skin)
                         .encode('utf-8'))
            mapa['assets/addons/%s/%s' % (skin, rel)] = dados
    return mapa


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', required=True, type=Path)
    parser.add_argument('--saida', required=True, type=Path)
    args = parser.parse_args(argv)
    if args.apk.resolve() == args.saida.resolve():
        raise SystemExit('entrada e saida precisam ser diferentes')

    extras = arquivos_do_addon()
    extras.update(arquivos_do_servico())
    dbg('arquivos para atualizar: %d (addon + servico/keymap)' % len(extras))
    arquivos_da_skin = mapa_da_skin()

    perfil = {}
    substituidos = set()
    startups = 0
    skins = 0
    arvore = 0
    with zipfile.ZipFile(args.apk) as _z:
        existentes = _z.namelist()
    nomes_skin = {n for n in existentes if n.startswith(SKIN_PREFIX)}
    # Addon registrado no addon-manifest.xml? Skin ausente da base não é criada
    # pela metade (o Kodi ignoraria a pasta e o item de Aparência sumiria).
    presentes = {skin for skin in SKINS
                 if 'assets/addons/%s/addon.xml' % skin in existentes}
    if 'skin.novatv' not in presentes:
        raise SystemExit('APK base sem a skin ativa skin.novatv')
    arquivos_da_skin = {n: d for n, d in arquivos_da_skin.items()
                        if n.split('/')[2] in presentes}
    ignorados = sorted(set(arquivos_da_skin) - nomes_skin)
    extras.update({n: d for n, d in arquivos_da_skin.items() if n not in nomes_skin})
    dbg('skin: %d arquivo(s) da Classica para %s (%d fora do zip)'
        % (len(arquivos_da_skin), '/'.join(SKINS), len(ignorados)))
    with zipfile.ZipFile(args.apk) as origem:
        nomes = set(origem.namelist())
        for exigido in EXIGIDOS:
            if exigido not in nomes:
                raise SystemExit('APK base sem %s' % exigido)
        if 'assets/addons/service.smarted.bootstrap/service.py' not in nomes:
            raise SystemExit('APK base sem o servico smarted')

        with zipfile.ZipFile(args.saida, 'w', allowZip64=True) as destino:
            vistos = set()
            for item in origem.infolist():
                if item.is_dir() or SIG.fullmatch(item.filename):
                    continue
                if item.filename in vistos:
                    raise SystemExit('entrada duplicada: %s' % item.filename)
                vistos.add(item.filename)
                dados = origem.read(item)
                if item.filename.startswith(SKIN_PREFIX):
                    # A Home inteira vem da skin Classica (home + janelas + media).
                    # O mapa SKIN_ARQUIVOS continua valendo para outros caminhos.
                    novo = arquivos_da_skin.get(item.filename)
                    if novo is not None and novo != dados:
                        dados = novo
                        arvore += 1
                if item.filename.startswith(ADDON_PREFIX):
                    substituidos.add(item.filename)
                    continue
                if item.filename.startswith(SERVICO) and \
                        item.filename[len(SERVICO):] in MODULOS:
                    substituidos.add(item.filename)
                    continue
                if item.filename == KEYMAP_DESTINO:
                    substituidos.add(item.filename)
                    continue
                if item.filename in SKIN_ARQUIVOS and item.filename not in arquivos_da_skin:
                    novo_skin = SKIN_ARQUIVOS[item.filename].read_bytes()
                    if novo_skin != dados:
                        dados = novo_skin
                        skins += 1
                        dbg('%s: XML da skin atualizado' % item.filename)
                    substituidos.add(item.filename)
                    # sem continue: o arquivo precisa ser gravado abaixo
                alvo_startup = STARTUP.fullmatch(item.filename)
                if alvo_startup:
                    novo = patch_startup(dados)
                    if novo != dados:
                        dados = novo
                        startups += 1
                        dbg('%s: Startup.xml atualizado' % alvo_startup.group(1))
                if item.filename.startswith('assets/smarted/profile/'):
                    perfil[item.filename] = hashlib.sha256(dados).hexdigest()
                info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                info.compress_type = item.compress_type
                info.external_attr = item.external_attr
                info.comment = item.comment
                destino.writestr(info, dados)

            for nome in sorted(extras):
                info = zipfile.ZipInfo(nome, date_time=(2026, 11, 17, 18, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                destino.writestr(info, extras[nome])
                dbg('gravado: %s' % nome)
            dbg('substituidos no APK base: %d; Startups atualizados: %d; '
                'XMLs de skin atualizados: %d'
                % (len(substituidos), startups, skins))

    with zipfile.ZipFile(args.saida) as z:
        for nome, resumo in perfil.items():
            if hashlib.sha256(z.read(nome)).hexdigest() != resumo:
                raise SystemExit('perfil semeado alterado: %s' % nome)
        for nome in extras:
            if nome not in z.namelist() or z.read(nome) != extras[nome]:
                raise SystemExit('arquivo nao entrou igual: %s' % nome)
        for nome, origem in SKIN_ARQUIVOS.items():
            if nome in z.namelist() and z.read(nome) != origem.read_bytes():
                raise SystemExit('XML da skin nao entrou igual: %s' % nome)
        for aba in ('lib/arm64-v8a/libkodi.so', 'lib/armeabi-v7a/libkodi.so'):
            if aba not in z.namelist():
                raise SystemExit('ABI perdida: %s' % aba)
        if any(SIG.fullmatch(n) for n in z.namelist()):
            raise SystemExit('assinatura antiga nao foi removida')
        dbg('OK: %d arquivos do perfil intactos, duas ABIs e sem assinatura antiga'
            % len(perfil))
    return 0


if __name__ == '__main__':
    sys.exit(main())
