# -*- coding: utf-8 -*-
"""Serviço de boot do SMARTEDTV.

Roda no início do Kodi e garante que o Brazuca Play esteja instalado,
habilitado e com o bootstrap interno pronto antes de qualquer tela abrir.
"""
from __future__ import absolute_import, unicode_literals

import os
import threading
import time

import xbmc
import xbmcaddon
import xbmcvfs

import repair
import smart_ads
from favourites import ensure_favourites
from performance import ensure_performance
from menu_smarted import garantir_menu, rodar_validacao_navegacao, silenciar_avisos_brazuca
from repository import ensure_repository
from skin_setup import (ensure_home_nodes, ensure_shortcuts, ensure_skin,
                        home_xml_candidates)

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
PAYLOAD_DIR = os.path.join(ADDON_PATH, 'payload')

# O perfil semeado pode ainda estar sendo copiado no primeiro boot: tentamos
# o reparo várias vezes antes de desistir (nada de esperar 90s para começar).
WAIT_SECONDS = 20
POLL_SECONDS = 5
REPAIR_ATTEMPTS = 6
# o nav-check passou a rodar em segundo plano: espera a Home assentar antes de
# percorrer as pastas (nada de I/O de rede competindo com a abertura do player)
NAV_CHECK_DELAY = 20
REPAIR_RETRY_SECONDS = 5
UISOUNDS_SILENCIO = 'resource.uisounds.silencio'


def log(message, level=xbmc.LOGINFO):
    xbmc.log('[%s] %s' % (ADDON_ID, message), level)


def jsonrpc(method, params=None):
    import json
    request = {'jsonrpc': '2.0', 'id': 1, 'method': method}
    if params is not None:
        request['params'] = params
    try:
        return json.loads(xbmc.executeJSONRPC(json.dumps(request)))
    except Exception as error:
        log('JSON-RPC %s falhou: %s' % (method, error), xbmc.LOGWARNING)
        return {}


def addon_manager_ready():
    """O Kodi só responde quando terminou de montar o banco de addons."""
    return 'result' in jsonrpc('Addons.GetAddons', {'enabled': True})


def enable_addons(addon_ids):
    """Habilita os addons no Kodi (idempotente) e devolve os que falharam."""
    failed = []
    jsonrpc('Addons.SetAddonEnabled', {'addonid': 'metadata.local', 'enabled': True})
    xbmc.executebuiltin('UpdateLocalAddons()')
    for addon_id in addon_ids:
        response = jsonrpc('Addons.SetAddonEnabled', {'addonid': addon_id, 'enabled': True})
        if response.get('error'):
            # já habilitado / sem permissão: só registra, não interrompe o boot
            log('não foi possível habilitar %s: %s' % (addon_id, response['error']),
                xbmc.LOGWARNING)
            failed.append(addon_id)
    return failed


def apply_silencio():
    """Navegacao 100% silenciosa: tema de sons vazio instalado no boot."""
    enable_addons([UISOUNDS_SILENCIO])
    resposta = jsonrpc('Settings.SetSettingValue',
                       {'setting': 'lookandfeel.soundskin', 'value': UISOUNDS_SILENCIO})
    if resposta.get('error'):
        # plano B: tema de sons vazio (o Kodi nao carrega nenhum som)
        resposta = jsonrpc('Settings.SetSettingValue',
                           {'setting': 'lookandfeel.soundskin', 'value': ''})
    if resposta.get('error'):
        log('silencio: nao foi possivel trocar o tema de sons: %s' % resposta['error'],
            xbmc.LOGWARNING)
        return False
    log('silencio: navegacao sem sons (%s)' % UISOUNDS_SILENCIO)
    return True


def write_report(home, report):
    path = os.path.join(home, 'userdata', 'smarted-bootstrap.log')
    lines = ['smarted bootstrap %s' % time.strftime('%Y-%m-%d %H:%M:%S'),
             'resultado: %s' % ('ok' if report['ok'] else 'incompleto')]
    lines += ['  ' + entry for entry in report['log']]
    try:
        folder = os.path.dirname(path)
        if folder and not os.path.isdir(folder):
            os.makedirs(folder)
        with open(path, 'a') as handle:
            handle.write('\n'.join(lines) + '\n\n')
    except Exception as error:
        log('não foi possível gravar o relatório: %s' % error, xbmc.LOGWARNING)


