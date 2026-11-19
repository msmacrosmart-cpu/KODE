# -*- coding: utf-8 -*-
"""Ponte entre a skin e o bootstrap.

Dois usos:

* ``RunScript(service.smarted.bootstrap,diagnostico)`` — repete o reparo dos
  addons e mostra o relatório (botão "Diagnóstico Brazuca Play" dos Ajustes).
* ``RunScript(service.smarted.bootstrap,secret-*)`` — contadores do unlock
  secreto da skin. ``Skin.SetSetting`` **não** é um builtin do Kodi (o keymapper
  responde "no such action"), então a aritmética é feita aqui e o resultado é
  gravado com o builtin oficial ``Skin.SetString``, que a skin lê de volta com
  ``Skin.String(...)``.
"""
from __future__ import absolute_import, unicode_literals

import sys

import xbmc
import xbmcgui
import xbmcvfs

import service
from favourites import ensure_favourites
from performance import ensure_performance
from skin_setup import ensure_home_nodes, ensure_skin, home_xml_candidates

# Novo desbloqueio (v1.0.32): 5 entradas consecutivas em Ajustes. Sem cliques
# na logo, sem etapa extra. O resultado é gravado como skin bool
# (``secret_unlocked``), que persiste em addon_data/skin.novatv/settings.xml —
# ou seja, continua liberado depois de reiniciar o app.
SETTINGS_VISITS_TO_UNLOCK = 5
SECRET_LIMITS = {
    'secret_settings_cycle': SETTINGS_VISITS_TO_UNLOCK,
}


def _current(name):
    raw = xbmc.getInfoLabel('Skin.String(%s)' % name) or ''
    try:
        return int(float(raw))
    except ValueError:
        return 0


def _store(name, value):
    xbmc.executebuiltin('Skin.SetString(%s,%d)' % (name, max(0, value)))


def skin_flag(name):
    """Lê um skin bool (Skin.HasSetting) sem depender do tema atual."""
    try:
        return bool(xbmc.getCondVisibility('Skin.HasSetting(%s)' % name))
    except Exception:
        return False


def unlock_advanced():
    xbmc.executebuiltin('Skin.SetBool(secret_unlocked)')
    xbmc.executebuiltin(
        'Notification(SMARTEDTV, Modo avancado liberado, 4000)')


def bump_settings_visits():
    """Conta entradas em Ajustes e libera o modo avançado na 5ª."""
    if skin_flag('secret_unlocked'):
        return SETTINGS_VISITS_TO_UNLOCK
    visits = min(SETTINGS_VISITS_TO_UNLOCK, _current('secret_settings_cycle') + 1)
    _store('secret_settings_cycle', visits)
    if visits >= SETTINGS_VISITS_TO_UNLOCK:
        unlock_advanced()
    return visits


def bump_secret(name):
    """Incrementa (com teto) um contador do unlock secreto."""
    limit = SECRET_LIMITS[name]
    value = min(limit, _current(name) + 1)
    _store(name, value)
    return value


def reset_secret(name):
    _store(name, 0)
    return 0


def handle_skin_command(command):
    """Executa um comando vindo da skin. Retorna True se tratou o comando."""
    if command == 'secret-cycle':
        bump_settings_visits()
        return True
    if command in ('skin', 'skin-setup'):
        home = xbmcvfs.translatePath('special://home')
        ensure_skin(home)
        return bool(ensure_home_nodes(
            home_xml_candidates(os.path.join(home, 'addons')),
            os.path.join(home, 'userdata', 'favourites.xml'))['ok'])
    if command == 'anuncio-teste':
        import smart_ads
        if getattr(smart_ads, 'e_tv', lambda: False)():
            # Na TV o anuncio e video (VAST) tocado pelo player do Kodi. Este
            # botao existe para o dono do app validar em aparelho: liga o modo
            # de teste (tag oficial do Google) e pede um anuncio na hora.
            enviado, detalhe = testar_anuncio_tv()
            xbmcgui.Dialog().notification(
                'SMARTEDTV Anúncios',
                detalhe,
                xbmcgui.NOTIFICATION_INFO if enviado
                else xbmcgui.NOTIFICATION_WARNING, 6000)
            return True
        enviado = smart_ads.testar_anuncio(service.log)
        xbmcgui.Dialog().notification(
            'SMARTEDTV Anúncios',
            'Anúncio solicitado' if enviado else 'Anúncio não solicitado (VIP ou fora do Android)',
            xbmcgui.NOTIFICATION_INFO if enviado else xbmcgui.NOTIFICATION_WARNING, 5000)
        return True
    if command == 'nav-check':
        from menu_smarted import rodar_validacao_navegacao
        rodar_validacao_navegacao(service.log)
        return True
    if command == 'performance':
        return apply_performance()
    if command == 'favoritos':
        return restore_favourites()
    if command in ('secret-click', 'secret-reset',
                   'secret-full-reset', 'secret reset all'):
        # modelo antigo (cliques na logo): desativado, mas aceito sem erro
        reset_secret('secret_settings_cycle')
        xbmc.executebuiltin('Skin.Reset(secret_unlocked)')
        return True
    return False


