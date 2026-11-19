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
    """(removidos, motivos) - addons que saem do APK nesta montagem."""
    quebrados, pastas = addons_anunciados_sem_codigo(existentes, zip_aberto)
    motivos = {addon: 'declarado no APK e sem o codigo que carrega'
               for addon in quebrados}
    # Pasta de addon sem addon.xml: o Kodi nem carrega, mas ocupa o perfil e
    # aparece em Ajuda > Informacoes; tambem sai (nao e addon desta entrega).
    for addon, prefixo in pastas.items():
        if (prefixo + 'addon.xml') not in existentes:
            quebrados.add(addon)
            motivos[addon] = 'pasta sem addon.xml'
    for addon in ADDONS_QUE_NAO_VEM:
        if addon in pastas:
            quebrados.add(addon)
            motivos.setdefault(addon, 'addon de terceiro que a entrega nao inclui')
    # Nada que outro addon do APK exige pode sair: sem a dependencia o Kodi
    # nem inicia o gerenciador de addons (foi o que aconteceu com o
    # audioencoder.kodi.builtin.aac na 1.0.135).
    exigidos = addons_exigidos(existentes, zip_aberto)
    for addon in sorted(quebrados & exigidos):
        quebrados.discard(addon)
        motivos.pop(addon, None)
    return sorted(quebrados), motivos


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

        with zipfile.ZipFile(args.saida, 'w', allowZip64=True) as destino:
            vistos = set()
            for item in origem.infolist():
                if item.is_dir() or SIG.fullmatch(item.filename):
                    continue
                if any(item.filename.startswith('assets/addons/%s/' % addon)
                       for addon in removidos):
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
