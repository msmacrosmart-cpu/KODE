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
import itertools
import re
import sqlite3
import struct
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDON_ID = 'script.smartedtv.welcome'
ADDON_DIR = ROOT / 'kodi' / 'addons' / ADDON_ID
ADDON_PREFIX = 'assets/addons/%s/' % ADDON_ID
SERVICO = 'assets/addons/service.smarted.bootstrap/'
# Plugin-ponte: e quem entrega a tela de pastas (rotas pasta/ordenar) e as
# rotas da Home. Sem ele no APK o filtro/ordenacao nova nao existiria no
# aparelho, mesmo com o XML da skin atualizado.
PONTE = 'assets/addons/plugin.video.smarted/'
PONTE_DIR = ROOT / 'kodi' / 'addons' / 'plugin.video.smarted'
# ``variante.py`` decide MOBILE x TV (pasta do Dropbox, pacote, anuncio); sem
# ele no APK o app cai no padrao mobile e as duas versoes baixariam o mesmo APK.
#
# ``ads_regra.py`` e ``ads_vast.py`` FALTAVAM nesta lista, e isso quebrava o
# servico no aparelho: ``smart_ads.py`` faz ``import ads_regra`` no topo, o
# modulo nao existia no APK e o Python abortava o ``service.py`` inteiro com
# FileNotFoundError (log real de 2026-11-19: "No such file or directory:
# .../service.smarted.bootstrap/ads_regra.py"). Resultado: notificacao de erro
# no boot e NENHUM dos trabalhos do servico (reparo, favoritos, skin, anuncio)
# rodava. ``ads_vast.py`` tem o mesmo risco: e importado por smart_ads.py para o
# anuncio de video da TV. Todo modulo do addon que e importado precisa entrar
# aqui; os testes comparam a pasta com esta lista para nao faltar de novo.
MODULOS = ('service.py', 'menu_smarted.py', 'performance.py', 'vip.py',
           'variante.py', 'smart_ads.py', 'ads_regra.py', 'ads_vast.py',
           'ad_return.py', 'ao_vivo.py', 'smarted_release.py', 'check.py',
           # ``service.py`` tambem importa estes tres no topo (repair,
           # favourites, skin_setup). Sem eles o servico morre no import - o
           # mesmo caminho de falha do ads_regra, so que parando ainda mais
           # cedo: nada de reparo, favoritos, skin nem anuncio.
           'repair.py', 'favourites.py', 'skin_setup.py',
           'addon.xml')

# Marcador lido por ``variante.py`` dentro do APK: diz QUAL versao e este APK
# (celular ou TV). O App Armor nao tem fonte neste repositorio - o build so
# reempacota assets - entao a variante viaja como arquivo, e nao por um pacote
# Android diferente.
MARCADOR_VARIANTE = 'assets/smartedtv-variante.txt'
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
    # Home: identidade visual aprovada.
    # MyVideoNav: e a tela de pastas/categorias do Brazuca; entra aqui para a
    # correcao do bloco branco chegar ao APK (antes so o Home.xml era trocado
    # e o XML do repositorio nao valia nada no aparelho).
    for nome in ('Home.xml', 'MyVideoNav.xml')
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


def arquivos_da_ponte():
    """Todo o plugin-ponte (rotas, ordenacao, arte local das categorias)."""
    arquivos = {}
    if not PONTE_DIR.is_dir():
        raise SystemExit('plugin-ponte ausente: %s' % PONTE_DIR)
    for caminho in sorted(PONTE_DIR.rglob('*')):
        if not caminho.is_file() or '__pycache__' in caminho.parts or caminho.suffix == '.pyc':
            continue
        arquivos[PONTE + caminho.relative_to(PONTE_DIR).as_posix()] = caminho.read_bytes()
    for rel in ('addon.xml', 'default.py', 'routes.py', 'ordering.py'):
        if PONTE + rel not in arquivos:
            raise SystemExit('plugin-ponte incompleto: falta %s' % rel)
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
                  'ActivateWindow(Home),00:00:25,silent)</onload>')

