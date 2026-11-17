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

Como o boot termina (correcao da tela preta)
-------------------------------------------
O `Startup.xml` de cada skin agora tem dois `<onload>`:

    AlarmClock(smartedtv_entrada,RunScript(script.smartedtv.welcome),00:00:00,silent)
    RunScript(script.smartedtv.welcome,seguro=1)

Antes havia
`AlarmClock(smartedtv_entrada_seguro,ReplaceWindow($INFO[System.StartupWindow]),00:00:30,silent)`.
Esse alarme dispara em torno da janela de startup (12999), que ja saiu de cena
quando os 30 s terminam, e `$INFO[System.StartupWindow]` resolve para ela mesma —
depois de "Continuar com anuncios" nenhuma janela era ativada: **tela preta**.
Agora:

1. `onInit` da tela → `smartedtv.welcome.ativa=1` (o vigia para de agir);
2. a tela sai de cena → `_ir_para_home()` ativa a Home explicitamente e confirma
   por ate 5 s (`ActivateWindow` → `ReplaceWindow(Home)` → `RestartApp`);
3. se o processo da tela morrer antes do passo 1, o vigia `seguro=1` abre a Home
   em 8 s.

VOLTAR na Home reabre esta tela
------------------------------
O keymap `system/keymaps/zzz-smartedtv-voltar.xml` (injetado no APK) liga o
VOLTAR da Home a `RunScript(script.smartedtv.welcome,voltar)`. A tela reabre por
cima da Home, com o campo do codigo vazio, e a licenca ja ativada (vip.json)
continua valendo — quem entrou so para ver volta e poe o codigo.

Argumentos (`sys.argv`)
    (nenhum)   abre a tela no boot, antes da Home
    seguro=1   vigia do boot (processo separado, nao mostra tela)
    voltar     VOLTAR na Home: reabre a tela por cima da Home

Controles desta tela:
    310 campo do codigo   311 ativar
    120 checkout          121 compartilhar link      122 baixar APK
    123 atualizar aplicativo                       312 assistir com anuncios
    905/906/955 dialogos
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
MARCA_ABERTA = 'smartedtv.welcome.ativa'
MARCA_SAIU = 'smartedtv.welcome.saiu'      # a tela saiu de cena
MARCA_HOME = 'smartedtv.welcome.home'      # abrindo|ok|restart
# Trava do modo `voltar`: duas teclas seguidas nao empilham duas telas.
MARCA_VOLTAR = 'smartedtv.welcome.voltar'
# Comando usado pelo proprio Startup.xml das skins para ir a Home.
FLUXO_INTERFACE_PRINCIPAL = 'ReplaceWindow($INFO[System.StartupWindow])'

HOME_ID = 10000                 # janela da Home (winnames.xml)
# Quanto o vigia espera a tela avisar que desenhou antes de abrir a Home.
ESPERA_VIGIA = 8
# Quanto esperamos a Home aparecer antes do RestartApp de emergencia.
ESPERA_HOME = 5
# Argumento do keymap que reabre a tela a partir da Home.
ARG_VOLTAR = 'voltar'

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