def testar_anuncio_tv():
    """Pede UM anuncio de video na TV (modo de teste) e devolve (ok, texto).

    E o mesmo caminho do pre-roll real; a diferenca e a tag: sem tag do
    projeto, usa a de TESTE oficial do Google, para o dono do app validar em
    aparelho sem gerar trafego invalido.
    """
    import smart_ads
    antes = ''
    try:
        antes = xbmc.getInfoLabel('Window(10000).Property(smartedtv.vast.teste)')
        xbmc.executebuiltin('SetProperty(smartedtv.vast.teste,1,tv)')
    except Exception:
        pass
    try:
        recibo = smart_ads.testar_anuncio_video(service.log)
    finally:
        if not (antes or '').strip():
            try:
                xbmc.executebuiltin(
                    'ClearProperty(smartedtv.vast.teste,tv)')
            except Exception:
                pass
    if recibo.get('exibido'):
        return True, 'Anúncio de vídeo exibido (%s s)' % recibo.get('segundos', '?')
    motivo = recibo.get('motivo', '?')
    textos = {
        'sem-tag': 'Sem tag VAST configurada',
        'tag-sem-resposta': 'A tag VAST não respondeu (rede)',
        'vast-sem-criativo': 'A tag não trouxe vídeo de anúncio',
        'nao-iniciou': 'O player não abriu o vídeo do anúncio',
        'player-recusou': 'O Kodi recusou o vídeo do anúncio',
    }
    return False, textos.get(motivo, 'Anúncio não exibido (%s)' % motivo)


def restore_favourites():
    """Recria os atalhos do Brazuca Play em userdata/favourites.xml."""
    home = xbmcvfs.translatePath('special://home')
    added = ensure_favourites(home, service.log)
    if added:
        xbmcgui.Dialog().ok('SMARTEDTV', 'Atalhos adicionados aos favoritos:\n%s' %
                            '\n'.join(added))
    else:
        xbmcgui.Dialog().ok('SMARTEDTV', 'Os atalhos do Brazuca Play já estão nos favoritos.')
    return True


def apply_performance():
    """Reaplica cache/aceleração e mostra o que foi aceito pelo Kodi."""
    home = xbmcvfs.translatePath('special://home')
    result = ensure_performance(home, service.jsonrpc, service.log)
    linhas = ['Cache: %s' % ('gravado' if result['advancedsettings'] else 'preservado')]
    linhas.append('Aplicados: %d' % len(result['applied']))
    if result['failed']:
        linhas.append('Recusados: %s' % ', '.join(result['failed'][:6]))
    xbmcgui.Dialog().ok('SMARTEDTV', '\n'.join(linhas))
    return True


def show_report():
    progress = xbmcgui.DialogProgress()
    progress.create('Brazuca Play', 'Verificando addons e dependências...')
    progress.update(30, 'Conferindo addons e dependências...')
    report = service.run_repair(show_dialogs=False)
    progress.update(100, 'Verificação concluída')
    progress.close()
    if report['ok']:
        xbmcgui.Dialog().ok(
            'Brazuca Play',
            'OK: %d addons verificados.\nRestaurados agora: %s' % (
                len(report['required']),
                ', '.join(report['repaired']) or 'nenhum'))
    else:
        xbmcgui.Dialog().ok(
            'Brazuca Play',
            'Pendências: %s\n\nRelatório completo: userdata/smarted-bootstrap.log' % (
                ', '.join(report['missing']) or 'nenhuma'))


if __name__ == '__main__':
    arguments = sys.argv[1:]
    command = arguments[0].strip().lower() if arguments else ''
    if not handle_skin_command(command):
        show_report()
