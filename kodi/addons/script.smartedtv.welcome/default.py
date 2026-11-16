# -*- coding: utf-8 -*-
"""Tela de entrada do SMARTEDTV — interface do ZIP, aberta ANTES da Home.

Interface e 100% a do ZIP (`resources/skins/Default/1080i/DialogWelcome.xml` +
`resources/skins/Default/media/`, sem nenhuma alteracao visual). Este arquivo so
liga a tela ao ciclo de inicializacao do aplicativo:

* e chamado pelo `Startup.xml` da skin ativa (janela 12999), que o Kodi abre no
  lugar da Home durante `CApplication::Initialize`. Enquanto esse XML estiver em
  uso, a Home (10000) ainda nao foi criada;
* mantem a janela viva no lugar de `ReplaceWindow($INFO[System.StartupWindow])`,
  entao o Kodi termina de inicializar com a tela na frente;
* quando o usuario conclui, a janela fecha e a Home e aberta.

As acoes reutilizam o que ja existe no projeto (`vip.py` do
service.smarted.bootstrap) e nao inventam API, endpoint nem credencial.
"""
from __future__ import absolute_import, unicode_literals

import os
import sys

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

ADDON_ID = 'script.smartedtv.welcome'
SERVICO = 'service.smarted.bootstrap'
XML_RELATIVO = 'resources/skins/Default/1080i/DialogWelcome.xml'
MARCA_ABERTA = 'smartedtv.welcome.ativa'
# Comando usado pelo proprio Startup.xml das skins do projeto para ir a Home.
FLUXO_INTERFACE_PRINCIPAL = 'ReplaceWindow($INFO[System.StartupWindow])'


def _log(mensagem, nivel=None):
    try:
        xbmc.log('[%s] %s' % (ADDON_ID, mensagem),
                 xbmc.LOGINFO if nivel is None else nivel)
    except Exception:
        pass


def _pasta_do_servico():
    """Pasta real do service.smarted.bootstrap (no APK Android fica em xbmc)."""
    # 1) banco de addons: e o caminho oficial, e o addon ja esta habilitado
    try:
        pasta = xbmcaddon.Addon(SERVICO).getAddonInfo('path')
        if pasta:
            return xbmcvfs.translatePath(pasta)
    except Exception:
        pass
    # 2) caminhos conhecidos (addons embarcados no APK usam special://xbmc)
    for raiz in ('special://xbmc/addons/', 'special://home/addons/',
                 'special://profile/addons/'):
        try:
            candidato = xbmcvfs.translatePath(raiz + SERVICO)
            if xbmcvfs.exists(candidato):
                return candidato
        except Exception:
            continue
    return None


def _vip():
    """Modulo de licenca VIP que ja existe no projeto (sem duplicar logica)."""
    pasta = _pasta_do_servico()
    if not pasta:
        _log('service.smarted.bootstrap nao encontrado', xbmc.LOGWARNING)
        return None
    try:
        if pasta not in sys.path:
            sys.path.append(pasta)
        import vip  # modulo real do service.smarted.bootstrap
        return vip
    except Exception as erro:
        _log('modulo vip indisponivel: %s' % erro, xbmc.LOGWARNING)
        return None


def _pasta_da_tela():
    """Pasta do addon, preferindo o caminho do proprio arquivo (sem banco de addons)."""
    arquivo = globals().get('__file__')
    if arquivo:
        try:
            candidato = os.path.dirname(xbmcvfs.translatePath(arquivo))
            if xbmcvfs.exists(os.path.join(candidato, XML_RELATIVO)):
                return candidato
        except Exception:
            pass
    for raiz in ('special://xbmc/addons/', 'special://home/addons/'):
        try:
            candidato = xbmcvfs.translatePath(raiz + ADDON_ID)
            if xbmcvfs.exists(os.path.join(candidato, XML_RELATIVO)):
                return candidato
        except Exception:
            continue
    try:
        return xbmcvfs.translatePath(
            xbmcaddon.Addon(ADDON_ID).getAddonInfo('path'))
    except Exception:
        return None


def _sinalizar_abertura():
    try:
        xbmcgui.Window(10000).setProperty(MARCA_ABERTA, '1')
    except Exception:
        pass