# A janela de startup precisa DESENHAR alguma coisa: quando ela fica vazia o
# usuario ve preto enquanto o Python/addons sobem (TV box lento, cache do APK
# sendo extraido, primeira abertura depois de atualizar). Este bloco vai para
# TODAS as skins, inclusive a reserva (skin.estuary).
STARTUP_CONTROLS = (
    '<controls>\n'
    '\t\t<control type="image"><left>0</left><top>0</top>'
    '<width>100%</width><height>100%</height>'
    '<texture colordiffuse="pb_dark">pb_white.png</texture></control>\n'
    '\t\t<control type="image"><left>0</left><top>0</top>'
    '<width>100%</width><height>100%</height>'
    '<texture>pb_scrim_v.png</texture></control>\n'
    # Logo do app no lugar do texto "SMARTEDTV": a marca desenhada e a
    # primeira coisa que o usuario ve (mesma imagem do launcher).
    '<control type="image"><left>0</left><top>430</top>'
    '<width>100%</width><height>132</height>'
    '<aspectratio align="center" aligny="center">keep</aspectratio>'
    '<texture>smarted_splash_logo.png</texture></control>\n'
    '\t\t<control type="label"><left>0</left><top>580</top>'
    '<width>100%</width><height>36</height><font>font12</font>'
    '<textcolor>pb_muted</textcolor><align>center</align>'
    '<aligny>center</aligny><label>Carregando</label></control>\n'
    '\t</controls>')


def _sem_comentarios(texto):
    """Comentarios fora do caminho: o texto antigo cita <controls /> neles."""
    return re.sub(r'<!--.*?-->', '', texto, flags=re.DOTALL)


def _com_controles(texto):
    """Troca o <controls> de uma skin pelo da espera (um so por janela)."""
    achado = re.search(r'<controls\b[^>]*/>|<controls\b[^>]*>.*?</controls>',
                       texto, re.DOTALL)
    if achado:
        return texto[:achado.start()] + STARTUP_CONTROLS + texto[achado.end():]
    return texto.replace('</window>', '\n' + STARTUP_CONTROLS + '\n</window>', 1)


def validar_startup(dados):
    """Recusa publicar Startup.xml que deixaria o app no preto."""
    raiz = ET.fromstring(dados)
    acoes = [(e.text or '').strip() for e in raiz.findall('onload')]
    if len([a for a in acoes if 'smartedtv_entrada,' in a]) != 1:
        raise SystemExit('Startup.xml: disparo da tela invalido %r' % acoes)
    if len([a for a in acoes if 'seguro=1' in a]) != 1:
        raise SystemExit('Startup.xml: vigia do boot invalido %r' % acoes)
    if [a for a in acoes if 'ReplaceWindow' in a]:
        raise SystemExit('Startup.xml: ReplaceWindow do startup nao pode voltar')
    if len([a for a in acoes if 'smartedtv_home_seguro' in a]) != 1:
        raise SystemExit('Startup.xml: sem seguro da Home %r' % acoes)
    controles = raiz.findall('controls')
    if len(controles) != 1:
        raise SystemExit('Startup.xml: precisa de exatamente um <controls>')
    labels = [(e.text or '').strip() for e in controles[0].iter('label')]
    if 'Carregando' not in labels:
        raise SystemExit('Startup.xml: janela de boot sem espera visivel')
    # a espera so pode usar fontes que a skin declarar; o build confere no
    # simulador, aqui basta nao depender de add-on/rede
    for rotulo in controles[0].iter('label'):
        if '$INFO' in (rotulo.text or ''):
            raise SystemExit('Startup.xml: espera do boot nao pode depender de dados')
    return True


def _nossos(texto, trecho):
    return ('smartedtv_entrada,' in trecho or 'smartedtv_home_seguro' in trecho
            or ('seguro=1' in trecho and 'script.smartedtv.welcome' in trecho))


