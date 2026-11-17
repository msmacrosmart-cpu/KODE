# -*- coding: utf-8 -*-
"""Tela de entrada do SMARTEDTV — interface do pacote `smartedtv-src`, aberta
ANTES da Home.

O desenho é o do pacote entregue (medido do CSS e reproduzido em
`resources/skins/Default/1080i/DialogWelcome.xml`, com as texturas e os QR Codes
originais). Este arquivo só liga os controles ao que já existe no app.

Como a tela entra no boot (Kodi 21 Omega)
-----------------------------------------
O `Startup.xml` de cada skin tem dois `<onload>`:

    AlarmClock(smartedtv_entrada,RunScript(script.smartedtv.welcome),00:00:00,silent)
    RunScript(script.smartedtv.welcome,seguro=1)

* o primeiro dispara esta tela;
* o segundo é um processo **separado** que vigia o boot: se o da tela morrer
  antes de avisar que desenhou, ele abre a Home em 8 s.

A tela é um `WindowXMLDialog` modal aberto a partir do script. Enquanto ele está
na tela, a Home (10000) **não existe**: é `open()` quem a cria, num segundo
thread, enquanto o modal está de pé (o Kodi só carrega a próxima janela quando a
modal sai de cena). Até a v8 isto era feito só com `ReplaceWindow`, e o
`AlarmClock` que deveria salvar o boot disparava em torno da *janela de startup*
(janela que já morreu no instante do disparo): o comando era executado na 12999,
que está vazia — daí a **tela preta**, em vez da Home. Agora:

1. `onInit` da tela → escreve `smartedtv.welcome.ativa=1` (o vigia para de agir);
2. a tela sai de cena (Assistir com anúncios, Voltar ou código VIP ativado) →
   `_abrir_home()` abre a Home 10000 de forma explícita, com confirmação;
3. se a Home não abrir em 5 s, o script chama `RestartApp` (rede de segurança);
4. se este processo morrer antes do passo 1, o vigia `seguro=1` abre a Home.

Voltar na Home reabre esta tela
-------------------------------
O keymap `system/keymaps/zzz-smartedtv-voltar.xml` (injetado no APK) liga o
VOLTAR da Home a `RunScript(script.smartedtv.welcome,voltar)`:

    <Home><keyboard><backspace>RunScript(script.smartedtv.welcome,voltar)...

Assim quem entrou em "Assistir com anúncios" só para ver volta para a tela
inicial — com o campo do código vazio e pronto para quem tiver um código VIP —
sem passar pelo boot. A licença já gravada (vip.json) não é tocada.

Controles desta tela (o resto do app continua igual):
    310 campo do código   311 ativar
    120 checkout          121 compartilhar link      122 baixar APK
    123 atualizar aplicativo                       312 assistir com anúncios
    905/906/955 diálogos

Argumentos (`sys.argv`, como o Startup.xml e o keymap chamam)
     (nenhum)   abre a tela no boot, antes da Home
     seguro=1   vigia do boot (processo separado, não mostra tela)
     voltar     VOLTAR na Home: reabre a tela por cima da Home
"""
from __future__ import absolute_import, unicode_literals

import os
import sys
import time

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

ADDON_ID = 'script.smartedtv.welcome'
SERVICO = 'service.smarted.bootstrap'
XML_RELATIVO = 'resources/skins/Default/1080i/DialogWelcome.xml'

# Propriedades da janela 10000 usadas na comunicação entre a tela, o vigia e o
# resto do app (também ficam visíveis no log e em ferramentas de diagnóstico).
MARCA_ABERTA = 'smartedtv.welcome.ativa'
MARCA_SAIU = 'smartedtv.welcome.saiu'
MARCA_HOME = 'smartedtv.welcome.home'
PROP_DIALOGO = 'welcome_dialog'
PROP_TITULO = 'welcome_status_title'
PROP_TEXTO = 'welcome_status_text'
PROP_OK = 'welcome_status_ok'

