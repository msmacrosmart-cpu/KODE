# -*- coding: utf-8 -*-
"""Janela independente de boas-vindas do SMARTEDTV para Kodi Omega 21.

A interface e 100% a do ZIP (DialogWelcome.xml + media/, sem nenhuma alteracao
visual). Este arquivo so adapta os pontos de integracao: resolve o proprio
caminho (o ZIP usava xbmcaddon.Addon(), que so funciona quando o Kodi associa o
script a um addon habilitado no banco de addons), sinaliza ao servico de boot que
a janela abriu, registra cada etapa no log e encaminha cada acao para os fluxos
ja existentes no SMARTEDTV. Onde o projeto nao tem implementacao correspondente,
a acao e apenas registrada no log e NAO e simulada
(relatorio em docs/integracao-tela-entrada.md).
"""
import os
import traceback

import xbmc
import xbmcgui
import xbmcvfs

ADDON_ID = 'script.smartedtv.welcome'
XML_RELATIVO = 'resources/skins/Default/1080i/DialogWelcome.xml'
MARCA_ABERTA = 'smartedtv.welcome.ativa'


# Comando de navegacao ja usado pela skin do projeto para voltar a interface
# principal (ex.: kodi/skin.estilo.personalizado/xml/MyFavourites.xml).
FLUXO_INTERFACE_PRINCIPAL = 'ActivateWindow(Home)'

# Acoes da tela sem fluxo correspondente no projeto. Nenhuma URL, API, endpoint
# ou credencial e inventada aqui: os QR Codes entregues no ZIP continuam sendo
# o unico acesso ao checkout e ao compartilhamento.
ACOES_SEM_FLUXO = {
    120: 'Abrir checkout',
    121: 'Compartilhar link',
    311: 'Ativar codigo VIP',
}


def _log(mensagem, nivel=None):
    try:
        xbmc.log('[%s] %s' % (ADDON_ID, mensagem),
                 xbmc.LOGINFO if nivel is None else nivel)
    except Exception:
        pass


def _caminho_da_tela():
    """Resolve a pasta do addon sem depender do banco de addons do Kodi.

    Ordem: pasta do proprio script (__file__), addons de sistema do APK
    (special://xbmc/addons), addons do perfil (special://home/addons) e, por
    ultimo, xbmcaddon.Addon() (que exige o addon registrado/habilitado).
    """
    candidatos = []
    arquivo = globals().get('__file__')
    if arquivo:
        try:
            candidatos.append(os.path.dirname(xbmcvfs.translatePath(arquivo)))
        except Exception:
            candidatos.append(os.path.dirname(arquivo))
    for raiz in ('special://xbmc/addons/', 'special://home/addons/'):
        try:
            candidatos.append(xbmcvfs.translatePath(raiz + ADDON_ID))
        except Exception:
            candidatos.append(raiz + ADDON_ID)
    try:
        import xbmcaddon
        candidatos.append(xbmcvfs.translatePath(
            xbmcaddon.Addon().getAddonInfo('path')))
    except Exception:
        pass

    for candidato in candidatos:
        if not candidato:
            continue
        xml = os.path.join(candidato, XML_RELATIVO)
        try:
            existe = xbmcvfs.exists(xml)
        except Exception:
            existe = os.path.isfile(xml)
        if existe:
            _log('layout localizado em %s' % xml)
            return candidato
    _log('nenhum candidato contem %s: %r' % (XML_RELATIVO, candidatos),
         xbmc.LOGERROR)
    return None


def _sinalizar_abertura():
    """Permite ao servico de boot confirmar que a janela realmente abriu."""
    try:
        xbmcgui.Window(10000).setProperty(MARCA_ABERTA, '1')
        return
    except Exception:
        pass
    try:
        xbmc.executebuiltin('SetProperty(%s,1,10000)' % MARCA_ABERTA)
    except Exception:
        pass


class WelcomeDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super(WelcomeDialog, self).__init__(*args, **kwargs)
        self._closing = False

    def onInit(self):
        # onInit so roda quando a janela foi carregada de verdade: e o sinal
        # usado pelo servico de boot para confirmar que a tela entrou no ar.
        _sinalizar_abertura()
        _log('onInit: janela carregada')
        # Mantem o foco inicial no campo de codigo, como no HTML de referencia.
        try:
            self.setFocusId(310)
        except Exception:
            _log('onInit: nao foi possivel focar 310', xbmc.LOGWARNING)

    def _sem_fluxo(self, acao):
        xbmc.log('[script.smartedtv.welcome] %s: sem implementacao correspondente '
                 'no SMARTEDTV; acao nao simulada' % acao, xbmc.LOGWARNING)

    def _voltar_para_interface_principal(self):
        """Fecha a janela e devolve o usuario ao fluxo principal existente."""
        self.close()
        xbmc.executebuiltin(FLUXO_INTERFACE_PRINCIPAL)

    def onClick(self, control_id):
        if control_id == 312:
            self.setProperty("show_free_dialog", "true")
            try:
                self.setFocusId(905)
            except Exception:
                pass
        elif control_id == 905:
            self.clearProperty("show_free_dialog")
            try:
                self.setFocusId(312)
            except Exception:
                pass
        elif control_id == 906:
            # Confirmacao do modo gratuito: encaminha para a Home existente.
            # O projeto nao possui camada de anuncios; isso nao e simulado.
            self._voltar_para_interface_principal()
        elif control_id in ACOES_SEM_FLUXO:
            self._sem_fluxo(ACOES_SEM_FLUXO[control_id])
        elif control_id in (130, 131):
            # Seletor visual de aparelho: sem fluxo correspondente no projeto.
            self._sem_fluxo('Seletor de aparelho (%d)' % control_id)

    def onAction(self, action):
        if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
            if self.getProperty("show_free_dialog") == "true":
                self.clearProperty("show_free_dialog")
                try:
                    self.setFocusId(312)
                except Exception:
                    pass
                return
            # Voltar fora do modal: fecha a entrada e devolve a Home.
            self._voltar_para_interface_principal()


def open_welcome():
    _log('open_welcome() iniciada; __file__=%r' % globals().get('__file__'))
    caminho = _caminho_da_tela()
    if not caminho:
        return
    dialog = None
    try:
        # Mesmos parametros visuais do ZIP: XML, skin Default, resolucao 1080i.
        dialog = WelcomeDialog('DialogWelcome.xml', caminho, 'Default', '1080i')
        _log('WindowXMLDialog criado; abrindo doModal()')
        dialog.doModal()
        _log('doModal() encerrado normalmente')
    except Exception as error:
        # Uma falha da janela de entrada nao pode interromper o aplicativo.
        xbmc.log('[%s] falha ao abrir a tela: %s\n%s'
                 % (ADDON_ID, error, traceback.format_exc()), xbmc.LOGERROR)
    finally:
        del dialog


if __name__ == "__main__":
    open_welcome()