def patch_startup(dados):
    """Deixa o Startup.xml de qualquer skin no formato do SMARTEDTV.

    Aplica em TODAS as skins do APK (inclusive a reserva, skin.estuary): se
    uma delas ficasse com o `ReplaceWindow($INFO[System.StartupWindow])`
    antigo e fosse ativada por um perfil antigo, o app abriria no preto.

    Resultado, sempre o mesmo (idempotente):
    * um disparo da tela de entrada, um vigia `seguro=1` e um alarme de
      seguranca que abre a Home sem depender de Python;
    * um unico <controls>, com a espera desenhada (fundo + "Carregando");
    * nenhum ReplaceWindow do startup e nenhum onload nosso duplicado
      (builds anteriores somavam o bloco inteiro a um arquivo que ja tinha o
      `seguro=1`, e o boot abria a tela duas vezes).
    """
    texto = _sem_comentarios(dados.decode('utf-8'))
    raiz = ET.fromstring(texto)
    if raiz.tag != 'window':
        raise SystemExit('Startup.xml sem <window> para injetar a tela')
    # 1. remove os onload nossos (de qualquer versao anterior) e o salto antigo
    def _limpar(match):
        trecho = match.group(0)
        # salto direto para a Home no startup tambem sai: quem abre a Home e a
        # tela de entrada (sem isso o app abria a Home por tras da tela, ou no
        # preto quando a tela ainda nao existia)
        if 'ReplaceWindow(' in trecho:
            return ''
        return '' if _nossos(texto, trecho) else trecho
    corpo = re.sub(r'<onload[^>]*>.*?</onload>|<onload\s*/>', _limpar, texto,
                   flags=re.DOTALL)
    corpo = re.sub(r'ReplaceWindow\(\$INFO\[System\.StartupWindow\]\)', '',
                   corpo)
    # 2. os tres <onload> entram logo no inicio da janela
    corpo = re.sub(r'(<window[^>]*>)', r'\1\n\t' + STARTUP_ONLOAD, corpo,
                   count=1)
    # onload vazio (era o salto antigo, agora sem texto) sai de cena
    corpo = re.sub(r'[ \t]*<onload\s*>(?:\s*)</onload>\s*\n?', '', corpo)
    corpo = re.sub(r'[ \t]*<onload\s*/>\s*\n?', '', corpo)
    # 3. a espera desenhada substitui o <controls> da skin
    novo = _com_controles(corpo)
    # linhas que sobraram em branco (eram dos onload remontados) nao ficam
    novo = re.sub(r'(?m)^[ \t]*\n', '', novo)
    novo = re.sub(r'\n{2,}', '\n', novo)
    # <controls> sempre no inicio da linha (o <onload> anterior pode ter ficado
    # sem quebra quando a skin nao tinha <controls> nenhum)
    novo = re.sub(r'[ \t]*<controls>', '\n<controls>', novo, count=1)
    validar_startup(novo.encode('utf-8'))
    if novo == dados.decode('utf-8'):
        return dados
    return novo.encode('utf-8')


# ---------------------------------------------------------------------------
# Addons que deixam a notificacao "Add-on com erro" na tela do projetor
# ---------------------------------------------------------------------------
# O Kodi abre a tela de um addon que ele conhece; se o codigo nao existe (pasta
# vazia, zip do usuario apagado, ``library`` apontando para arquivo ausente) a
# tela vira "Add-on com erro" POR CIMA da Home - e nesse estado a Home nao
# carrega o conteudo. O dono do app viu exatamente isso: YouTube, OpenWizard e
# outros addons que nunca fizeram parte desta entrega.
#
# Regras daqui:
#   * addon declarado no APK cuja pasta/codigo nao existe -> sai do zip;
#   * addon que a skin cita e o app NAO entrega -> sai do zip (a Home usa
#     ``System.HasAddon`` para ele, entao o botao simplesmente nao aparece);
#   * nada de esconder erro: o build lista o que saiu no log.
# Addons EMBUTIDOS do motor do Kodi (nao sao desta entrega nem de terceiros).
# O motor nao inicia sem varios deles; nenhuma limpeza jamais os toca.
EMBUTIDOS_DO_KODI = (
    'audioencoder.kodi.builtin.',
    'screensaver.xbmc.builtin.',
    'kodi.binary.',
    'kodi.resource',
    'xbmc.',
    'game.controller.',
    'metadata.',
    'resource.language.',
    'resource.uisounds.',
    'resource.images.',
    'webinterface.',
    'vfs.',
    'inputstream.',
    'skin.',
    'script.module.',
    'service.subtitles.',
)