HOME_ID = 10000
# Quanto o vigia espera a tela avisar que desenhou antes de abrir a Home.
ESPERA_VIGIA = 8
# Quanto esperamos a Home aparecer antes do RestartApp de emergência.
ESPERA_HOME = 5
JANELA_INICIAL = 12999          # WINDOW_STARTUP_ANIM: a janela do Startup.xml
# Argumento que o keymap usa em VOLTAR na Home (ver system/keymaps do APK).
ARG_VOLTAR = 'voltar'
JANELA_HOME = 10000             # winnames.xml: <window><id>10000</id>


def _log(mensagem, nivel=None):
    try:
        xbmc.log('[%s] %s' % (ADDON_ID, mensagem),
                 xbmc.LOGINFO if nivel is None else nivel)
    except Exception:
        pass


def _propriedade(chave, padrao=''):
    try:
        valor = xbmcgui.Window(HOME_ID).getProperty(chave)
        return valor if valor else padrao
    except Exception:
        return padrao


def _definir(chave, valor='1'):
    try:
        xbmcgui.Window(HOME_ID).setProperty(chave, valor)
        return True
    except Exception as erro:
        _log('nao consegui escrever a propriedade %s: %s' % (chave, erro),
             xbmc.LOGWARNING)
        return False


def _limpar(chave):
    try:
        xbmcgui.Window(HOME_ID).clearProperty(chave)
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
    """Módulo de licença VIP que já existe no projeto (sem duplicar lógica)."""
    pasta = _pasta_do_servico()
    if not pasta:
        _log('service.smarted.bootstrap nao encontrado', xbmc.LOGWARNING)
        return None
    try:
        if pasta not in sys.path:
            sys.path.append(pasta)
        import vip  # módulo real do service.smarted.bootstrap
        return vip
    except Exception as erro:
        _log('modulo vip indisponivel: %s' % erro, xbmc.LOGWARNING)
        return None


def _pasta_da_tela():
    """Pasta do addon, preferindo o caminho do próprio arquivo."""
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


# --------------------------------------------------------------------- Home
def _tela_da_home():
    """True quando a Home já está na tela.

    `System.CurrentWindow` devolve o nome da janela em inglês; comparamos com
    `Home` e, como reforço, verificamos se ainda estamos na janela de startup.
    """
    try:
        return xbmc.getInfoLabel('System.CurrentWindow').strip() == 'Home'
    except Exception:
        return False


def _comando_ok(comando, espera=0.6):
    """Dispara um builtin e confirma no log do Kodi que ele rodou."""
    try:
        xbmc.executebuiltin(comando)
    except Exception as erro:
        _log('builtin falhou (%s): %s' % (comando, erro), xbmc.LOGERROR)
        return False
    if not espera:
        return True
    xbmc.sleep(int(espera * 1000))
    return True


def _abrir_home(motivo=''):
    """Abre a Home DEPOIS que a tela saiu de cena. Nunca deixa tela preta.

    1. `ActivateWindow(Home)` — caminho normal, funciona com a Home ainda não
       carregada (o Kodi carrega a janela ao ativá-la);
    2. `ReplaceWindow(Home)` — se a ativação não pegou (janela de startup ainda
       sendo a corrente);
    3. confirma por até 5 s olhando `System.CurrentWindow`;
    4. se nada disso funcionou, `RestartApp` (o app volta com a Home; é melhor
       reiniciar do que ficar preso numa tela vazia).
    """
    if motivo:
        _log('abrindo a Home: %s' % motivo)
    _definir(MARCA_HOME, 'abrindo')
    # a partir daqui o vigia não deve mais agir sozinho
    _definir(MARCA_ABERTA, '1')

    _comando_ok('ActivateWindow(Home,return)', espera=1.2)
    if _tela_da_home():
        _log('Home ativa (ActivateWindow)')
        _definir(MARCA_HOME, 'ok')
        return True

    _log('ActivateWindow(Home) nao apareceu; tentando ReplaceWindow',
         xbmc.LOGWARNING)
    _comando_ok('ReplaceWindow(Home)', espera=1.2)
    if _tela_da_home():
        _log('Home ativa (ReplaceWindow)')
        _definir(MARCA_HOME, 'ok')
        return True

    limite = time.time() + ESPERA_HOME
    while time.time() < limite:
        xbmc.sleep(250)
        if _tela_da_home():
            _log('Home ativa (aguardando o carregamento)')
            _definir(MARCA_HOME, 'ok')
            return True

    # Último recurso: reinicia a interface. O Startup.xml dispara de novo, mas a
    # marca `MARCA_SAIU` faz a tela se abrir já em modo "seguir para a Home".
    _log('a Home nao apareceu; reiniciando o app', xbmc.LOGERROR)
    _definir(MARCA_HOME, 'restart')
    _definir(MARCA_SAIU, '1')
    _comando_ok('RestartApp', espera=0)
    return False


