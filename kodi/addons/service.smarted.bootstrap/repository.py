# -*- coding: utf-8 -*-
"""Vikings Repo no primeiro boot: registro, habilitacao e add-on de video.

O Kodi so "conhece" um repositorio quando a pasta do add-on
(``repository.*``/``*.repo``) existe na pasta de add-ons do perfil, ou quando
ela vem entre os add-ons de sistema do APK — e o gerenciador de add-ons e
atualizado depois disso. Este modulo faz o mesmo que o "Instalar a partir de
arquivo zip" da interface, sem GUI:

1. se o repositorio veio dentro do APK (``assets/addons/vkkodi.repo``), o Kodi
   ja o copiou para o perfil no primeiro boot — nada a fazer;
2. se nao veio, mas o zip esta no ``payload`` deste add-on, ele e extraido para
   ``special://home/addons/<id>`` e ``UpdateLocalAddons()`` registra a pasta;
3. o repositorio e habilitado por JSON-RPC (``Addons.SetAddonEnabled``), o que
   o coloca na lista de repositorios ativos;
4. se o add-on de video ``plugin.video.BrazucaPlay.Matrix`` estiver ausente,
   ``UpdateAddonRepos()`` + ``InstallAddon(<id>)`` instalam a versao publicada
   no repositorio. Quando o perfil semeado ja trouxe o add-on (caso normal),
   nada e baixado.

Nada aqui inventa repositorio: sem zip (no APK ou no payload) o modulo apenas
registra o fato no log do bootstrap.

O modulo nao importa ``xbmc*`` no topo: recebe ``jsonrpc``/``execute`` por
parametro, para poder ser testado fora do Kodi.
"""
from __future__ import absolute_import, unicode_literals

import glob
import os
import shutil
import zipfile
from xml.etree import ElementTree

import repair

PLUGIN_ID = 'plugin.video.BrazucaPlay.Matrix'
# Nomes de zip que podem ser um repositorio Vikings (o time publica mais de um:
# ``repository.vikings`` no site e ``vkkodi.repo``/``vikings.repo`` no GitHub).
PADROES_REPO = ('repository*.zip', '*.repo*.zip')
PADRAO_PLUGIN = PLUGIN_ID + '-*.zip'
REPO_URL = 'https://github.com/vikingsbuild/vikings.repo/raw/master/vkkodi.repo/vkkodi.repo-3.00.zip'


def _log(log, mensagem):
    if log:
        log(mensagem)


def _e_repositorio(addon_id):
    return bool(addon_id) and (addon_id.startswith('repository.') or addon_id.endswith('.repo'))


def pasta_addons(home):
    return os.path.join(home, 'addons')


def repos_instalados(pastas):
    """Ids de repositorio presentes nas pastas dadas (perfil, sistema, extras)."""
    achados = set()
    for pasta in pastas:
        if not pasta or not os.path.isdir(pasta):
            continue
        try:
            filhos = os.listdir(pasta)
        except OSError:
            continue
        for nome in filhos:
            if _e_repositorio(nome) and os.path.isfile(os.path.join(pasta, nome, 'addon.xml')):
                achados.add(nome)
    return achados


def instalado(adicionais=(), home=None, addons_dir=None):
    """True quando ha algum repositorio Vikings instalado."""
    pastas = list(adicionais)
    if home:
        pastas.append(pasta_addons(home))
    if addons_dir:
        pastas.append(addons_dir)
    return bool(repos_instalados(pastas))


def _ler_zip(caminho):
    """Devolve (addon_id, [(entrada, caminho_relativo)]) de um zip de add-on."""
    with zipfile.ZipFile(caminho) as arquivo:
        nomes = [n for n in arquivo.namelist() if n.endswith('addon.xml') and n.count('/') == 1]
        if len(nomes) != 1:
            raise ValueError('zip sem addon.xml unico na raiz')
        bruto = arquivo.read(nomes[0])
        addon_id = ElementTree.fromstring(bruto).get('id') or ''
        return addon_id, arquivo.namelist()