class WelcomeDialog(xbmcgui.WindowXMLDialog):
    """Mesmo dialogo do ZIP; aqui so encaminhamos as acoes para o projeto."""

    def onInit(self):
        # a tela realmente abriu: cancela o seguro de 30 s do Startup.xml para a
        # Home nunca aparecer atras da tela de entrada
        try:
            xbmc.executebuiltin('CancelAlarm(smartedtv_entrada_seguro,silent)')
        except Exception:
            pass
        self.saiu = False
        _sinalizar_abertura()
        _log('tela de entrada carregada (antes da Home)')
        try:
            self.setFocusId(310)
        except Exception:
            pass

    # --- acoes ligadas ao que ja existe no projeto -----------------------
    def _abrir_checkout(self):
        vip = _vip()
        if vip is not None and vip.abrir_checkout():
            _log('checkout aberto pelo fluxo existente (vip.abrir_checkout)')
            return
        _log('checkout: fluxo existente indisponivel', xbmc.LOGWARNING)

    def _compartilhar(self):
        vip = _vip()
        if vip is not None and vip.compartilhar():
            _log('compartilhamento aberto (vip.compartilhar)')
            return
        _log('compartilhamento: fluxo existente indisponivel', xbmc.LOGWARNING)

    def _ativar_codigo(self):
        """Le o controle 310 e valida com o servidor pelo modulo vip do projeto."""
        vip = _vip()
        if vip is None:
            xbmcgui.Dialog().ok(
                'SMARTEDTV VIP',
                'A ativacao por codigo nao esta disponivel neste aparelho.')
            return
        try:
            campo = self.getControl(310)
            codigo = (campo.getText() or '').strip()
        except Exception:
            codigo = ''
        if not codigo:
            codigo = xbmcgui.Dialog().input(
                'Digite o codigo de ativacao', type=xbmcgui.INPUT_ALPHANUM)
        if not codigo:
            return
        xbmcgui.Dialog().notification(
            'SMARTEDTV', 'Validando o codigo...', xbmcgui.NOTIFICATION_INFO, 3000)
        ok, mensagem = vip.validar(codigo)
        if ok:
            xbmcgui.Dialog().ok(
                'SMARTEDTV VIP', mensagem,
                'Os anuncios param na proxima abertura do aplicativo.')
            _log('codigo ativado; licenca gravada em vip.json')
        else:
            xbmcgui.Dialog().ok(
                'SMARTEDTV VIP', mensagem,
                'Compre um codigo em pay.cakto.com.br ou tente de novo.')
            _log('codigo recusado: %s' % mensagem, xbmc.LOGWARNING)

    def _modo_gratuito(self):
        """Fecha a entrada e abre a Home (versao com anuncios, como ja e hoje)."""
        self._sair()

    def _continuar(self):
        self._sair()

    def _sair(self):
        """Fecha a janela; a Home e aberta pelo chamador, depois do doModal."""
        self.saiu = True
        self.close()

    # --- eventos ---------------------------------------------------------
    def onClick(self, control_id):
        if control_id == 312:                 # Abrir o modal de confirmacao
            self.setProperty('show_free_dialog', 'true')
            try:
                self.setFocusId(905)
            except Exception:
                pass
        elif control_id == 905:               # Voltar do modal
            self.clearProperty('show_free_dialog')
            try:
                self.setFocusId(312)
            except Exception:
                pass
        elif control_id == 906:               # Confirmar modo gratuito
            self._modo_gratuito()
        elif control_id == 120:               # Abrir checkout
            self._abrir_checkout()
        elif control_id == 121:               # Compartilhar link
            self._compartilhar()
        elif control_id == 311:               # Ativar codigo VIP
            self._ativar_codigo()
        elif control_id in (130, 131):
            # Seletor visual de aparelho do ZIP: nao existe fluxo equivalente.
            _log('seletor de aparelho: sem fluxo no projeto', xbmc.LOGWARNING)

    def onAction(self, action):
        if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
            if self.getProperty('show_free_dialog') == 'true':
                self.clearProperty('show_free_dialog')
                try:
                    self.setFocusId(312)
                except Exception:
                    pass
                return
            self._continuar()


def _ir_para_home(motivo=''):
    if motivo:
        _log('abrindo a Home: %s' % motivo, xbmc.LOGWARNING)
    # o seguro so serve enquanto a tela nao assumiu; agora quem manda e daqui
    try:
        xbmc.executebuiltin('CancelAlarm(smartedtv_entrada_seguro,silent)')
    except Exception:
        pass
    try:
        xbmc.executebuiltin(FLUXO_INTERFACE_PRINCIPAL)
    except Exception as erro:
        _log('falha ao abrir a Home: %s' % erro, xbmc.LOGERROR)


def abrir_tela_entrada():
    """Abre o dialogo do ZIP no lugar da Home. Devolve True quando abriu."""
    # O seguro de 30 s do Startup.xml continua ativo de proposito: ele so e
    # cancelado quando a tela realmente aparece (onInit) ou quando saimos para
    # a Home. Assim, se o Python travar antes de desenhar, o Kodi ainda abre a
    # Home em 30 s em vez de ficar parado na janela de startup.
    pasta = _pasta_da_tela()
    if not pasta:
        _log('pasta da tela nao encontrada', xbmc.LOGERROR)
        _ir_para_home('tela de entrada indisponivel')
        return False
    try:
        janela = WelcomeDialog('DialogWelcome.xml', pasta, 'Default', '1080i')
    except Exception as erro:
        _log('falha ao montar a tela: %s' % erro, xbmc.LOGERROR)
        _ir_para_home('tela de entrada indisponivel')
        return False
    try:
        janela.doModal()
    except Exception as erro:
        _log('falha ao exibir a tela: %s' % erro, xbmc.LOGERROR)
        _ir_para_home('tela de entrada indisponivel')
        return False
    # A janela ja saiu de cena (doModal retornou): agora sim a Home.
    _ir_para_home()
    return True


if __name__ == '__main__':
    abrir_tela_entrada()