ADDONS_QUE_NAO_VEM = (
    'plugin.video.youtube',           # skin cita a busca do YouTube
    'plugin.program.openwizard2',
    'plugin.audio.mp3streams',        # perfil antigo do aparelho
    'service.subtitles.legendei',
    'plugin.program.openwizard',      # assistente de repositorio de terceiros
    'plugin.program.openwizard2',
    'plugin.video.openwizard',
    'repository.openwizard',
    'plugin.program.super.favourites',
    'script.module.bingie',
    'skin.bingie',
)


def pastas_de_addons(existentes):
    """{id: prefixo no zip} das pastas de addon embarcadas."""
    achados = {}
    for nome in existentes:
        if not nome.startswith('assets/addons/'):
            continue
        partes = nome.split('/')
        if len(partes) > 3 and partes[2]:
            achados.setdefault(partes[2], 'assets/addons/%s/' % partes[2])
    return achados


def addons_anunciados_sem_codigo(existentes, zip_aberto):
    """Ids de addons que o APK anuncia mas nao entrega por inteiro.

    Um addon esta "anunciado" quando tem ``addon.xml`` no zip (o Kodi le esse
    arquivo e passa a conhecer o addon) ou quando aparece em
    ``addon-manifest.xml``. Ele esta QUEBRADO quando o ``addon.xml`` diz qual
    biblioteca carregar e esse arquivo/pasta nao existe no zip - e assim que o
    Kodi monta a tela de erro.
    """
    import xml.etree.ElementTree as ET
    pastas = pastas_de_addons(existentes)
    quebrados = set()
    for nome in existentes:
        if not nome.startswith('assets/addons/') or not nome.endswith('/addon.xml'):
            continue
        partes = nome.split('/')
        if len(partes) < 4 or partes[2] not in pastas:
            continue
        try:
            raiz = ET.fromstring(zip_aberto.read(nome))
        except Exception:
            # addon.xml que nao le: nao da para saber o que ele carrega, e
            # remover as cegas poderia tirar uma skin/idioma que o app usa.
            # O servico do app trata esse caso no aparelho (limpar_addons_
            # quebrados), onde o historico de uso mostra o que falta.
            dbg('addon com addon.xml ilegivel (mantido): %s' % partes[2])
            continue
        for ext in raiz.findall('extension'):
            lib = (ext.get('library') or '').strip()
            if not lib:
                continue
            alvo = 'assets/addons/%s/%s' % (partes[2], lib)
            if alvo in existentes:
                continue
            if any(n.startswith(alvo.rstrip('/') + '/') for n in existentes):
                continue
            quebrados.add(partes[2])
    return quebrados, pastas


def addons_exigidos(existentes, zip_aberto):
    """Ids que algum addon que FICA no APK declara como dependencia obrigatoria.

    O Kodi nao inicia com dependencia obrigatoria faltando:
        critical: addon 'audioencoder.kodi.builtin.aac' not installed or not enabled.
        critical: CServiceManager::InitStageTwo: Unable to start CAddonMgr
    e o app fica sem GUI (tela preta, Home vazia). Remover um addon que outro
    depende derruba o aparelho inteiro - logo, dependencia de quem fica e
    intocavel, mesmo que esteja na lista de terceiros.
    """
    import xml.etree.ElementTree as ET
    exigidos = set()
    for nome in existentes:
        if not nome.startswith('assets/addons/') or not nome.endswith('/addon.xml'):
            continue
        try:
            raiz = ET.fromstring(zip_aberto.read(nome))
        except Exception:
            continue
        for requires in raiz.findall('requires'):
            for importado in requires.findall('import'):
                if (importado.get('optional') or '').lower() in ('true', '1'):
                    continue
                if importado.get('addon'):
                    exigidos.add(importado.get('addon'))
    return exigidos


