# -*- coding: utf-8 -*-
"""Menu de ajustes da SMARTEDTV.

Abre o diálogo "Deseja assistir sem anúncios?" com:

  1. Sim, quero o VIP (R$ 24,90)  -> checkout da Cakto
  2. Já tenho um código           -> teclado do Kodi -> valida no site
  3. Compartilhar aplicativo      -> folha de compartilhamento do Android
  4. Configurações do Kodi        -> janela normal de ajustes

Funciona igual em TV (controle remoto) e em celular/tablet (toque): tudo é
diálogo nativo do Kodi, então o D-pad navega e o toque seleciona.
"""
from __future__ import absolute_import, unicode_literals

import os
import sys

import xbmc
import xbmcgui

ADDON = xbmcgui  # só para deixar claro que é diálogo nativo

try:
    _aqui = os.path.dirname(os.path.abspath(__file__))
    _servico = os.path.join(_aqui, '..', 'service.smarted.bootstrap')
    if _servico not in sys.path:
        sys.path.append(_servico)
    import vip  # noqa: E402
except Exception:  # noqa: BLE001 - sem o serviço o menu ainda abre
    vip = None


def _status():
    if vip is None:
        return 'Licença indisponível neste aparelho.'
    if vip.ativa():
        dados = vip.estado()
        expira = dados.get('expira') or 'sem prazo'
        return 'VIP ativo (até %s) — sem anúncios.' % expira
    return 'Versão com anúncios.'


def _dialogo():
    opcoes = [
        'Assistir sem anúncios (VIP R$ 24,90)',
        'Já tenho um código de ativação',
        'Compartilhar aplicativo',
        'Configurações do Kodi',
    ]
    if vip is not None and vip.ativa():
        opcoes[0] = 'VIP já ativo — renovar / ver opções'
    titulo = 'Deseja assistir sem anúncios?'
    cabecalho = '%s\n%s' % (titulo, _status())
    escolha = xbmcgui.Dialog().select(cabecalho, opcoes, useDetails=False)
    return escolha


def _ativar():
    teclado = xbmcgui.Dialog().input('Digite o código de ativação', type=xbmcgui.INPUT_ALPHANUM)
    if not teclado:
        return
    xbmcgui.Dialog().notification('SMARTEDTV', 'Validando o código...', xbmcgui.NOTIFICATION_INFO, 4000)
    ok, mensagem = vip.validar(teclado)
    if ok:
        xbmcgui.Dialog().ok('SMARTEDTV VIP', mensagem, 'Os anúncios param na próxima abertura.')
    else:
        xbmcgui.Dialog().ok('SMARTEDTV VIP', mensagem,
                            'Compre um código em pay.cakto.com.br ou tente de novo.')


def main():
    escolha = _dialogo()
    if escolha < 0:
        return
    if escolha == 0:
        if vip is None:
            return
        if vip.ativa():
            renovar = xbmcgui.Dialog().yesno('SMARTEDTV VIP', _status(),
                                             'Deseja renovar agora?')
            if renovar:
                vip.abrir_checkout()
        else:
            if xbmcgui.Dialog().yesno('SMARTEDTV VIP',
                                      'Assinar o Plano VIP por R$ 24,90?',
                                      'Zero anúncios. Pagamento pela Cakto (Pix ou cartão).',
                                      nolabel='Agora não', yeslabel='Ir para o pagamento'):
                vip.abrir_checkout()
    elif escolha == 1:
        if vip is not None:
            _ativar()
    elif escolha == 2:
        if vip is not None:
            vip.compartilhar()
    else:
        xbmc.executebuiltin('ActivateWindow(Settings)')


if __name__ == '__main__':
    main()