def _sinalizar_abertura():
    _definir(MARCA_ABERTA, '1')


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
        """Abre o checkout da Cakto no navegador externo do Android (sai do app)."""
        url_cakto = 'https://pay.cakto.com.br/nkvbegd_1323120'
        try:
            xbmc.executebuiltin(
                'StartAndroidActivity(android.intent.action.VIEW,%s,,)' % url_cakto)
            _log('checkout aberto no navegador externo: %s' % url_cakto)
            return
        except Exception as erro:
            _log('nao foi possivel abrir checkout externo: %s' % erro, xbmc.LOGWARNING)
        self._dialogo('Checkout indisponível',
                      'Não consegui abrir o pagamento neste aparelho. '
                      'Aponte a câmera para o QR Code ao lado.')

    def _compartilhar(self):
        """Abre o link de download do APK no Dropbox no navegador externo (sai do app)."""
        url_dropbox = ('https://www.dropbox.com/scl/fi/adn9elzkjzxof741bbui2/'
                       'SMARTEDTV-atual.apk')
        try:
            xbmc.executebuiltin(
                'StartAndroidActivity(android.intent.action.VIEW,%s,,)' % url_dropbox)
            _log('download do APK aberto no navegador externo: %s' % url_dropbox)
            return
        except Exception as erro:
            _log('nao foi possivel abrir download externo: %s' % erro, xbmc.LOGWARNING)
        self._dialogo('Download indisponível',
                      'Não consegui abrir o link de download neste aparelho.')

    def _baixar_apk(self):
        """Abre o link de download do APK no Dropbox no navegador externo (sai do app)."""
        url_dropbox = ('https://www.dropbox.com/scl/fi/adn9elzkjzxof741bbui2/'
                       'SMARTEDTV-atual.apk')
        try:
            xbmc.executebuiltin(
                'StartAndroidActivity(android.intent.action.VIEW,%s,,)' % url_dropbox)
            _log('download do APK aberto no navegador externo: %s' % url_dropbox)
            return
        except Exception as erro:
            _log('nao foi possivel abrir download externo: %s' % erro, xbmc.LOGWARNING)
        self._dialogo('Download indisponível',
                      'Não consegui abrir o link de download neste aparelho.')

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
        _definir(MARCA_SAIU, '1')      # o vigia para de agir
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
        # 130/131 (seletor de aparelho) e 140/141 (planos) sairam da tela: a
        # tela e 16:9 fixa e quem define a validade do codigo e o servidor.
        # Clique nesses ids nao faz nada (ver tests).

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
        # a tela desenhou: o vigia `seguro=1` pode dormir (nao ha mais alarme
        # de 30 s no Startup.xml — era ele que deixava a tela preta)
        self.saiu = False
        _limpar(MARCA_SAIU)
        _sinalizar_abertura()
        _log('tela de entrada carregada (antes da Home)')
        try:
            self.setFocusId(310)
        except Exception:
            pass


def _tela_da_home():
    """True quando a Home ja esta na tela (`System.CurrentWindow`)."""
    try:
        return xbmc.getInfoLabel('System.CurrentWindow').strip() == 'Home'
    except Exception:
        return False


def _comando_ok(comando, espera=0.6):
    """Dispara um builtin; devolve False (e loga) se o Kodi recusar."""
    try:
        xbmc.executebuiltin(comando)
    except Exception as erro:
        _log('builtin falhou (%s): %s' % (comando, erro), xbmc.LOGERROR)
        return False
    if espera:
        try:
            xbmc.sleep(int(espera * 1000))
        except Exception:
            pass
    return True


def _ir_para_home(motivo=''):
    """Abre a Home DEPOIS que a tela saiu de cena. Nunca deixa tela preta.

    1. `ActivateWindow(Home,return)` — caminho normal (o Kodi carrega a janela
       ao ativa-la, mesmo com a Home ainda nao criada);
    2. `ReplaceWindow(Home)` — se a ativacao nao pegou;
    3. confirma por ate 5 s olhando `System.CurrentWindow`;
    4. se nada funcionou, `RestartApp` (melhor reiniciar do que ficar no escuro).

    O antigo comando do Startup.xml
    (`ReplaceWindow($INFO[System.StartupWindow])`) NAO e usado aqui: ele aponta
    para a janela de startup, que ja morreu — era a causa da tela preta.
    """
    if motivo:
        _log('abrindo a Home: %s' % motivo, xbmc.LOGWARNING)
    _definir(MARCA_HOME, 'abrindo')
    _definir(MARCA_ABERTA, '1')      # a partir daqui o vigia nao age sozinho

    _comando_ok('ActivateWindow(Home,return)', espera=1.2)
    if _tela_da_home():
        _log('Home ativa (ActivateWindow)')
        _definir(MARCA_HOME, 'ok')
        return True

    _log('ActivateWindow(Home) nao apareceu; tentando ReplaceWindow(Home)',
         xbmc.LOGWARNING)
    _comando_ok('ReplaceWindow(Home)', espera=1.2)
    if _tela_da_home():
        _log('Home ativa (ReplaceWindow)')
        _definir(MARCA_HOME, 'ok')
        return True

    limite = time.time() + ESPERA_HOME
    while time.time() < limite:
        try:
            xbmc.sleep(250)
        except Exception:
            pass
        if _tela_da_home():
            _log('Home ativa (aguardando o carregamento)')
            _definir(MARCA_HOME, 'ok')
            return True

    _log('a Home nao apareceu; reiniciando o app', xbmc.LOGERROR)
    _definir(MARCA_HOME, 'restart')
    _definir(MARCA_SAIU, '1')
    _comando_ok('RestartApp', espera=0)
    return False


