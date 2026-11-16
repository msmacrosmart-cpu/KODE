# -*- coding: utf-8 -*-
"""Janela independente de boas-vindas do SMARTEDTV para Kodi Omega 21.

A interface e 100% a do ZIP (DialogWelcome.xml + media/, sem nenhuma alteracao
visual). Este arquivo so adapta os pontos de integracao: abre/fecha a janela e
encaminha cada acao para os fluxos ja existentes no SMARTEDTV. Onde o projeto
nao tem implementacao correspondente, a acao e apenas registrada no log e NAO
e simulada (relatorio em docs/integracao-tela-entrada.md).
"""
import xbmc
import xbmcgui
import xbmcaddon
import os


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


class WelcomeDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        super(WelcomeDialog, self).__init__(*args, **kwargs)
        self._closing = False

    def onInit(self):
        # Mantem o foco inicial no campo de codigo, como no HTML de referencia.
        try:
            self.setFocusId(310)
        except Exception:
            pass

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
    addon = xbmcaddon.Addon()
    addon_path = addon.getAddonInfo("path")
    dialog = WelcomeDialog(
        "DialogWelcome.xml",
        addon_path,
        "Default",
        "1080i"
    )
    try:
        dialog.doModal()
    except Exception as error:
        # Uma falha da janela de entrada nao pode interromper o aplicativo.
        xbmc.log('[script.smartedtv.welcome] falha ao abrir a tela: %s' % error,
                 xbmc.LOGERROR)
    finally:
        del dialog


if __name__ == "__main__":
    open_welcome()
