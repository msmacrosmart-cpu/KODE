# -*- coding: utf-8 -*-
"""Serviço de boot do SMARTED-TV.

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
from favourites import ensure_favourites
from performance import ensure_performance
from menu_smarted import garantir_menu, rodar_validacao_navegacao, silenciar_avisos_brazuca
import smart_ads
from skin_setup import ensure_home_nodes, ensure_skin, home_xml_candidates

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
PAYLOAD_DIR = os.path.join(ADDON_PATH, 'payload')

# O perfil semeado pode ainda estar sendo copiado no primeiro boot: tentamos
# o reparo várias vezes antes de desistir (nada de esperar 90s para começar).
# TV box/stick com armazenamento lento: 20 s esperando o banco de addons era
# tempo de TELA SEM INTERFACE (o Startup ja saiu e a Home ainda nao veio). A
# espera cai para 8 s; se o gerenciador nao responder nesse tempo, o boot segue
# para a Home e o preparo termina em segundo plano (que ja existia).
WAIT_SECONDS = 8
POLL_SECONDS = 5
REPAIR_ATTEMPTS = 6
REPAIR_RETRY_SECONDS = 5
# Projetor/box lento: o reparo (extrair addons do zip) pode demorar bem mais
# que a TV. Nesse aparelho a Home tem de abrir MESMO ASSIM, com o conteudo
# aparecendo depois - antes o boot ficava esperando o reparo e o usuario via
# uma tela parada em "Carregando" (ou preta).
BOOT_LENTO_SEGUNDOS = 25
# Depois que a Home esta na tela, o reparo continua em segundo plano.
REPARO_EM_SEGUNDO_PLANO = True
# Uma unica escrita de guisettings.xml no fim do boot (ver _adiar_persistencia).
GUISETTINGS = 'guisettings.xml'
UISOUNDS_SILENCIO = 'resource.uisounds.silencio'
CORE_ADDONS = ('script.smartedtv.welcome', 'service.smarted.bootstrap',
               'plugin.video.smarted', UISOUNDS_SILENCIO)


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


# Quanto esperar o Kodi registrar no banco do addon que acabou de ser
# extraido. Em TV box/stick (armazenamento interno lento) o UpdateLocalAddons
# leva mais que no celular.
ADDON_SCAN_SECONDS = 12
ADDON_SCAN_POLL = 1


def addon_registrado(addon_id):
    """O addon ja aparece no banco do Kodi (e habilitado)?"""
    response = jsonrpc('Addons.GetAddonDetails',
                       {'addonid': addon_id, 'properties': ['enabled']})
    detalhe = (response or {}).get('result', {}).get('addon') or {}
    return bool(detalhe.get('enabled'))


def esperar_addon_registrado(addon_id, limite=ADDON_SCAN_SECONDS, monitor=None):
    """Espera o banco de addons enxergar ``addon_id`` (sem prender o boot).

    O ``UpdateLocalAddons()`` e assincrono: pedir
    ``Addons.SetAddonEnabled`` no mesmo instante devolve erro porque o addon
    ainda nao existe para o Kodi - era o "addon com erro" em TV box/stick logo
    depois de uma atualizacao, com o pacote ja extraido no perfil.

    A espera usa ``monitor.waitForAbort`` quando ha monitor (o mesmo padrao do
    resto do bootstrap: acorda na hora se o app estiver saindo).
    """
    waited = 0
    while waited < limite:
        if addon_registrado(addon_id):
            return True
        if monitor is not None:
            try:
                if monitor.waitForAbort(ADDON_SCAN_POLL):
                    return addon_registrado(addon_id)
            except Exception:
                time.sleep(ADDON_SCAN_POLL)
        else:
            time.sleep(ADDON_SCAN_POLL)
        waited += ADDON_SCAN_POLL
    return addon_registrado(addon_id)


def enable_addons(addon_ids, esperar=False, monitor=None, recem_instalados=None):
    """Habilita os addons no Kodi (idempotente) e devolve os que falharam.

    ``esperar=True`` faz uma pausa (com confirmacao no banco de addons) so
    para os addons em ``recem_instalados`` - os que ESTE boot acabou de
    extrair para o perfil. E neles que o ``SetAddonEnabled`` falhava em TV
    box/stick: o zip era descompactado e o pedido de habilitar chegava antes de
    o Kodi reler a pasta de addons. Addon que ja estava instalado nao precisa
    de espera nenhuma, entao o boot nao fica mais lento por causa disso.
    """
    failed = []
    recem = set(recem_instalados or ())
    jsonrpc('Addons.SetAddonEnabled', {'addonid': 'metadata.local', 'enabled': True})
    xbmc.executebuiltin('UpdateLocalAddons()')
    for addon_id in addon_ids:
        if esperar and addon_id in recem and not esperar_addon_registrado(
                addon_id, monitor=monitor):
            # Ainda nao apareceu no banco: registra e tenta habilitar mesmo
            # assim (o SetAddonEnabled pode funcionar quando o addon chega).
            log('addon %s ainda nao aparece no banco apos %d s; tentando habilitar'
                % (addon_id, ADDON_SCAN_SECONDS), xbmc.LOGWARNING)
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


def _remover_arvore(caminho):
    try:
        import xbmcvfs
        pastas, arquivos = xbmcvfs.listdir(caminho)
        for nome in arquivos:
            xbmcvfs.delete(caminho + '/' + nome)
        for nome in pastas:
            _remover_arvore(caminho + '/' + nome)
        xbmcvfs.rmdir(caminho)
    except Exception:
        pass


def limpar_estagios_de_seed():
    """Apaga somente estagios temporarios de um seed interrompido.

    O seed Java publica o perfil por rename atomico. Se o processo morrer no
    meio, sobra ``.smarted-seed-<uuid>`` no diretorio do usuario. O proximo
    boot remove esses restos; o perfil publicado e o addon_data nunca entram
    nessa varredura.
    """
    removidos = 0
    try:
        import xbmcvfs
        raiz = xbmcvfs.translatePath('special://profile')
        pastas, arquivos = xbmcvfs.listdir(raiz)
        for nome in pastas + arquivos:
            if not nome.startswith('.smarted-seed-'):
                continue
            caminho = raiz.rstrip('/') + '/' + nome
            _remover_arvore(caminho)
            if not xbmcvfs.exists(caminho):
                removidos += 1
        if removidos:
            log('seed: %d estagio(s) temporario(s) removido(s)' % removidos)
        return removidos
    except Exception as erro:
        log('seed: varredura de estagios falhou (%s)' % erro,
            xbmc.LOGWARNING)
        return 0


def limpar_estado_interface():
    """Remove marcas de uma sessao anterior da tela de entrada.

    Quit/reabertura nao podem herdar ``saiu``/``home=ok``/``voltar`` presos na
    janela 10000; a tela nova precisa decidir o boot do zero. Nao limpa
    ``smartedtv.welcome.ativa``: o vigia do Startup.xml conta com ela.
    """
    limpar_estagios_de_seed()
    try:
        import xbmcgui
        janela = xbmcgui.Window(10000)
        for chave in ('smartedtv.welcome.saiu', 'smartedtv.welcome.home',
                      'smartedtv.welcome.voltar',
                      'smartedtv.welcome.saindo'):
            try:
                janela.clearProperty(chave)
            except Exception:
                pass
        log('interface: marcas antigas da tela de entrada limpas')
        return True
    except Exception as erro:
        log('interface: nao foi possivel limpar marcas (%s)' % erro,
            xbmc.LOGWARNING)
        return False


def _janela_atual():
    try:
        return (xbmc.getInfoLabel('System.CurrentWindow') or '').strip().lower()
    except Exception:
        return ''


def esperar_addons_manager(monitor, log=None):
    """Espera o banco de addons do Kodi responder, sem prender o boot.

    Devolve True quando respondeu dentro de ``WAIT_SECONDS``. Em projetor com
    armazenamento lento esse passo pode consumir o tempo todo, entao quem chama
    pode seguir para a Home e terminar o preparo depois.
    """
    waited = 0
    while waited < WAIT_SECONDS:
        if monitor.abortRequested():
            return False
        if addon_manager_ready():
            return True
        if monitor.waitForAbort(POLL_SECONDS):
            return False
        waited += POLL_SECONDS
    if log:
        log('addons: gerenciador nao respondeu em %d s; seguindo para a Home'
            % WAIT_SECONDS, xbmc.LOGWARNING)
    return False


def garantir_interface_inicial(monitor, log=None, espera=25):
    """Recupera um boot sem janela (tela preta) sem tocar no processo.

    O Startup.xml normal abre a tela de entrada. Se o Kodi reutilizou um estado
    antigo e nao abriu nenhuma janela, este vigia pede a tela de entrada e, se
    ela nao vier, libera a Home. Nao apaga perfil, VIP, cache nem configuracoes.
    """
    limite = time.time() + max(8, int(espera))
    while time.time() < limite:
        if monitor.abortRequested():
            return False
        atual = _janela_atual()
        try:
            if xbmc.getCondVisibility('Window.IsActive(Home)'):
                return True
        except Exception:
            pass
        if atual in ('home', 'startup', 'startupwindow'):
            return True
        try:
            if monitor.waitForAbort(1):
                return False
        except Exception:
            time.sleep(1)
    log('boot: nenhuma janela ativa em %d s; reabrindo a tela de entrada'
        % espera, xbmc.LOGWARNING)
    xbmc.executebuiltin('RunScript(script.smartedtv.welcome)')
    limite = time.time() + 12
    while time.time() < limite:
        try:
            if xbmc.getCondVisibility('Window.IsActive(Home)'):
                return True
        except Exception:
            pass
        if _janela_atual() in ('home', 'startup', 'startupwindow'):
            return True
        try:
            if monitor.waitForAbort(1):
                return False
        except Exception:
            time.sleep(1)
    log('boot: a tela de entrada nao veio; liberando a Home', xbmc.LOGERROR)
    xbmc.executebuiltin('ActivateWindow(Home)')
    return False


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
        # Fica so no log: e um detalhe de manutencao do perfil, nao uma acao
        # do usuario, e a notificacao aparecia por cima da tela de entrada.
        log('atalhos adicionados aos favoritos (%d)' % len(added))
    return added


def apply_navigation():
    """Descobre as pastas reais do Brazuca e publica a barra superior.

    A descoberta (menu raiz do addon por Files.GetDirectory) e feita pelo
    plugin.video.smarted; aqui disparamos com force=1 para o boot sempre
    refazer o mapeamento e gravar o cache do dia.
    """
    xbmc.executebuiltin('RunPlugin(plugin://plugin.video.smarted/?route=sync-nav)')


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
                              'Control.HasFocus(9303) | Control.HasFocus(9203) | System.HasActiveModalDialog' % HERO_CONTROL):
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
    return 'sem movimento'  # nunca roubar o foco para simular uma seta



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
            xbmc.log('SMARTED-TV: hero rotacao %d (%s) posicao=%d'
                     % (passo, modo, _posicao_hero()), getattr(xbmc, 'LOGINFO', 20))


def apply_performance():
    """Cache agressivo + aceleração por hardware (idempotente).

    O nome do aparelho decide o perfil de video: projetor usa MediaCodec sem
    Surface (evita o canal com audio e tela preta); TV/box/stick mantem Surface.
    """
    home = xbmcvfs.translatePath('special://home')
    try:
        nome = xbmc.getInfoLabel('System.FriendlyName') or ''
    except Exception:
        nome = ''
    try:
        result = ensure_performance(home, jsonrpc, log, nome_dispositivo=nome)
    except Exception as error:
        log('performance: falhou (%s)' % error, xbmc.LOGWARNING)
        return {'applied': [], 'failed': [], 'advancedsettings': False,
                'projetor': False}
    if result.get('projetor'):
        log('video: projetor detectado em %r; Surface desligado e '
            'ajuste de taxa de quadros desativado' % nome)
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


def _liberar_home_agora(log=None):
    """Abre a Home sem esperar o preparo terminar (devolve (abriu, tentativas))."""
    for tentativa in (1, 2, 3):
        if log:
            log('boot: liberando a Home (tentativa %d)' % tentativa)
        try:
            xbmc.executebuiltin('ActivateWindow(Home)')
        except Exception as erro:
            if log:
                log('boot: ActivateWindow(Home) falhou (%s)' % erro,
                    xbmc.LOGWARNING)
        time.sleep(1.0)
        atual = _janela_atual()
        if atual in ('home', '10000'):
            return True, tentativa, atual
    try:
        xbmc.executebuiltin('ReplaceWindow(Home)')
    except Exception:
        pass
    time.sleep(0.8)
    return _janela_atual() in ('home', '10000'), 3, _janela_atual()


def _preparar_em_segundo_plano(monitor):
    """Termina addons/perfil/favoritos/menu/skin com a Home ja na tela."""
    def preparar():
        try:
            # A HOME JA ESTA NA TELA. Antes de mexer em addon (que pode demorar
            # em TV box/stick), espera o gerenciador responder: extrair pacote
            # com o banco de addons ainda montando era o "addon com erro" e a
            # Home vazia nesses aparelhos. Aqui a espera NAO atrasa a Home.
            if not esperar_addons_manager(monitor, log=log):
                log('preparo: gerenciador de addons nao respondeu; tentando o '
                    'reparo mesmo assim', xbmc.LOGWARNING)
            report, attempts = repair_until_ready(monitor)
            if report is None:
                return
            # O advancedsettings.xml e o cache de rede/video precisam valer ja
            # NESTE boot (nao no proximo): e o que evita a Home "carregando
            # para sempre" em box/stick e o canal engasgado. Idempotente.
            apply_performance()
            xbmc.executebuiltin('UpdateLocalAddons()')
            # Espera o banco enxergar cada addon recem-extraido (TV box/stick
            # levam mais que o celular): sem isso o SetAddonEnabled devolvia
            # erro e o addon ficava desabilitado, com a Home sem conteudo.
            failed = enable_addons(report['required'], esperar=True,
                                   monitor=monitor,
                                   recem_instalados=report['repaired'])
            write_favourites()
            garantir_menu(xbmc, log=log)
            silenciar_avisos_brazuca(log=log)
            apply_performance()
            home = xbmcvfs.translatePath('special://home')
            ensure_skin(home, log=log)
            apply_navigation()
            ensure_home_nodes(home_xml_candidates(os.path.join(home, 'addons')),
                              os.path.join(home, 'userdata', 'favourites.xml'),
                              log=log)
            if report['ok'] and not failed:
                log('pronto (em segundo plano) após %d tentativa(s)' % attempts)
                xbmc.executebuiltin(
                    'Notification(SMARTED, Conteudo pronto para usar, 4000)')
            else:
                log('perfil incompleto (segundo plano): %s'
                    % ', '.join(report['missing'] + failed), xbmc.LOGWARNING)
        except Exception as erro:  # nunca derrubar o app por causa do preparo
            log('preparo em segundo plano falhou: %s' % erro, xbmc.LOGWARNING)

    thread = threading.Thread(target=preparar, name='preparo-pos-home',
                              daemon=True)
    thread.start()
    return thread


def main():
    monitor = xbmc.Monitor()
    limpar_estado_interface()
    try:
        vigia = threading.Thread(target=garantir_interface_inicial,
                                 args=(monitor, log), name='boot-interface')
        vigia.daemon = True
        vigia.start()
    except Exception as erro:
        log('boot: nao foi possivel iniciar o vigia da interface (%s)' % erro,
            xbmc.LOGWARNING)
    log('startup: preparando o Brazuca Play')
    # A tela de entrada e um addon separado. Se o banco de addons do aparelho
    # ficou com ele desabilitado numa atualizacao, o Startup.xml chama
    # RunScript e nada aparece (tela preta). Habilita os addons do app antes.
    try:
        # Caminho de BOOT: nao espera o banco de addons (a Home ainda vai
        # abrir). A espera com confirmacao fica nos caminhos de reparo, que
        # rodam com a Home ja na tela - ver `enable_addons`.
        enable_addons(CORE_ADDONS)
    except Exception as erro:
        log('addons: falha ao habilitar os addons do app (%s)' % erro,
            xbmc.LOGWARNING)
    xbmc.executebuiltin('Notification(SMARTED, Preparando o conteudo..., 4000)')

    # Anuncios: o gancho de pre-roll precisa existir ANTES de qualquer video
    # (canal/filme/serie). Sem esta chamada o MonitorPreRoll nunca era criado e
    # nenhum anuncio era pedido, em nenhum aparelho. O app-open espera a Home.
    try:
        # Publica o perfil do aparelho (celular x TV/box/projetor/stick) antes
        # de qualquer gatilho: e ele que decide AdMob ou video VAST.
        smart_ads.publicar_perfil(log)
    except Exception as erro:
        log('ads: nao foi possivel identificar o dispositivo (%s)' % erro,
            xbmc.LOGWARNING)
    try:
        smart_ads.iniciar_monitor(log)
        abertura = threading.Thread(target=smart_ads.abertura_depois_do_boot,
                                    args=(monitor, log), name='ads-abertura')
        abertura.daemon = True
        abertura.start()
    except Exception as erro:  # nunca derrubar o boot por causa de anuncio
        log('ads: nao foi possivel iniciar os gatilhos (%s)' % erro,
            xbmc.LOGWARNING)

    pronto = esperar_addons_manager(monitor, log=log)
    if monitor.abortRequested():
        return

    # Projetor/box lento: NAO segurar a Home esperando a extracao dos addons.
    # Abre a Home agora (a skin ja desenha, o menu aparece) e termina o reparo
    # numa thread. Sem isso o aparelho lento ficava parado na espera do boot.
    if not pronto and REPARO_EM_SEGUNDO_PLANO:
        log('boot: addons ainda carregando; abrindo a Home e concluindo depois',
            xbmc.LOGWARNING)
        _, _, _ = _liberar_home_agora()
        _preparar_em_segundo_plano(monitor)
        return

    report, attempts = repair_until_ready(monitor)
    if report is None:
        return

    # o addon precisa aparecer habilitado no Kodi antes da Home abrir
    xbmc.executebuiltin('UpdateLocalAddons()')
    failed = enable_addons(report['required'])
    apply_silencio()
    write_favourites()
    garantir_menu(xbmc, log=log)
    silenciar_avisos_brazuca(log=log)
    performance = apply_performance()

    # 1º arranque: skin SMARTEDTV ativa + nós da Home ligados às rotas do addon
    home = xbmcvfs.translatePath('special://home')
    addons_dir = os.path.join(home, 'addons')
    skin = ensure_skin(home, log=log)
    apply_navigation()  # depois de fixar a skin, publica a barra antes dos nós
    nodes = ensure_home_nodes(
        home_xml_candidates(addons_dir),
        os.path.join(home, 'userdata', 'favourites.xml'),
        log=log)
    log('skin=%s (alterada=%s, instalada=%s) e %d nós da Home' % (
        skin['skin'], skin['changed'], skin['installed'], len(nodes['routes'])))

    if report['ok'] and not failed:
        log('pronto após %d tentativa(s): %d addons verificados, %d otimizações' % (
            attempts, len(report['required']), len(performance['applied'])))
        xbmc.executebuiltin(
            'Notification(SMARTED, Conteudo pronto para usar, 4000)')
    else:
        # Perfil incompleto NAO vira aviso na tela: o texto tecnico ("veja
        # userdata/smarted-bootstrap.log") interrompia o uso na TV, onde o
        # usuario nao tem como abrir log nenhum. O reparo continua rodando em
        # segundo plano e o problema fica registrado no log interno; a Home
        # ja esta liberada (_liberar_home_agora) e os addons que faltam sao
        # recriados no proximo ciclo de reparo.
        problems = report['missing'] + failed
        log('perfil incompleto: %s' % ', '.join(problems), xbmc.LOGWARNING)

    # o HERO alterna sozinho entre os lancamentos enquanto a Home esta aberta
    def checar_navegacao():
        # Files.GetDirectory nos 7 destinos e caro (rede): o boot nao espera.
        if monitor.waitForAbort(45):
            return
        try:
            rodar_validacao_navegacao(log)
        except Exception as erro:  # noqa: BLE001
            log('nav-check: falhou (%s)' % erro, xbmc.LOGWARNING)

    threading.Thread(target=checar_navegacao, name='nav-check', daemon=True).start()

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


if __name__ == '__main__':
    main()