def vigiar_inicializacao():
    """Processo `seguro=1`: garante que o boot sempre termina na Home.

    O AlarmClock antigo do Startup.xml disparava em torno da janela de startup,
    que ja morreu quando o comando rodava — a Home nunca abria (tela preta).
    Aqui quem vigia e um processo de verdade, com prazo e sem depender de janela.
    """
    _log('vigia de inicializacao da tela iniciado')
    limite = time.time() + ESPERA_VIGIA
    while time.time() < limite:
        if _propriedade(MARCA_ABERTA) or _propriedade(MARCA_SAIU):
            _log('vigia: a tela assumiu o boot')
            return _vigiar_depois_da_tela()
        try:
            xbmc.sleep(250)
        except Exception:
            pass
    if _propriedade(MARCA_ABERTA) or _propriedade(MARCA_SAIU):
        return _vigiar_depois_da_tela()
    _log('vigia: a tela nao apareceu em %d s; abrindo a Home' % ESPERA_VIGIA,
         xbmc.LOGWARNING)
    _ir_para_home('vigia (tela nao chegou a desenhar)')
    return True


def _vigiar_depois_da_tela(prazo=25):
    """A tela assumiu: se ela sair de cena sem a Home, abre a Home."""
    limite = time.time() + prazo
    while time.time() < limite:
        if _propriedade(MARCA_HOME):
            return True                    # a tela ja resolveu
        if _propriedade(MARCA_SAIU):
            try:
                xbmc.sleep(1500)           # deixa a propria tela tentar
            except Exception:
                pass
            if _tela_da_home() or _propriedade(MARCA_HOME):
                return True
            _log('vigia: a tela saiu sem abrir a Home; assumindo',
                 xbmc.LOGWARNING)
            _ir_para_home('vigia (a tela saiu e a Home nao veio)')
            return True
        try:
            xbmc.sleep(250)
        except Exception:
            pass
    return True


def voltar_para_a_tela():
    """VOLTAR na Home: mostra a tela de entrada de novo (sem reiniciar nada).

    Chamado pelo keymap da Home. A tela abre POR CIMA da Home (que ja carregou
    neste ponto); ao sair — Continuar com anuncios, Voltar ou codigo ativado — a
    Home continua onde estava, entao a tela nunca deixa o app no escuro.
    Devolve True quando desenhou.
    """
    if not _tela_da_home():
        # ainda dentro do boot (janela de startup): fluxo normal
        return abrir_tela_entrada()
    if _propriedade(MARCA_VOLTAR):
        _log('VOLTAR na Home: a tela ja esta aberta, ignorando')
        return False
    pasta = _pasta_da_tela()
    if not pasta:
        _log('pasta da tela nao encontrada (voltar na Home)', xbmc.LOGERROR)
        return False
    _log('VOLTAR na Home: reabrindo a tela de entrada')
    _definir(MARCA_VOLTAR, '1')
    _definir(MARCA_ABERTA, '1')
    _definir(MARCA_HOME, 'ok')
    try:
        janela = WelcomeDialog('DialogWelcome.xml', pasta, 'Default', '1080i')
    except Exception as erro:
        _log('falha ao montar a tela (voltar): %s' % erro, xbmc.LOGERROR)
        _limpar(MARCA_VOLTAR)
        return False
    try:
        janela.doModal()
    except Exception as erro:
        _log('falha ao exibir a tela (voltar): %s' % erro, xbmc.LOGERROR)
        _limpar(MARCA_VOLTAR)
        return False
    _limpar(MARCA_VOLTAR)
    # A Home ja estava carregada: basta garantir que continua na tela. Nada de
    # RestartApp (o usuario estaria assistindo) e nada de ReplaceWindow.
    if not _tela_da_home():
        _comando_ok('ActivateWindow(Home,return)', espera=0.6)
    _limpar(MARCA_SAIU)
    return True


def abrir_tela_entrada():
    """Abre a tela do pacote no lugar da Home. Devolve True quando abriu."""
    # Quem salva o boot se o Python travar antes de desenhar e o vigia
    # `seguro=1` do Startup.xml (8 s). Aqui limpamos qualquer trava do modo
    # `voltar` e abrimos a Home em todos os caminhos de falha.
    _limpar(MARCA_VOLTAR)
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
    # `seguro=1` no RunScript do Startup.xml = vigia de inicializacao;
    # `voltar` vem do keymap da Home (VOLTAR reabre a tela de entrada).
    argumentos = [a.lower() for a in sys.argv[1:]]
    if any('seguro' in a for a in argumentos):
        vigiar_inicializacao()
    elif any(ARG_VOLTAR in a for a in argumentos):
        voltar_para_a_tela()
    else:
        abrir_tela_entrada()