def addons_sem_entrega(existentes, zip_aberto):
    """(removidos, motivos) - addons de TERCEIRO que saem do APK.

    A remocao e SOMENTE por lista de nomes comprovados no aparelho, nunca por
    heuristica. Ja se tentou heuristica ("addon.xml sem o arquivo que carrega",
    "pasta sem addon.xml") e o resultado foi catastrofico: a 1.0.135 e a 1.0.136
    sairam sem ``audioencoder.kodi.builtin.aac``/``.wma`` e sem
    ``screensaver.xbmc.builtin.*`` - addons EMBUTIDOS do Kodi, que as regras
    genericas classificaram como "quebrados". Sem o audioencoder o Kodi nem
    inicia:
        critical: addon 'audioencoder.kodi.builtin.aac' not installed or not enabled.
        critical: CServiceManager::InitStageTwo: Unable to start CAddonMgr
    (medido no emulador de projetor: tela sem GUI e Home sem dados).
    """
    pastas = pastas_de_addons(existentes)
    removidos = []
    motivos = {}
    for addon in ADDONS_QUE_NAO_VEM:
        if addon in pastas:
            removidos.append(addon)
            motivos[addon] = 'addon de terceiro comprovado no perfil (evidencia no projetor)'
    # Cinto de seguranca: mesmo que alguem acrescente um nome por engano, nada
    # que seja do motor do Kodi, dependencia obrigatoria ou skin sai do zip.
    protegidos = addons_exigidos(existentes, zip_aberto)
    finais = []
    for addon in removidos:
        if addon in protegidos or addon.startswith(EMBUTIDOS_DO_KODI):
            motivos.pop(addon, None)
            continue
        finais.append(addon)
    return sorted(finais), motivos


PERFIL_PREFIX = 'assets/smarted/profile/'
PERFIL_MANIFESTO = 'assets/smarted/profile-manifest.txt'
PIN_PERFIL_BASE = '1447de816a44ecc11c42c2c315cf20e61c9baa037e914a13293711cf152d1ede'
# Pedido explicito: remover do perfil semeado APENAS YouTube e MP3 Streams,
# mantendo todo o restante (Elementum, BrazucaPlay, ResolveURL, skins, etc.).
ADDONS_FORA_DO_PERFIL = (
    'plugin.video.youtube',
    'plugin.audio.mp3streams',
)


def _caminho_perfil_excluido(rel):
    for addon in ADDONS_FORA_DO_PERFIL:
        if (rel.startswith('addons/%s/' % addon)
                or rel.startswith('userdata/addon_data/%s/' % addon)
                or rel.startswith('addons/packages/%s-' % addon)
                or rel == 'addons/packages/%s.zip' % addon):
            return True
    return False