def extrair_payload(home, payload_dir, log=None, ids=None):
    """Extrai os zips de repositorio do payload. Devolve a lista de ids."""
    instalados = []
    padroes = []
    for padrao in PADROES_REPO:
        padroes.extend(sorted(glob.glob(os.path.join(payload_dir, padrao))))
    for caminho in padroes:
        try:
            addon_id, _ = _ler_zip(caminho)
        except Exception as erro:  # noqa: BLE001 - zip estranho nao pode derrubar o boot
            _log(log, 'vikings: %s nao e um add-on valido (%s)'
                 % (os.path.basename(caminho), erro))
            continue
        if not _e_repositorio(addon_id):
            _log(log, 'vikings: %s declara %s (nao e repositorio)' % (os.path.basename(caminho), addon_id))
            continue
        if ids is not None and addon_id not in ids:
            continue
        destino = os.path.join(pasta_addons(home), addon_id)
        try:
            with zipfile.ZipFile(caminho) as arquivo:
                membros = repair._safe_members(arquivo, addon_id)
                if os.path.isdir(destino):
                    shutil.rmtree(destino)
                os.makedirs(destino)
                for entrada, relativo in membros:
                    alvo = os.path.join(destino, *relativo.split('/'))
                    pasta = os.path.dirname(alvo)
                    if pasta and not os.path.isdir(pasta):
                        os.makedirs(pasta)
                    with arquivo.open(entrada) as fonte, open(alvo, 'wb') as saida:
                        shutil.copyfileobj(fonte, saida, 256 * 1024)
            if os.path.isfile(os.path.join(destino, 'addon.xml')):
                instalados.append(addon_id)
                _log(log, 'vikings: INSTALADO %s a partir do payload' % addon_id)
            else:
                _log(log, 'vikings: FALHOU ao extrair %s (addon.xml ausente)' % addon_id)
        except Exception as erro:  # pacote corrompido, disco cheio, permissao...
            _log(log, 'vikings: ERRO ao extrair %s: %s' % (addon_id, erro))
            shutil.rmtree(destino, ignore_errors=True)
    return instalados


def habilitar(addon_ids, jsonrpc, log=None):
    """Habilita add-ons por JSON-RPC e devolve os que falharam."""
    falharam = []
    for addon_id in addon_ids:
        try:
            resposta = jsonrpc('Addons.SetAddonEnabled',
                               {'addonid': addon_id, 'enabled': True}) or {}
        except Exception as erro:  # noqa: BLE001
            resposta = {'error': {'message': str(erro)}}
        if resposta.get('error'):
            mensagem = (resposta.get('error') or {}).get('message', 'erro')
            _log(log, 'vikings: nao habilitou %s (%s)' % (addon_id, mensagem))
            falharam.append(addon_id)
        else:
            _log(log, 'vikings: %s habilitado' % addon_id)
    return falharam


def plugin_instalado(adicionais=(), home=None):
    pastas = list(adicionais)
    if home:
        pastas.append(pasta_addons(home))
    return any(os.path.isfile(os.path.join(p, PLUGIN_ID, 'addon.xml')) for p in pastas if p)


def instalar_plugin(execute, jsonrpc, log=None):
    """Pede ao Kodi para instalar o add-on de video a partir do repositorio."""
    try:
        execute('UpdateAddonRepos()')
    except Exception as erro:  # noqa: BLE001
        _log(log, 'vikings: UpdateAddonRepos falhou (%s)' % erro)
    try:
        execute('InstallAddon(%s)' % PLUGIN_ID)
    except Exception as erro:  # noqa: BLE001
        _log(log, 'vikings: InstallAddon falhou (%s)' % erro)
        return False
    resposta = jsonrpc('Addons.GetAddonDetails',
                       {'addonid': PLUGIN_ID, 'properties': ['version']}) or {}
    ok = bool((resposta.get('result') or {}).get('addon'))
    _log(log, 'vikings: %s %s' % (PLUGIN_ID, 'instalado pelo repositorio'
                                  if ok else 'ainda ausente (o reparo do perfil resolve)'))
    return ok


def ensure_repository(home, payload_dir, adicionais=(), jsonrpc=None, execute=None,
                      log=None):
    """Garante o Vikings Repo registrado/habilitado e o add-on de video presente.

    Devolve ``{'repos': [...], 'instalado': bool, 'habilitado': [...],
    'plugin': bool, 'falhas': [...]}``.
    """
    pastas = [p for p in adicionais if p] + [pasta_addons(home)]
    report = {'repos': [], 'instalado': False, 'habilitado': [], 'plugin': False,
              'falhas': []}

    report['repos'] = sorted(repos_instalados(pastas))
    if not report['repos']:
        report['repos'] = sorted(extrair_payload(home, payload_dir, log))
    report['instalado'] = bool(report['repos'])
    if not report['instalado']:
        _log(log, 'vikings: repositorio ausente do APK e do payload '
                  '(endereco oficial: %s)' % REPO_URL)
        return report

    if jsonrpc is not None:
        if execute is not None:
            try:
                execute('UpdateLocalAddons()')
            except Exception as erro:  # noqa: BLE001
                _log(log, 'vikings: UpdateLocalAddons falhou (%s)' % erro)
        report['falhas'] = habilitar(report['repos'], jsonrpc, log)
        report['habilitado'] = [i for i in report['repos'] if i not in report['falhas']]

    report['plugin'] = plugin_instalado(adicionais, home=home)
    if not report['plugin'] and execute is not None and jsonrpc is not None:
        report['plugin'] = instalar_plugin(execute, jsonrpc, log)
    return report