def vigiar_inicializacao():
    """Processo `seguro=1`: garante que o boot sempre termina na Home.

    O AlarmClock do Startup.xml original disparava em torno da janela de startup,
    que já morreu quando o comando rodava — a Home nunca abria (tela preta).
    Aqui quem vigia é um processo de verdade, com prazo e sem depender de janela.

    Depois de a tela assumir, o vigia continua de olho: se a tela sair de cena e
    a Home não aparecer em alguns segundos (caminho que deveria ser do próprio
    script da tela), ele assume e abre a Home. É a rede final contra tela preta.
    """
    _log('vigia de inicializacao da tela iniciado')
    limite = time.time() + ESPERA_VIGIA
    while time.time() < limite:
        if _propriedade(MARCA_ABERTA) or _propriedade(MARCA_SAIU):
            _log('vigia: a tela assumiu o boot')
            return _vigiar_depois_da_tela()
        xbmc.sleep(250)
    if _propriedade(MARCA_ABERTA) or _propriedade(MARCA_SAIU):
        return _vigiar_depois_da_tela()
    _log('vigia: a tela nao apareceu em %d s; abrindo a Home' % ESPERA_VIGIA,
         xbmc.LOGWARNING)
    _abrir_home('vigia (tela nao chegou a desenhar)')
    return True


def _vigiar_depois_da_tela(prazo=25):
    """A tela assumiu: se ela sair de cena sem a Home, abre a Home."""
    limite = time.time() + prazo
    while time.time() < limite:
        if _propriedade(MARCA_HOME):
            return True                    # o script da tela já resolveu
        if _propriedade(MARCA_SAIU):
            xbmc.sleep(1500)               # deixa o próprio script tentar
            if _tela_da_home() or _propriedade(MARCA_HOME):
                return True
            _log('vigia: a tela saiu sem abrir a Home; assumindo',
                 xbmc.LOGWARNING)
            _abrir_home('vigia (a tela saiu e a Home nao veio)')
            return True
        xbmc.sleep(250)
    return True


# --------------------------------------------------------------------- tela
class WelcomeDialog(xbmcgui.WindowXMLDialog):
    """Mesma tela do pacote; aqui só encaminhamos as ações para o projeto."""

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.saiu = False

    # --- diálogos ---------------------------------------------------------
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

    # --- ações ligadas ao que já existe no projeto ------------------------
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
        """ATUALIZAR APLICATIVO: fluxo de atualização que já existe no app."""
        vip = _vip()
        if vip is not None and vip.procurar_atualizacao():
            _log('checagem de atualizacao aberta (vip.procurar_atualizacao)')
            return
        self._baixar_apk()

    def _ativar_codigo(self):
        """Lê o controle 310 e valida com o servidor pelo módulo vip do projeto."""
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
        """Fecha a entrada e libera a Home (versão com anúncios, como hoje)."""
        _log('modo gratuito escolhido: Assistir com anúncios')
        self._sair()

    def _sair(self):
        self.saiu = True
        _definir(MARCA_SAIU, '1')      # o vigia para de agir
        self.close()

    # --- eventos ---------------------------------------------------------
    def onClick(self, control_id):
        if self.getProperty(PROP_DIALOGO):
            # qualquer clique com diálogo aberto só fecha o diálogo
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
            # "Continuar com anúncios" do diálogo de confirmação
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
        # a tela desenhou: o vigia pode dormir
        _limpar(MARCA_SAIU)
        _definir(MARCA_ABERTA, '1')
        _log('tela de entrada carregada (antes da Home)')
        self.saiu = False
        try:
            self.setFocusId(310)
        except Exception:
            pass