def run_repair(show_dialogs=False):
    home = xbmcvfs.translatePath('special://home')
    report = repair.repair_profile(home, PAYLOAD_DIR)
    for entry in report['log']:
        log(entry)
    write_report(home, report)
    if report['repaired']:
        xbmc.executebuiltin('UpdateLocalAddons()')
    failed = enable_addons(report['required'])
    if show_dialogs:
        dialog = xbmcaddon.Addon().getLocalizedString
        import xbmcgui
        if report['ok'] and not failed:
            xbmcgui.Dialog().ok(
                'Brazuca Play',
                'Addons verificados: %d\nTudo pronto para abrir o Brazuca Play.' %
                len(report['required']))
        else:
            problems = report['missing'] + failed
            xbmcgui.Dialog().ok(
                'Brazuca Play',
                'Não foi possível preparar:\n%s\n\nRelatório: userdata/smarted-bootstrap.log' %
                '\n'.join(problems[:8]))
    return report


def write_favourites():
    """Garante os atalhos do Brazuca Play em userdata/favourites.xml."""
    home = xbmcvfs.translatePath('special://home')
    try:
        added = ensure_favourites(home, log)
    except Exception as error:
        log('não foi possível gravar os favoritos: %s' % error, xbmc.LOGWARNING)
        return []
    if added:
        xbmc.executebuiltin('Notification(SMARTED, Atalhos adicionados aos favoritos, 3000)')
    return added


def apply_navigation():
    """Descobre as pastas reais do Brazuca e publica a barra superior.

    A descoberta (menu raiz do addon por Files.GetDirectory) e feita pelo
    plugin.video.smarted; aqui disparamos com force=1 para o boot sempre
    refazer o mapeamento e gravar o cache do dia.
    """
    xbmc.executebuiltin('RunPlugin(plugin://plugin.video.smarted/?route=sync-nav&force=1)')


HERO_ROTATION = 8.0      # segundos entre um lancamento e outro
HERO_CONTROL = 9201      # linha de lancamentos que alimenta o HERO


def _hero_livre():
    """O HERO so troca sozinho quando ninguem esta mexendo nele."""
    if xbmc.getCondVisibility('Player.HasMedia'):
        return False
    if not xbmc.getCondVisibility('Window.IsActive(10000)'):
        return False
    if xbmc.getCondVisibility('Control.HasFocus(%d) | Control.HasFocus(9300) | '
                              'Control.HasFocus(9301) | Control.HasFocus(9302) | '
                              'Control.HasFocus(9303)' % HERO_CONTROL):
        return False
    return bool(xbmc.getInfoLabel('Container(%d).ListItem.Label' % HERO_CONTROL))


def _posicao_hero():
    try:
        return int(xbmc.getInfoLabel('Container(%d).Position' % HERO_CONTROL) or 0)
    except (TypeError, ValueError):
        return 0


def _avanca_hero():
    """Passa o HERO para o proximo lancamento sem depender do foco do usuario."""
    antes = _posicao_hero()
    xbmc.executebuiltin('Control.Move(%d,1)' % HERO_CONTROL)
    time.sleep(0.4)
    if _posicao_hero() != antes:
        return 'move'
    # alguns builds do Kodi so movem o cursor de um container com foco: usa o
    # foco por um instante (fora dos controles do HERO) e devolve na hora
    atual = xbmc.getInfoLabel('System.CurrentControlId') or ''
    xbmc.executebuiltin('SetFocus(%d)' % HERO_CONTROL)
    xbmc.executebuiltin('Action(Right)')
    xbmc.executebuiltin('SetFocus(%s)' % (atual if atual.isdigit() else '9000'))
    return 'foco'