def _limpar_addons_db_bytes(dados):
    """Remove apenas YouTube e MP3 Streams do Addons*.db sem tocar nos demais."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        caminho_tmp = Path(tmp.name)
        tmp.write(dados)
    try:
        mexeu = False
        con = sqlite3.connect(str(caminho_tmp))
        try:
            for addon in ADDONS_FORA_DO_PERFIL:
                for sql in (
                    'DELETE FROM repo WHERE addonID = ?',
                    'DELETE FROM addonlinkrepo WHERE addonID = ?',
                    'DELETE FROM installed WHERE addonID = ?',
                    'DELETE FROM addons WHERE addonID = ?',
                    'DELETE FROM package WHERE addonID = ?',
                ):
                    try:
                        cur = con.execute(sql, (addon,))
                        if getattr(cur, 'rowcount', 0) > 0:
                            mexeu = True
                    except Exception:
                        continue
            if mexeu:
                con.commit()
        finally:
            con.close()
        return caminho_tmp.read_bytes() if mexeu else dados
    finally:
        caminho_tmp.unlink(missing_ok=True)


def _mutf8_para_utf16(dados):
    """Decodifica MUTF-8 para tupla de code units UTF-16 (ordem do DexFileVerifier)."""
    out = []
    i = 0
    n = len(dados)
    while i < n:
        b0 = dados[i]
        if (b0 & 0x80) == 0:
            out.append(b0)
            i += 1
        elif (b0 & 0xE0) == 0xC0 and i + 1 < n:
            u = ((b0 & 0x1F) << 6) | (dados[i + 1] & 0x3F)
            out.append(u)
            i += 2
        elif (b0 & 0xF0) == 0xE0 and i + 2 < n:
            u = (((b0 & 0x0F) << 12)
                 | ((dados[i + 1] & 0x3F) << 6)
                 | (dados[i + 2] & 0x3F))
            out.append(u)
            i += 3
        else:
            out.append(b0)
            i += 1
    return tuple(out)


def _strings_do_dex(dex):
    """Lista [(offset_payload, bytes_mutf8), ...] de string_ids em classes*.dex."""
    if len(dex) < 112 or not dex.startswith(b'dex\n'):
        raise SystemExit('classes4.dex invalido')
    count, table_off = struct.unpack_from('<II', dex, 56)
    itens = []
    for idx in range(count):
        off = struct.unpack_from('<I', dex, table_off + 4 * idx)[0]
        pos = off
        while dex[pos] & 0x80:
            pos += 1
        pos += 1
        fim = dex.index(0, pos)
        itens.append((pos, bytes(dex[pos:fim])))
    return itens


def _atualizar_dex_com_pin(dex_original, pin_antigo, pin_novo):
    """Substitui o pin SHA-256 em classes4.dex preservando string_ids ordenado."""
    antigo_b = pin_antigo.encode('ascii')
    novo_b = pin_novo.encode('ascii')
    if len(antigo_b) != 64 or len(novo_b) != 64:
        raise SystemExit('pin SHA-256 invalido')
    buf = bytearray(dex_original)
    strings = _strings_do_dex(buf)
    indices = [i for i, (_p, s) in enumerate(strings) if s == antigo_b]
    if len(indices) != 1:
        raise SystemExit('classes4.dex: esperado 1 pin de manifesto, achado %d'
                         % len(indices))
    pos = strings[indices[0]][0]
    buf[pos:pos + 64] = novo_b
    # Valida estritamente a ordenacao lexicografica UTF-16 de TODA a tabela
    verificadas = _strings_do_dex(buf)
    anterior = None
    for idx, (_p, s) in enumerate(verificadas):
        atual = _mutf8_para_utf16(s)
        if anterior is not None and not (anterior < atual):
            raise SystemExit(
                'classes4.dex: string_ids fora de ordem em %d (%r >= %r)'
                % (idx, verificadas[idx - 1][1], s))
        anterior = atual
    buf[12:32] = hashlib.sha1(memoryview(buf)[32:]).digest()
    struct.pack_into('<I', buf, 8, zlib.adler32(memoryview(buf)[12:]) & 0xFFFFFFFF)
    return bytes(buf)


def preparar_perfil_limpo(origem):
    """Retira apenas YouTube e MP3 Streams de assets/smarted/profile/ + Addons33.db.

    Atualiza assets/smarted/profile-manifest.txt e o pin SHA-256 em classes4.dex
    escolhendo uma permutacao de linhas do manifesto cujo SHA-256 caia
    estritamente entre as strings vizinhas de classes4.dex.
    """
    nomes = set(origem.namelist())
    if PERFIL_MANIFESTO not in nomes or 'classes4.dex' not in nomes:
        return set(), {}
    dex_orig = origem.read('classes4.dex')
    strings = _strings_do_dex(dex_orig)
    pin_idx = None
    pin_atual = None
    for idx, (_pos, s) in enumerate(strings):
        if len(s) == 64 and re.fullmatch(rb'[0-9a-f]{64}', s):
            candidato = s.decode('ascii')
            if candidato == hashlib.sha256(origem.read(PERFIL_MANIFESTO)).hexdigest():
                pin_idx = idx
                pin_atual = candidato
                break
            if candidato == PIN_PERFIL_BASE and pin_idx is None:
                pin_idx = idx
                pin_atual = candidato
    if pin_idx is None:
        return set(), {}

    prev_u16 = _mutf8_para_utf16(strings[pin_idx - 1][1]) if pin_idx > 0 else ()
    next_u16 = (_mutf8_para_utf16(strings[pin_idx + 1][1])
                if pin_idx + 1 < len(strings) else (0xFFFF,))

    excluidos = set()
    modificados = {}
    for nome in sorted(nomes):
        if not nome.startswith(PERFIL_PREFIX):
            continue
        rel = nome[len(PERFIL_PREFIX):]
        if not rel:
            continue
        if _caminho_perfil_excluido(rel):
            excluidos.add(nome)
            continue
        if re.fullmatch(r'userdata/Database/Addons\d+\.db', rel):
            orig_db = origem.read(nome)
            novo_db = _limpar_addons_db_bytes(orig_db)
            if novo_db != orig_db:
                modificados[nome] = novo_db

    if not excluidos and not modificados:
        return set(), {}

    linhas_orig = origem.read(PERFIL_MANIFESTO).decode('utf-8').splitlines()
    linhas_novas = []
    for linha in linhas_orig:
        if not linha.strip():
            continue
        partes = linha.split('\t')
        if len(partes) != 3:
            raise SystemExit('profile-manifest.txt invalido: %r' % linha)
        rel = partes[2]
        zip_path = PERFIL_PREFIX + rel
        if zip_path in excluidos or _caminho_perfil_excluido(rel):
            excluidos.add(zip_path)
            continue
        if zip_path in modificados:
            blob = modificados[zip_path]
            linhas_novas.append('%s\t%d\t%s\n' % (
                hashlib.sha256(blob).hexdigest(), len(blob), rel))
        else:
            linhas_novas.append(linha + '\n')

    if not linhas_novas:
        raise SystemExit('profile-manifest.txt ficou vazio')

    # Minera uma ordenacao valida das ultimas linhas para preservar a ordem de
    # string_ids em classes4.dex (ex.: prefixo '1447', prev_u16 < novo < next_u16).
    cauda_tam = min(11, len(linhas_novas))
    cabeca_bytes = ''.join(linhas_novas[:-cauda_tam]).encode('utf-8')
    cauda = linhas_novas[-cauda_tam:]
    base_hash = hashlib.sha256(cabeca_bytes)
    manifesto_final = None
    pin_novo = None
    prefixo_alvo = pin_atual[:4]

    for exigir_prefixo in (True, False):
        for perm in itertools.permutations(cauda):
            bloco = ''.join(perm).encode('utf-8')
            h = base_hash.copy()
            h.update(bloco)
            cand = h.hexdigest()
            if exigir_prefixo and not cand.startswith(prefixo_alvo):
                continue
            cand_u16 = tuple(ord(c) for c in cand)
            if prev_u16 < cand_u16 < next_u16:
                manifesto_final = cabeca_bytes + bloco
                pin_novo = cand
                break
        if manifesto_final is not None:
            break

    # Reserva para APK sintetico de teste com poucas linhas no manifesto:
    # ajusta PRAGMA user_version num Addons*.db ate achar hash no intervalo.
    if manifesto_final is None:
        alvos_db = [n for n in sorted(nomes)
                    if n.startswith(PERFIL_PREFIX + 'userdata/Database/Addons')
                    and n.endswith('.db')]
        if alvos_db:
            alvo_db = alvos_db[0]
            rel_db = alvo_db[len(PERFIL_PREFIX):]
            base_db = modificados.get(alvo_db) or origem.read(alvo_db)
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                p_tmp = Path(tmp.name)
                tmp.write(base_db)
            try:
                for versao_usr in range(1, 200000):
                    con = sqlite3.connect(str(p_tmp))
                    con.execute('PRAGMA user_version = %d' % versao_usr)
                    con.commit()
                    con.close()
                    blob = p_tmp.read_bytes()
                    linha_db = '%s\t%d\t%s\n' % (
                        hashlib.sha256(blob).hexdigest(), len(blob), rel_db)
                    tentativa = ''.join(
                        linha_db if l.endswith('\t' + rel_db + '\n') else l
                        for l in linhas_novas
                    ).encode('utf-8')
                    cand = hashlib.sha256(tentativa).hexdigest()
                    cand_u16 = tuple(ord(c) for c in cand)
                    if prev_u16 < cand_u16 < next_u16:
                        modificados[alvo_db] = blob
                        manifesto_final = tentativa
                        pin_novo = cand
                        break
            finally:
                p_tmp.unlink(missing_ok=True)

    if manifesto_final is None or pin_novo is None:
        raise SystemExit('nao foi possivel gerar pin ordenado para classes4.dex')

    dex_novo = _atualizar_dex_com_pin(dex_orig, pin_atual, pin_novo)
    modificados[PERFIL_MANIFESTO] = manifesto_final
    modificados['classes4.dex'] = dex_novo
    dbg('perfil semeado limpo: %d entradas de YouTube/MP3 Streams removidas '
        '(manifesto %s -> %s)' % (len(excluidos), pin_atual[:12], pin_novo[:12]))
    return excluidos, modificados


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
    parser.add_argument(
        '--variante', choices=('mobile', 'tv'), default=None,
        help='grava assets/smartedtv-variante.txt dentro do APK (mobile|tv)')
    args = parser.parse_args(argv)
    if args.apk.resolve() == args.saida.resolve():
        raise SystemExit('entrada e saida precisam ser diferentes')

    extras = arquivos_do_addon()
    extras.update(arquivos_do_servico())
    extras.update(arquivos_da_ponte())
    if args.variante:
        extras[MARCADOR_VARIANTE] = (
            '# versao desta instalacao: mobile = celular/tablet, '
            'tv = Android TV/box/stick/projetor\n%s\n' % args.variante
        ).encode('utf-8')
        dbg('variante gravada no APK: %s' % args.variante)
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
        # Addon que o Kodi abriria e nao tem codigo = notificacao de erro na
        # Home. Sai do zip antes de qualquer outra troca.
        removidos, motivos = addons_sem_entrega(nomes, origem)
        for addon in removidos:
            dbg('addon fora do APK: %s (%s)' % (addon, motivos[addon]))
        perfil_excluidos, perfil_modificados = preparar_perfil_limpo(origem)

        with zipfile.ZipFile(args.saida, 'w', allowZip64=True) as destino:
            vistos = set()
            for item in origem.infolist():
                if item.is_dir() or SIG.fullmatch(item.filename):
                    continue
                if item.filename in perfil_excluidos:
                    continue
                if any(item.filename.startswith('assets/addons/%s/' % addon)
                       for addon in removidos):
                    continue
                if item.filename in vistos:
                    raise SystemExit('entrada duplicada: %s' % item.filename)
                vistos.add(item.filename)
                dados = perfil_modificados.get(item.filename)
                if dados is None:
                    dados = origem.read(item)
                if item.filename == 'assets/system/addon-manifest.xml':
                    texto_man = dados.decode('utf-8')
                    linhas_man = [
                        ln for ln in texto_man.splitlines(keepends=True)
                        if not any(('>%s<' % alvo) in ln for alvo in ADDONS_FORA_DO_PERFIL)
                    ]
                    novo_man = ''.join(linhas_man).encode('utf-8')
                    if novo_man != dados:
                        ET.fromstring(novo_man)
                        dados = novo_man
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
                if item.filename in extras and item.filename.startswith(PONTE):
                    # a copia do APK base e substituida pela do repositorio; um
                    # arquivo que so exista no APK continua como esta
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
