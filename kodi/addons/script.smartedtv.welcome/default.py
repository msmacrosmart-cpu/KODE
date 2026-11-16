# -*- coding: utf-8 -*-
"""Tela de entrada do SMARTEDTV — interface do pacote `smartedtv-src`, aberta
ANTES da Home.

O desenho e o do pacote entregue (medido do CSS e reproduzido em
`resources/skins/Default/1080i/DialogWelcome.xml`, com as texturas e os QR Codes
originais). Este arquivo so liga os controles ao que ja existe no app:

* e chamado pelo `Startup.xml` da skin ativa (janela 12999), que o Kodi abre no
  lugar da Home durante `CApplication::Initialize` — a Home (10000) ainda nao
  foi criada e so e aberta quando a tela conclui;
* os botoes usam o modulo `vip.py` do `service.smarted.bootstrap` que ja vem no
  APK: validar codigo, abrir checkout, compartilhar, checar atualizacao e
  abrir URLs. Nenhuma API, endpoint ou credencial nova.

Controles desta tela:
    310 campo do codigo   311 ativar
    120 checkout          121 compartilhar link      122 baixar APK
    123 atualizar aplicativo                       312 continuar com anuncios
    905/906/955 dialogos
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
# Comando usado pelo proprio Startup.xml das skins para ir a Home.
FLUXO_INTERFACE_PRINCIPAL = 'ReplaceWindow($INFO[System.StartupWindow])'

# Propriedades da janela usadas pelos grupos do XML (dialogos).
PROP_DIALOGO = 'welcome_dialog'
PROP_TITULO = 'welcome_status_title'
PROP_TEXTO = 'welcome_status_text'
PROP_OK = 'welcome_status_ok'


def _log(mensagem, nivel=None):
    try:
        xbmc.log('[%s] %s' % (ADDON_ID, mensagem),
                 xbmc.LOGINFO if nivel is None else nivel)
    except Exception:
        pass


def _pasta_do_servico():
    """Pasta real do service.smarted.bootstrap (no APK Android fica em xbmc)."""
    try:
        pasta = xbmcaddon.Addon(SERVICO).getAddonInfo('path')
        if pasta:
            return xbmcvfs.translatePath(pasta)
    except Exception:
        pass
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
    """Pasta do addon, preferindo o caminho do proprio arquivo."""
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
    """Mesma tela do pacote; aqui so encaminhamos as acoes para o projeto."""

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.saiu = False

    # --- dialogos ---------------------------------------------------------
    def _dialogo(self, titulo, texto, ok='Entendi'):
        for chave, valor in ((PROP_TITULO, titulo), (PROP_TEXTO, texto),
                             (PROP_OK, ok)):
            self.setProperty(chave, valor)
        self.setProperty(PROP_DIALOGO, 'status')
        try:
            self.setFocusId(955)
        except Exception:
            pass

    def _fechar_dialogo(self, foco=311):
        self.clearProperty(PROP_DIALOGO)
        try:
            self.setFocusId(foco)
        except Exception:
            pass

    # --- acoes ligadas ao que ja existe no projeto -----------------------
    def _abrir_checkout(self):
        vip = _vip()
        if vip is not None and vip.abrir_checkout():
            _log('checkout aberto pelo fluxo existente (vip.abrir_checkout)')
            return
        self._dialogo('Checkout indisponível',
                      'Não consegui abrir o checkout neste aparelho. '
                      'Aponte a câmera para o QR Code ao lado.')

    def _compartilhar(self):
        vip = _vip()
        if vip is not None and vip.compartilhar():
            _log('compartilhamento aberto (vip.compartilhar)')
            return
        self._dialogo('Compartilhamento indisponível',
                      'Não consegui abrir o compartilhamento neste aparelho.')

    def _baixar_apk(self):
        vip = _vip()
        if vip is None:
            self._dialogo('Download indisponível',
                          'Não consegui abrir o link do aplicativo neste aparelho.')
            return
        url = getattr(vip, 'APK', None) or getattr(vip, 'APK_GITHUB', None)
        if url and vip.abrir_url(url, 'download do APK'):
            _log('download do APK aberto')
            return
        self._dialogo('Download indisponível',
                      'Não consegui abrir o link do aplicativo neste aparelho.')

    def _atualizar(self):
        """ATUALIZAR APLICATIVO: fluxo de atualizacao que ja existe no app."""
        vip = _vip()
        if vip is not None and vip.procurar_atualizacao():
            _log('checagem de atualizacao aberta (vip.procurar_atualizacao)')
            return
        self._baixar_apk()

    def _ativar_codigo(self):
        """Le o controle 310 e valida com o servidor pelo modulo vip do projeto."""
        vip = _vip()
        if vip is None:
            self._dialogo('Ativação indisponível',
                          'A ativação por código não está disponível neste aparelho.')
            return
        try:
            codigo = (self.getControl(310).getText() or '').strip()
        except Exception:
            codigo = ''
        if not codigo:
            codigo = xbmcgui.Dialog().input(
                'Digite o código de ativação', type=xbmcgui.INPUT_ALPHANUM)
        if not codigo:
            try:
                self.setFocusId(310)
            except Exception:
                pass
            return
        xbmcgui.Dialog().notification(
            'SMARTEDTV', 'Validando o código...', xbmcgui.NOTIFICATION_INFO, 3000)
        ok, mensagem = vip.validar(codigo)
        if ok:
            self._dialogo('VIP ativado', mensagem or 'Acesso VIP liberado.',
                          'Começar a assistir')
            _log('codigo ativado; licenca gravada em vip.json')
        else:
            self._dialogo('Código não ativado',
                          mensagem or 'O serviço não aceitou este código.',
                          'Tentar novamente')
            _log('codigo recusado: %s' % mensagem, xbmc.LOGWARNING)

    def _modo_gratuito(self):
        """Fecha a entrada e libera a Home (versao com anuncios, como hoje)."""
        self._sair()

    def _sair(self):
        self.saiu = True
        self.close()

    # --- eventos ---------------------------------------------------------
    def onClick(self, control_id):
        if self.getProperty(PROP_DIALOGO):
            # qualquer clique com dialogo aberto so fecha o dialogo
            if control_id in (905, 955):
                self._fechar_dialogo()
            elif control_id == 906:
                self._fechar_dialogo(312)
                self._sair()
            return
        if control_id == 312:
            self.setProperty(PROP_DIALOGO, 'ads')
            try:
                self.setFocusId(905)
            except Exception:
                pass
        elif control_id == 905:
            self._fechar_dialogo(312)
        elif control_id == 906:
            self._fechar_dialogo(312)
            self._modo_gratuito()
        elif control_id == 955:
            self._fechar_dialogo()
        elif control_id == 120:
            self._abrir_checkout()
        elif control_id == 121:
            self._compartilhar()
        elif control_id == 122:
            self._baixar_apk()
        elif control_id == 123:
            self._atualizar()
        elif control_id == 311:
            self._ativar_codigo()

    def onAction(self, action):
        if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
            if self.getProperty(PROP_DIALOGO) == 'ads':
                self._fechar_dialogo(312)
                return
            if self.getProperty(PROP_DIALOGO) == 'status':
                self._fechar_dialogo()
                return
            self._sair()

    def onInit(self):
        # a tela abriu: cancela o seguro de 30 s do Startup.xml para a Home
        # nunca aparecer atras da tela de entrada
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


def _ir_para_home(motivo=''):
    if motivo:
        _log('abrindo a Home: %s' % motivo, xbmc.LOGWARNING)
    try:
        xbmc.executebuiltin('CancelAlarm(smartedtv_entrada_seguro,silent)')
    except Exception:
        pass
    try:
        xbmc.executebuiltin(FLUXO_INTERFACE_PRINCIPAL)
    except Exception as erro:
        _log('falha ao abrir a Home: %s' % erro, xbmc.LOGERROR)


def abrir_tela_entrada():
    """Abre a tela do pacote no lugar da Home. Devolve True quando abriu."""
    # O seguro de 30 s do Startup.xml continua ativo de proposito: so e
    # cancelado quando a tela realmente aparece (onInit) ou quando saimos para a
    # Home. Se o Python travar antes de desenhar, o Kodi ainda abre a Home.
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