def rotate_hero(monitor, intervalo=HERO_ROTATION):
    """Alterna o destaque do HERO a cada ~8 s, pausando quando ha interacao."""
    espera = 0.0
    passo = 0
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            return
        if not _hero_livre():
            espera = 0.0
            continue
        espera += 1
        if espera < intervalo:
            continue
        espera = 0.0
        passo += 1
        try:
            modo = _avanca_hero()
        except Exception as erro:  # noqa: BLE001
            modo = 'erro %s' % erro
        # pulso que reativa o fade da arte do HERO (transicao suave)
        xbmc.executebuiltin('Skin.SetString(smarted_hero_tick,%d)' % (passo % 2))
        if passo in (1, 5) or passo % 30 == 0:
            xbmc.log('SMARTEDTV: hero rotacao %d (%s) posicao=%d'
                     % (passo, modo, _posicao_hero()), getattr(xbmc, 'LOGINFO', 20))


def apply_performance():
    """Cache agressivo + aceleração por hardware (idempotente)."""
    home = xbmcvfs.translatePath('special://home')
    try:
        result = ensure_performance(home, jsonrpc, log)
    except Exception as error:
        log('performance: falhou (%s)' % error, xbmc.LOGWARNING)
        return {'applied': [], 'failed': [], 'advancedsettings': False}
    return result


def repair_until_ready(monitor):
    """Repete o reparo até o perfil ficar completo (ou esgotar as tentativas)."""
    report = None
    for attempt in range(1, REPAIR_ATTEMPTS + 1):
        if monitor.abortRequested():
            break
        report = run_repair(show_dialogs=False)
        if report['ok']:
            return report, attempt
        log('tentativa %d/%d incompleta: %s' % (
            attempt, REPAIR_ATTEMPTS, ', '.join(report['missing']) or 'sem detalhes'),
            xbmc.LOGWARNING)
        if attempt < REPAIR_ATTEMPTS and monitor.waitForAbort(REPAIR_RETRY_SECONDS):
            break
    return report, REPAIR_ATTEMPTS


def _tocando_video():
    try:
        return bool(xbmc.Player().isPlayingVideo())
    except Exception:
        return False


def validar_navegacao_depois_do_boot(monitor):
    """nav-check fora da linha do boot (nunca durante a reproducao)."""
    if monitor.waitForAbort(NAV_CHECK_DELAY):
        return None
    if _tocando_video():
        log('nav-check: adiado (video em reproducao)')
        return None
    try:
        navegacao = rodar_validacao_navegacao(log)
    except Exception as error:  # nunca derrubar o servico por causa do teste
        log('nav-check: falhou (%s)' % error, xbmc.LOGWARNING)
        return None
    if navegacao is not None:
        falhas = [linha for linha in navegacao if linha.startswith('FALHA')]
        log('nav-check: %d destinos testados, %d falha(s)' % (len(navegacao), len(falhas)))
    return navegacao