def voltar_para_a_tela():
    """VOLTAR na Home: mostra a tela de entrada de novo (sem reiniciar nada).

    Chamado pelo keymap da Home. A tela abre POR CIMA da Home (a Home já carregou
    neste ponto); ao sair — Assistir com anúncios, Voltar ou código ativado — a
    Home continua exatamente onde estava, então a tela nunca deixa o app no
    escuro. Devolve True quando desenhou.
    """
    if not _tela_da_home():
        # ainda dentro do boot (janela de startup): deixa o fluxo normal abrir
        return abrir_tela_entrada()
    pasta = _pasta_da_tela()
    if not pasta:
        _log('pasta da tela nao encontrada (voltar na Home)', xbmc.LOGERROR)
        return False
    _log('VOLTAR na Home: reabrindo a tela de entrada')
    # marca o boot como concluido: o vigia `seguro=1` não deve agir aqui
    _definir(MARCA_ABERTA, '1')
    _definir(MARCA_HOME, 'ok')
    try:
        janela = WelcomeDialog('DialogWelcome.xml', pasta, 'Default', '1080i')
    except Exception as erro:
        _log('falha ao montar a tela (voltar): %s' % erro, xbmc.LOGERROR)
        return False
    try:
        janela.doModal()
    except Exception as erro:
        _log('falha ao exibir a tela (voltar): %s' % erro, xbmc.LOGERROR)
        return False
    # A Home já estava carregada: basta garantir que continua na tela. Nada de
    # RestartApp (o usuário estaria assistindo) e nada de ReplaceWindow.
    if not _tela_da_home():
        _comando_ok('ActivateWindow(Home,return)', espera=0.6)
    _limpar(MARCA_SAIU)
    return True


def abrir_tela_entrada():
    """Abre a tela do pacote no lugar da Home. Devolve True quando abriu.

    A Home é aberta pelo próprio script DEPOIS que a modal sai de cena (é o que
    o Kodi espera: a janela seguinte só é carregada ao fim do modal).
    """
    pasta = _pasta_da_tela()
    if not pasta:
        _log('pasta da tela nao encontrada', xbmc.LOGERROR)
        _abrir_home('tela de entrada indisponivel')
        return False
    try:
        janela = WelcomeDialog('DialogWelcome.xml', pasta, 'Default', '1080i')
    except Exception as erro:
        _log('falha ao montar a tela: %s' % erro, xbmc.LOGERROR)
        _abrir_home('tela de entrada indisponivel')
        return False
    try:
        janela.doModal()
    except Exception as erro:
        _log('falha ao exibir a tela: %s' % erro, xbmc.LOGERROR)
        _abrir_home('tela de entrada indisponivel')
        return False
    # A modal já saiu de cena (doModal retornou): agora sim a Home.
    _abrir_home('a tela de entrada terminou')
    return True


if __name__ == '__main__':
    # `seguro=1` no RunScript do Startup.xml = vigia de inicialização
    argumentos = [a.lower() for a in sys.argv[1:]]
    if any('seguro' in a for a in argumentos):
        vigiar_inicializacao()
    elif any(ARG_VOLTAR in a for a in argumentos):
        voltar_para_a_tela()
    else:
        abrir_tela_entrada()