def main():
    monitor = xbmc.Monitor()
    log('startup: preparando o Brazuca Play')
    xbmc.executebuiltin('Notification(SMARTED, Preparando o conteudo..., 4000)')

    waited = 0
    while waited < WAIT_SECONDS and not monitor.abortRequested():
        if addon_manager_ready():
            break
        if monitor.waitForAbort(POLL_SECONDS):
            return
        waited += POLL_SECONDS

    report, attempts = repair_until_ready(monitor)
    if report is None:
        return

    # o addon precisa aparecer habilitado no Kodi antes da Home abrir
    xbmc.executebuiltin('UpdateLocalAddons()')
    failed = enable_addons(report['required'])
    apply_silencio()
    write_favourites()
    apply_navigation()
    garantir_menu(xbmc, log=log)
    silenciar_avisos_brazuca(log=log)
    # Vikings Repo: registrado no build (assets/addons) ou extraido do payload;
    # o add-on de video e conferido e, se faltar, instalado pelo repositorio.
    repo = ensure_repository(
        xbmcvfs.translatePath('special://home'), PAYLOAD_DIR,
        [xbmcvfs.translatePath('special://xbmc/addons')],
        jsonrpc=jsonrpc, execute=xbmc.executebuiltin, log=log)
    log('vikings: repos=%s plugin=%s falhas=%s'
        % (', '.join(repo['repos']) or 'ausente',
           'ok' if repo['plugin'] else 'pendente',
           ', '.join(repo['falhas']) or 'nenhuma'))
    # OTIMIZACAO DE PLAYBACK: cache + aceleracao por hardware ANTES de qualquer
    # clique em "Assistir" (antes o apply_performance rodava depois do nav-check,
    # que passa por todas as pastas da barra e competia com a Home).
    performance = apply_performance()

    # o teste real dos botoes da barra continua, mas em segundo plano: some da
    # frente da abertura do player e nunca roda durante a reproducao.
    teste_nav = threading.Thread(target=validar_navegacao_depois_do_boot,
                                 args=(monitor,), name='nav-check')
    teste_nav.daemon = True
    teste_nav.start()

    # 1º arranque: skin SMARTEDTV ativa + nós da Home ligados às rotas do addon
    home = xbmcvfs.translatePath('special://home')
    addons_dir = os.path.join(home, 'addons')
    skin = ensure_skin(home, log=log)
    nodes = ensure_home_nodes(
        home_xml_candidates(addons_dir),
        os.path.join(home, 'userdata', 'favourites.xml'),
        log=log)
    atalhos = ensure_shortcuts(log=log)
    log('skin=%s (alterada=%s, instalada=%s), %d nós da Home e %d atalho(s) VIP' % (
        skin['skin'], skin['changed'], skin['installed'], len(nodes['routes']),
        len(atalhos)))

    if report['ok'] and not failed:
        log('pronto após %d tentativa(s): %d addons verificados, %d otimizações' % (
            attempts, len(report['required']), len(performance['applied'])))
        xbmc.executebuiltin(
            'Notification(SMARTED, Conteudo pronto para usar, 4000)')
    else:
        problems = report['missing'] + failed
        log('perfil incompleto: %s' % ', '.join(problems), xbmc.LOGWARNING)
        xbmc.executebuiltin(
            'Notification(SMARTED, Conteudo incompleto: veja userdata/smarted-bootstrap.log, 8000)')

    # ANUNCIOS (AdMob, app org.smartedtv.ads): o pop-up de abertura aparece uma
    # unica vez, logo depois de a Home carregar; o pre-roll entra no inicio de
    # qualquer canal/filme/serie pelo gancho do xbmc.Player.
    smart_ads.iniciar_monitor(log)
    abertura = threading.Thread(target=smart_ads.abertura_depois_do_boot,
                                args=(monitor, log), name='ads-abertura')
    abertura.daemon = True
    abertura.start()

    # PONTO DE RETOMADA: guarda onde o usuario parou e, quando o Kodi vai
    # fechar, salva o ponto e para o player pelo caminho normal (sem travar).
    try:
        import retomar
        retomar.iniciar(log)
        ponto = retomar.ultimo()
        if ponto:
            log('retomada disponivel: %s em %ds' % (ponto['titulo'], ponto['posicao']))
    except Exception as erro:  # noqa: BLE001
        log('retomada indisponivel (%s)' % erro, xbmc.LOGWARNING)

    # o HERO alterna sozinho entre os lancamentos enquanto a Home esta aberta
    rotacao = threading.Thread(target=rotate_hero, args=(monitor,), name='hero-rotate')
    rotacao.daemon = True
    rotacao.start()

    # reavalia de tempos em tempos (addon desabilitado, perfil limpo, etc.)
    while not monitor.abortRequested():
        if monitor.waitForAbort(1800):
            return
        if not monitor.abortRequested():
            run_repair(show_dialogs=False)
            write_favourites()
            apply_navigation()
            ensure_skin(home, log=log)
            ensure_home_nodes(home_xml_candidates(addons_dir),
                              os.path.join(home, 'userdata', 'favourites.xml'), log=log)
            ensure_shortcuts(log=log)


if __name__ == '__main__':
    # nenhuma falha do bootstrap pode deixar o Kodi sem serviço nem trava-lo:
    # tudo fica no log e o app segue funcionando
    try:
        log('startup: servico iniciado (versao %s)' % ADDON.getAddonInfo('version'))
        main()
    except Exception as erro:  # noqa: BLE001
        import traceback
        log('startup: FALHOU (%s)' % erro, xbmc.LOGERROR)
        log(traceback.format_exc(), xbmc.LOGERROR)
