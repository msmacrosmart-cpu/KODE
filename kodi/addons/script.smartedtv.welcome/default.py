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
   por ate 5 s (`ActivateWindow` → `ReplaceWindow(Home)`; nunca reinicia);
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
    120 checkout          121 abrir Dropbox        122 baixar APK
    123 atualizar aplicativo                       312 assistir com anuncios
    905/906/955 dialogos

IDs 120 e 121 (correcao)
------------------------
Os dois botoes SAEM do Kodi e abrem o navegador padrao do Android:

* 120 -> checkout da Cakto (https://pay.cakto.com.br/nkvbegd_1323120)
* 121 -> pagina do Dropbox com o APK (link verdadeiro do QR qr_apk.png)

O comando usado e ``StartAndroidActivity(package,intent,dataType,dataURI)``.
A versao anterior passava a action no campo do pacote
(``StartAndroidActivity(android.intent.action.VIEW,URL,,)``), o Kodi tentava
abrir um pacote chamado ``android.intent.action.VIEW`` e nada acontecia. Agora
o pacote vai vazio (intent implicito) e o Android escolhe o navegador padrao.
Pressionar e segurar o 121 continua abrindo o compartilhamento nativo
(ACTION_SEND), para nao perder a funcao que ja existia.
"""
from __future__ import absolute_import, unicode_literals

import os
import re
import sys
import threading
import time

import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

ADDON_ID = 'script.smartedtv.welcome'
SERVICO = 'service.smarted.bootstrap'
XML_RELATIVO = 'resources/skins/Default/1080i/DialogWelcome.xml'
XML_ARQUIVO = 'DialogWelcome.xml'
# Variante com area segura para TV/box/projetor/stick (overscan).
XML_TV_RELATIVO = 'resources/skins/Default/1080i/DialogWelcomeTV.xml'
XML_TV_ARQUIVO = 'DialogWelcomeTV.xml'
PLATAFORMA_ARQUIVO = 'special://home/../plataforma.txt'
MARCA_ABERTA = 'smartedtv.welcome.ativa'
MARCA_SAIU = 'smartedtv.welcome.saiu'      # a tela saiu de cena
MARCA_HOME = 'smartedtv.welcome.home'      # abrindo|ok|restart
# Trava do modo `voltar`: duas teclas seguidas nao empilham duas telas.
MARCA_VOLTAR = 'smartedtv.welcome.voltar'
# Comando usado pelo proprio Startup.xml das skins para ir a Home.
FLUXO_INTERFACE_PRINCIPAL = 'ReplaceWindow($INFO[System.StartupWindow])'
# Alarme que o Startup.xml entrega ao PROPRIO Kodi como ultimo recurso: se o
# Python nao subir (addon desabilitado/corrompido), a Home abre em 25 s. A tela
# viva cancela este alarme assim que desenha e em toda ida para a Home, para
# nao haver dois "abrir a Home" concorrentes (outra causa de tela preta).
ALARME_SEGURO = 'smartedtv_home_seguro'

# Fallbacks usados so quando o vip.py nao puder ser importado. Os valores sao
# os mesmos de vip.py: checkout do pacote e o link verdadeiro gravado no QR
# Code qr_apk.png (com rlkey; sem ele o link /scl/fi/ do Dropbox nao abre).
CHECKOUT = 'https://pay.cakto.com.br/nkvbegd_1323120'
APK_NOME = 'SMARTEDTV.apk'
# Pasta publicada: o download pede o APK PELO NOME, entao trocar o conteudo
# do arquivo na pasta ja publica versao nova (link de arquivo /scl/fi/ fica
# preso ao ID do arquivo e pode servir uma versao antiga).
DROPBOX_PASTA = ('https://www.dropbox.com/scl/fo/5w6yfp0tvee0xro2wh0m3/'
                 'AKikmSEMGOvGv1QTiKCV8CU?rlkey=3b8m9dnw571waz7vs83n0vn17')
# Link direto do arquivo (dl=1 baixa em vez de mostrar a pagina). E o reserva
# usado quando o vip.py nao esta disponivel: o /scl/fi/ fica preso ao arquivo
# em que o link foi criado, por isso o vip.py tenta antes o nome na pasta.
APK_DOWNLOAD = ('https://www.dropbox.com/scl/fi/adn9elzkjzxof741bbui2/'
                'SMARTEDTV.apk?rlkey=yp1ijxk6fdtcqm93gzi24ig5j'
                '&st=p1m6ebvg&dl=1')
DROPBOX_URL = ('https://www.dropbox.com/scl/fi/adn9elzkjzxof741bbui2/'
               'SMARTEDTV.apk?rlkey=yp1ijxk6fdtcqm93gzi24ig5j'
               '&st=p1m6ebvg&dl=0')

HOME_ID = 10000                 # janela da Home (winnames.xml)
# Quanto o vigia espera a tela avisar que desenhou antes de abrir a Home.
ESPERA_VIGIA = 8
# Quanto esperamos a Home aparecer antes da ultima tentativa/aviso.
ESPERA_HOME = 5
# Argumento do keymap que reabre a tela a partir da Home.
ARG_VOLTAR = 'voltar'
# Argumento do menu Energia: encerra o Kodi de forma limpa.
ARG_SAIR = 'sair'
# Argumento do menu Energia: reinicia o app limpando o estado antes.
ARG_REINICIAR = 'reiniciar'

# Propriedades da janela usadas pelos grupos do XML (dialogos).
PROP_DIALOGO = 'welcome_dialog'
PROP_TITULO = 'welcome_status_title'
PROP_TEXTO = 'welcome_status_text'
PROP_OK = 'welcome_status_ok'
PROP_TECLADO = 'welcome_teclado'

# Controles principais (fora dos dialogos) e os de cada dialogo. Servem para
# recuperar o foco quando uma janela/dialogo invisivel deixa o D-pad sem destino.
FOCO_PRINCIPAL = (310, 120, 121, 122, 123, 311, 312)
FOCO_ADS = (905, 906)
FOCO_STATUS = (955,)


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


def _link_do_dropbox_desta_versao(vip=None):
    """Link da pasta do Dropbox (``SMARTEDTV UNIVERSAL``).

    Com o APK universal ha UMA pasta para celular e TV. Quem manda continua
    sendo o ``vip.py`` (``pastas_dropbox``); aqui so perguntamos, para o botao
    nunca abrir um link diferente do que o app usa para se atualizar.
    """
    try:
        if vip is None:
            vip = _vip()
        eh_tv = getattr(vip, 'eh_tv', None)
        if not (callable(eh_tv) and eh_tv()):
            return None
        pastas = getattr(vip, 'pastas_dropbox', None)
        if callable(pastas):
            links = pastas() or []
            if links:
                return links[0]
    except Exception as erro:
        _log('nao consegui resolver a pasta do Dropbox: %s' % erro,
             xbmc.LOGWARNING)
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


_PLATAFORMA_GRAVADA = [False]


def _caminho_plataforma():
    try:
        return xbmcvfs.translatePath(PLATAFORMA_ARQUIVO)
    except Exception:
        return ''


def _plataforma_salva():
    """Le a escolha antiga do app (celular/tv) gravada pelo Java Plataforma."""
    caminho = _caminho_plataforma()
    if not caminho:
        return ''
    try:
        if not xbmcvfs.exists(caminho):
            return ''
        arquivo = xbmcvfs.File(caminho)
        try:
            texto = (arquivo.read() or '')
        finally:
            arquivo.close()
        if isinstance(texto, bytes):
            texto = texto.decode('utf-8', 'replace')
        texto = texto.strip().lower()
        if texto.startswith('tv'):
            return 'tv'
        if texto.startswith('celular'):
            return 'celular'
    except Exception:
        pass
    return ''


def _gravar_plataforma(modo):
    """Compartilha a deteccao com o Java (AdTela usa para focar o Pular)."""
    if _PLATAFORMA_GRAVADA[0]:
        return
    caminho = _caminho_plataforma()
    if not caminho:
        return
    try:
        arquivo = xbmcvfs.File(caminho, 'w')
        try:
            arquivo.write(('%s\n' % modo).encode('utf-8'))
        finally:
            arquivo.close()
        _PLATAFORMA_GRAVADA[0] = True
    except Exception:
        pass


def _parece_tv():
    """TV, box, projetor ou stick: tela grande (16:9, 16:10 ou 4:3) e/ou nome."""
    try:
        if not xbmc.getCondVisibility('System.Platform.Android'):
            return False
    except Exception:
        return False
    try:
        resolucao = xbmc.getInfoLabel('System.ScreenResolution') or ''
    except Exception:
        resolucao = ''
    achado = re.search(r'(\d{3,5})\s*[xX]\s*(\d{3,5})', resolucao)
    if achado:
        largura, altura = int(achado.group(1)), int(achado.group(2))
        if altura >= 600 and largura >= 1024:
            proporcao = float(largura) / float(altura)
            # 16:9 (TV/box/stick/projetor) e tambem 4:3/16:10 de projetores
            # antigos. Celulares atuais sao 18:9 ou mais e ficam de fora.
            if 1.25 <= proporcao <= 2.00:
                return True
    try:
        nome = (xbmc.getInfoLabel('System.FriendlyName') or '').lower()
    except Exception:
        nome = ''
    for marca in ('tv', 'box', 'stick', 'fire', 'aft', 'shield',
                  'chromecast', 'projector', 'projetor', 'leanback'):
        if marca in nome:
            return True
    return False


def _modo_tv():
    """True = usa a variante com margem de overscan.

    A escolha antiga (plataforma.txt) manda; sem ela, detecta pela resolucao e
    pelo nome do aparelho. A deteccao tambem e gravada para o Java, que assim
    sabe focar o botao Pular do anuncio no controle remoto.
    """
    salvo = _plataforma_salva()
    if salvo:
        return salvo == 'tv'
    tv = _parece_tv()
    _gravar_plataforma('tv' if tv else 'celular')
    return tv


def _xml_da_tela(pasta):
    """XML a abrir: a variante TV quando o aparelho pede area segura."""
    if _modo_tv():
        caminho = os.path.join(pasta, XML_TV_RELATIVO)
        try:
            if xbmcvfs.exists(caminho):
                return XML_TV_ARQUIVO
        except Exception:
            pass
    return XML_ARQUIVO


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


def _mascarar(codigo):
    """Nunca coloca o codigo inteiro no log (privacidade do cliente)."""
    codigo = (codigo or '').strip()
    if len(codigo) <= 6:
        return '***' if codigo else '(vazio)'
    return codigo[:4] + '...' + codigo[-2:]


def _id_acao(action):
    """Kodi 21 entrega um objeto Action; versoes antigas entregam int."""
    try:
        return int(action.getId())
    except Exception:
        try:
            return int(action)
        except Exception:
            return 0


def _clipboard():
    """Tenta ler a area de transferencia pelas APIs que o Kodi expuser.

    O Kodi 21/Android ainda nao implementa getClipboard(); a funcao devolve ''
    nesse caso. Quando uma versao futura expuser a API, o codigo copiado no
    WhatsApp/pagina entra direto no campo, sem biblioteca externa.
    """
    for modulo in (xbmc, xbmcgui):
        funcao = getattr(modulo, 'getClipboard', None)
        if callable(funcao):
            try:
                texto = funcao()
                if texto:
                    return texto.strip()
            except Exception:
                continue
    return ''


def _sinalizar_abertura():
    _definir(MARCA_ABERTA, '1')


class WelcomeDialog(xbmcgui.WindowXMLDialog):
    """Mesma tela do pacote; aqui so encaminhamos as acoes para o projeto."""

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)
        self.saiu = False
        self._ultimo_foco = 310
        self._foco_anterior = 310

    # --- foco / D-pad -----------------------------------------------------
    def _grupo_visivel(self, grupo=900):
        """O grupo do dialogo ja foi desenhado pelo Kodi?"""
        try:
            controle = self.getControl(grupo)
            return bool(controle.isVisible())
        except Exception:
            # Em teste (stub) nao existe isVisible; o comportamento antigo vale.
            return True

    def _focar(self, controle, tentativas=8):
        """Coloca o foco DEPOIS que o Kodi desenhou a visibilidade.

        O ``setFocusId`` antigo era chamado no mesmo clique que ligava a
        condicao ``welcome_dialog=ads``. Nesse instante o grupo 900 ainda
        estava invisivel e o Kodi recusava o foco em silencio: o controle
        ficava sem destino e o D-pad so voltava depois de um toque na tela.
        Aqui esperamos o grupo aparecer e confirmamos por ``getFocusId``. O
        segundo ``setFocusId`` vence a memoria de foco do Kodi, que podia
        restaurar o 906 (botao da direita) ao reabrir o dialogo.
        """
        destino = int(controle)
        dialogo = self.getProperty(PROP_DIALOGO)
        if dialogo == 'ads':
            for _ in range(12):
                if self._grupo_visivel(900):
                    break
                try:
                    xbmc.sleep(40)
                except Exception:
                    break
        # A validacao VIP roda numa thread: nesse caso o foco vai pelo builtin
        # (fila da thread de interface), nunca por setFocusId direto.
        na_thread = threading.current_thread() is not threading.main_thread()
        for tentativa in range(max(1, int(tentativas))):
            try:
                if na_thread:
                    xbmc.executebuiltin('SetFocus(%d)' % destino)
                else:
                    self.setFocusId(destino)
                atual = int(self.getFocusId() or 0)
                if atual == destino:
                    if dialogo == 'ads' and tentativa == 0:
                        # Deixa o Kodi aplicar a visibilidade do grupo; se ele
                        # restaurar a memoria (906), a proxima volta corrige.
                        try:
                            xbmc.sleep(80)
                        except Exception:
                            pass
                        if int(self.getFocusId() or 0) != destino:
                            continue
                    self._ultimo_foco = destino
                    return True
            except Exception:
                pass
            if tentativa + 1 < tentativas:
                try:
                    xbmc.sleep(50)
                except Exception:
                    pass
        _log('nao consegui confirmar o foco no controle %d' % destino,
             xbmc.LOGWARNING)
        return False

    def _foco_atual(self):
        try:
            return int(self.getFocusId() or 0)
        except Exception:
            return 0

    def _destino_de_foco(self):
        """Controle valido para o estado atual (dialogo aberto ou tela)."""
        dialogo = self.getProperty(PROP_DIALOGO)
        foco = self._foco_atual()
        if dialogo == 'ads':
            return 905 if foco not in FOCO_ADS else None
        if dialogo == 'status':
            return 955 if foco != 955 else None
        if foco not in FOCO_PRINCIPAL:
            return (self._ultimo_foco if self._ultimo_foco in FOCO_PRINCIPAL
                    else 310)
        return None

    def _garantir_foco(self):
        """Rede de seguranca chamada antes de cada tecla de navegacao."""
        destino = self._destino_de_foco()
        if destino is not None:
            self._focar(destino)
        return destino

    # --- dialogos ---------------------------------------------------------
    def _dialogo(self, titulo, texto, ok='Entendi'):
        for chave, valor in ((PROP_TITULO, titulo), (PROP_TEXTO, texto),
                             (PROP_OK, ok)):
            self.setProperty(chave, valor)
        self.setProperty(PROP_DIALOGO, 'status')
        self._focar(955)

    def _fechar_dialogo(self, foco=None):
        self.clearProperty(PROP_DIALOGO)
        destino = foco if foco is not None else (self._foco_anterior or 311)
        if destino not in FOCO_PRINCIPAL:
            destino = 311
        self._focar(destino)

    # --- acoes ligadas ao que ja existe no projeto -----------------------
    def _intent_navegador(self,url):
        """Sai do Kodi e entrega a URL ao navegador padrao do Android.

        Assinatura real: StartAndroidActivity(package,intent,dataType,dataURI).
        O pacote vai vazio (intent implicito). No Android isso vira
        ``setPackage(null)``, e o navegador padrao do aparelho abre por cima
        do Kodi. Devolve True quando o builtin foi aceito pelo Kodi.
        """
        comando = 'StartAndroidActivity(,android.intent.action.VIEW,,%s)' % url
        _log('[SMARTEDTV] Abrindo no navegador do Android: %s' % url)
        try:
            xbmc.executebuiltin(comando)
            _log('[SMARTEDTV] Intent entregue ao Android: %s' % comando)
            return True
        except Exception as erro:
            _log('[SMARTEDTV] StartAndroidActivity falhou (%s): %s'
                 % (comando, erro), xbmc.LOGERROR)
            return False

    def _abrir_checkout(self):
        """ID 120 - Abre o checkout da Cakto no navegador externo do Android."""
        url = CHECKOUT
        vip = _vip()
        if vip is not None:
            url = getattr(vip, 'CHECKOUT', CHECKOUT) or CHECKOUT
            try:
                if vip.abrir_checkout():
                    _log('[SMARTEDTV] Checkout aberto via vip.abrir_checkout(): %s'
                         % url)
                    return
            except Exception as erro:
                _log('[SMARTEDTV] vip.abrir_checkout falhou: %s' % erro,
                     xbmc.LOGWARNING)
        _log('[SMARTEDTV] Botao 120 (checkout) acionado. URL: %s' % url)
        if self._intent_navegador(url):
            return
        self._dialogo('Checkout indisponível',
                      'Não consegui abrir o pagamento neste aparelho. '
                      'Aponte a câmera para o QR Code ao lado.')

    def _abrir_dropbox(self):
        """ID 121 - Abre o Dropbox verdadeiro no navegador externo.

        Reutiliza a configuracao existente (vip.DROPBOX_URL), que e o mesmo
        endereco gravado no QR Code qr_apk.png. A pagina do Dropbox abre no
        navegador padrao do Android e permite baixar o APK.
        """
        url = DROPBOX_URL
        vip = _vip()
        if vip is not None:
            url = (_link_do_dropbox_desta_versao(vip)
                   or getattr(vip, 'DROPBOX_URL', DROPBOX_URL) or DROPBOX_URL)
            try:
                if hasattr(vip, 'abrir_dropbox') and vip.abrir_dropbox():
                    _log('[SMARTEDTV] Dropbox aberto via vip.abrir_dropbox(): %s'
                         % url)
                    return
                if vip.abrir_url(url, 'Dropbox'):
                    _log('[SMARTEDTV] Dropbox aberto via vip.abrir_url(): %s' % url)
                    return
            except Exception as erro:
                _log('[SMARTEDTV] vip.abrir_url(Dropbox) falhou: %s' % erro,
                     xbmc.LOGWARNING)
        _log('[SMARTEDTV] Botao 121 (Dropbox) acionado. URL: %s' % url)
        if self._intent_navegador(url):
            return
        self._dialogo('Dropbox indisponível',
                      'Não consegui abrir o link do Dropbox neste aparelho. '
                      'Aponte a câmera para o QR Code ao lado.')

    def _compartilhar(self):
        """Compartilhamento nativo Android (ACTION_SEND).

        Continua disponivel em 121 por toque longo, para nao perder a funcao
        que ja existia: abre o menu do Android (WhatsApp, Telegram, Gmail)
        com o link de download do APK do Dropbox.
        """
        mensagem = 'Baixe o SMARTEDTV aqui: %s' % APK_DOWNLOAD
        _log('[SMARTEDTV] Compartilhamento nativo acionado. Link: %s'
             % APK_DOWNLOAD)
        vip = _vip()
        if vip is not None:
            try:
                if vip.compartilhar():
                    _log('[SMARTEDTV] Compartilhamento nativo aberto via vip.')
                    return
            except Exception as erro:
                _log('[SMARTEDTV] vip.compartilhar falhou: %s' % erro,
                     xbmc.LOGWARNING)
        # Fallback: ACTION_SEND direto (mesma ordem package,intent,type,data;
        # o texto vai em extras JSON, entre aspas, para o parser do Kodi).
        extras = ('[{"type":"string","key":"android.intent.extra.TEXT",'
                  '"value":"%s"}]' % mensagem)
        comando = ('StartAndroidActivity(,android.intent.action.SEND,text/plain,'
                   '%s,,"%s")' % (APK_DOWNLOAD, extras.replace('"', '\\"')))
        try:
            xbmc.executebuiltin(comando)
            _log('[SMARTEDTV] Compartilhamento aberto via StartAndroidActivity.')
            return
        except Exception as erro:
            _log('[SMARTEDTV] StartAndroidActivity SEND falhou: %s' % erro,
                 xbmc.LOGERROR)
        self._dialogo('Compartilhamento indisponível',
                      'Não consegui abrir o compartilhamento neste aparelho.')

    def _baixar_apk(self):
        """ID 122 - Abre o download direto do APK no navegador do Android.

        O arquivo vem SEMPRE da pasta publicada (``SMARTEDTV UNIVERSAL``). Se
        ela nao estiver configurada, o aviso diz o que falta - nada e baixado
        de lugar desconhecido.
        """
        url = APK_DOWNLOAD
        vip = _vip()
        if vip is not None:
            try:
                if hasattr(vip, 'dropbox_configurado') and not vip.dropbox_configurado():
                    pasta = getattr(vip, 'pasta_nome', lambda: '?')()
                    _log('[SMARTEDTV] download: pasta %s nao configurada' % pasta,
                         xbmc.LOGWARNING)
                    self._dialogo(
                        'Atualizacao nao configurada',
                        'Esta versao consulta a pasta %s do Dropbox, que ainda '
                        'nao foi publicada. Nada sera baixado para nao instalar '
                        'a versao errada.' % pasta)
                    return
            except Exception as erro:
                _log('[SMARTEDTV] checagem da pasta do Dropbox falhou: %s'
                     % erro, xbmc.LOGWARNING)
            # Mesmo contrato do vip.py: pede o arquivo PELO NOME na pasta
            # publicada, entao o link nunca fica preso a uma versao antiga.
            por_nome = getattr(vip, 'url_do_apk_por_nome', None)
            if callable(por_nome):
                url = por_nome() or APK_DOWNLOAD
            else:
                url = getattr(vip, 'APK', APK_DOWNLOAD) or APK_DOWNLOAD
            try:
                if hasattr(vip, 'open_apk_download') and vip.open_apk_download():
                    _log('[SMARTEDTV] Download do APK aberto via vip.')
                    return
                if vip.abrir_url(url, 'download do APK'):
                    _log('[SMARTEDTV] Download do APK aberto: %s' % url)
                    return
            except Exception as erro:
                _log('[SMARTEDTV] vip.open_apk_download falhou: %s' % erro,
                     xbmc.LOGWARNING)
        _log('[SMARTEDTV] Botao 122 (baixar APK) acionado. URL: %s' % url)
        if self._intent_navegador(url):
            return
        self._dialogo('Download indisponível',
                      'Não consegui abrir o link de download neste aparelho.')

    def _atualizar(self):
        """ATUALIZAR APLICATIVO: consulta manifesto, baixa, verifica e instala."""
        _log('[SMARTEDTV] Botao atualizar aplicativo acionado.')
        vip = _vip()
        if vip is not None:
            try:
                if vip.procurar_atualizacao():
                    _log('[SMARTEDTV] Fluxo de atualizacao iniciado via vip.procurar_atualizacao().')
                    return
            except Exception as erro:
                _log('[SMARTEDTV] vip.procurar_atualizacao falhou: %s' % erro,
                     xbmc.LOGWARNING)
        # Mesmo fallback do botao 122: arquivo de nome fixo do Dropbox com
        # validacao de nome/tamanho. Abrir DROPBOX_URL cru mostrava a pagina
        # do arquivo antigo (o /scl/fi/ resolve pelo ID, nao pelo nome).
        _log('[SMARTEDTV] Fallback: abrindo o download do APK publicado.')
        if self._intent_navegador(APK_DOWNLOAD):
            return
        self._dialogo('Atualizacao indisponível',
                      'Não consegui verificar atualizacoes neste aparelho.')

    def _digitar_codigo(self):
        """Abre o teclado do Kodi (o unico compativel com este APK) e devolve o texto.

        O controle edit 310 tambem abre o teclado ao ser clicado; esta funcao e
        usada pelo botao Ativar quando o campo esta vazio. O conteudo atual e a
        area de transferencia (quando o Kodi expuser getClipboard) entram como
        valor inicial, para colar um codigo copiado de outro aplicativo sem
        duplicar caracteres. O texto devolvido e aparado apenas nas pontas.
        """
        try:
            atual = (self.getControl(310).getText() or '').strip()
        except Exception:
            atual = ''
        inicial = atual or _clipboard()
        try:
            codigo = xbmcgui.Dialog().input(
                'Digite o código de ativação',
                defaultt=inicial,
                type=xbmcgui.INPUT_ALPHANUM,
            )
        except TypeError:
            # assinaturas antigas nao aceitam defaultt
            codigo = xbmcgui.Dialog().input('Digite o código de ativação')
        if not codigo:
            return ''
        codigo = codigo.strip()
        try:
            self.getControl(310).setText(codigo)
        except Exception:
            pass
        return codigo

    def _ativar_codigo(self):
        """Valida o codigo em segundo plano (nao bloqueia a interface).

        A chamada de rede roda numa thread; o callback onClick volta na hora e a
        tela continua respondendo. O resultado e publicado nas propriedades do
        dialogo de status, que o botao 955 fecha. Se o servidor nao responder
        dentro do prazo, um vigia libera a tela para tentar de novo.
        """
        _log('[SMARTEDTV] Botao ativar codigo acionado.')
        if getattr(self, '_validando', False):
            _log('[SMARTEDTV] Ativacao ja em andamento; ignorando clique.')
            return
        vip = _vip()
        if vip is None:
            _log('[SMARTEDTV] Falha: modulo vip nao disponivel para ativacao.',
                 xbmc.LOGERROR)
            self._dialogo('Ativação indisponível',
                          'A ativação por código não está disponível neste aparelho.')
            return
        try:
            codigo = (self.getControl(310).getText() or '').strip()
        except Exception:
            codigo = ''
        if not codigo:
            _log('[SMARTEDTV] Campo de codigo vazio, abrindo teclado do Kodi.')
            codigo = self._digitar_codigo()
        if not codigo:
            _log('[SMARTEDTV] Nenhum codigo informado. Cancelado pelo usuario.')
            self._focar(310)
            return
        codigo = codigo.strip()
        _log('[SMARTEDTV] Codigo recebido (%s); iniciando validacao.'
             % _mascarar(codigo))

        self._ultimo_foco = 311
        self._foco_anterior = 311
        self._validando = True
        self._geracao_validacao = getattr(self, '_geracao_validacao', 0) + 1
        geracao = self._geracao_validacao
        self.setProperty(PROP_TITULO, 'Validando')
        self.setProperty(PROP_TEXTO, 'Validando seu código...')
        self.setProperty(PROP_OK, 'Aguarde')
        self.setProperty('welcome_status_action', '')
        self.setProperty(PROP_DIALOGO, 'status')
        self._focar(955)

        def trabalho():
            try:
                ok, mensagem = vip.validar(codigo)
            except Exception as erro:
                _log('[SMARTEDTV] Erro ao validar codigo: %s' % erro,
                     xbmc.LOGERROR)
                ok, mensagem = (False,
                                'Não foi possível validar agora. Tente novamente.')
            self._concluir_validacao(geracao, ok, mensagem)

        def vigia():
            # teto de seguranca: nenhuma tela fica presa em "Validando..."
            time.sleep(30)
            try:
                if (getattr(self, '_validando', False)
                        and getattr(self, '_geracao_validacao', 0) == geracao):
                    self._validando = False
                    self.setProperty(PROP_TITULO, 'Servidor indisponível')
                    self.setProperty(PROP_TEXTO,
                                     'Servidor de ativação temporariamente indisponível.')
                    self.setProperty(PROP_OK, 'Tentar novamente')
                    self.setProperty('welcome_status_action', '')
            except Exception:
                # a janela pode ter sido fechada enquanto a rede demorava
                pass

        # Em teste/simulador (sem Android) roda sincrono para o roteiro
        # conseguir conferir o resultado; no aparelho a rede vai para a thread.
        try:
            android = bool(xbmc.getCondVisibility('System.Platform.Android'))
        except Exception:
            android = False
        if not android:
            trabalho()
        else:
            thread = threading.Thread(target=trabalho, name='smarted-vip-validar')
            thread.daemon = True
            thread.start()
            vigia_thread = threading.Thread(target=vigia, name='smarted-vip-vigia')
            vigia_thread.daemon = True
            vigia_thread.start()

    def _concluir_validacao(self, geracao, ok, mensagem):
        """Publica o resultado; ignora resultado de uma tentativa ja vencida."""
        if getattr(self, '_geracao_validacao', 0) != geracao:
            return
        try:
            self._validando = False
        except Exception:
            return
        if ok:
            texto = 'VIP ativado com sucesso!'
            titulo = 'VIP ativado'
            acao = 'Começar a assistir'
            _log('[SMARTEDTV] Codigo ativado com sucesso; licenca gravada em vip.json.')
            # Unico ponto em que o app passa a abrir direto na Home: ativacao
            # com codigo valido. Sair pela tela sem ativar nao grava a marca.
            marcar_entrada_vista()
        else:
            texto = mensagem or 'Este código não é válido. Verifique e tente novamente.'
            titulo = 'Código não ativado'
            acao = 'Tentar novamente'
            _log('[SMARTEDTV] Codigo nao ativado: %s' % texto, xbmc.LOGWARNING)
        try:
            self.setProperty(PROP_TITULO, titulo)
            self.setProperty(PROP_TEXTO, texto)
            self.setProperty(PROP_OK, acao)
            self.setProperty('welcome_status_action', 'home' if ok else '')
            self.setProperty(PROP_DIALOGO, 'status')
            self._focar(955)
        except Exception:
            # janela ja fechada: o resultado nao tem onde aparecer
            pass

    def _modo_gratuito(self):
        """Fecha a entrada e libera a Home (versao com anuncios, como hoje)."""
        self._sair()

    def _sair(self):
        self.saiu = True
        # Marca que a tela esta saindo ANTES de fechar. O vigia espera a
        # troca normal terminar; so assume se ela travar (6 s). Sem isso,
        # dois ActivateWindow/ReplaceWindow concorrentes podiam deixar preto.
        _definir(MARCA_HOME, 'saindo')
        _definir(MARCA_SAIU, '1')      # o vigia sabe que a tela saiu de cena
        self.close()

    # --- eventos ---------------------------------------------------------
    def onClick(self, control_id):
        _log('[SMARTEDTV] onClick recebido: control_id=%s' % control_id)
        # OK do dialogo de STATUS: precisa ser tratado ANTES do fechamento
        # generico, senao o sucesso do VIP nunca chega a abrir a Home.
        if control_id == 955 and self.getProperty(PROP_DIALOGO) == 'status':
            if getattr(self, '_validando', False):
                _log('[SMARTEDTV] Validacao em andamento; OK somente depois do resultado.')
                return
            acao = self.getProperty('welcome_status_action')
            _log('[SMARTEDTV] Status OK; acao=%r' % acao)
            self._fechar_dialogo()
            if acao == 'home':
                self._sair()
            return
        if self.getProperty(PROP_DIALOGO):
            # qualquer clique com dialogo aberto so fecha o dialogo
            _log('[SMARTEDTV] Dialogo aberto (%s), fechando dialogo.',
                 self.getProperty(PROP_DIALOGO))
            if control_id in (905, 955):
                self._fechar_dialogo()
            elif control_id == 906:
                self._fechar_dialogo(312)
                self._sair()
            return
        if control_id == 312:
            _log('[SMARTEDTV] Botao 312 (Assistir com anuncios) acionado.')
            self._ultimo_foco = 312
            self._foco_anterior = 312
            self.setProperty(PROP_DIALOGO, 'ads')
            self._focar(905)
        elif control_id == 905:
            _log('[SMARTEDTV] Botao 905 (Voltar do dialogo ads) acionado.')
            self._fechar_dialogo(312)
        elif control_id == 906:
            _log('[SMARTEDTV] Botao 906 (Continuar com anuncios) acionado.')
            self._fechar_dialogo(312)
            self._modo_gratuito()
        elif control_id == 955:
            _log('[SMARTEDTV] Botao 955 (OK do dialogo status) acionado.')
            if getattr(self, '_validando', False):
                _log('[SMARTEDTV] Validacao em andamento; OK somente depois do resultado.')
                return
            acao = self.getProperty('welcome_status_action')
            self._fechar_dialogo()
            if acao == 'home':
                # Sucesso do codigo: fecha a entrada; o fluxo normal abre a Home
                # (nada de RestartApp, nada de fechar o app).
                self._sair()
        elif control_id == 120:
            self._abrir_checkout()
        elif control_id == 121:
            self._abrir_dropbox()
        elif control_id == 122:
            self._baixar_apk()
        elif control_id == 123:
            self._atualizar()
        elif control_id == 311:
            self._ativar_codigo()
        elif control_id == 310:
            _log('[SMARTEDTV] Campo 310 (codigo) recebeu foco/clique.')
        # 130/131 (seletor de aparelho) e 140/141 (planos) sairam da tela: a
        # tela e 16:9 fixa e quem define a validade do codigo e o servidor.
        # Clique nesses ids nao faz nada (ver tests).

    def onAction(self, action):
        acao = _id_acao(action)
        # Qualquer seta/OK: se o foco caiu (controle invisivel, dialogo que
        # acabou de abrir), devolve para um controle valido em vez de deixar o
        # D-pad sem destino. O toque na tela deixava de ser necessario.
        if acao in (getattr(xbmcgui, 'ACTION_MOVE_LEFT', 1),
                    getattr(xbmcgui, 'ACTION_MOVE_RIGHT', 2),
                    getattr(xbmcgui, 'ACTION_MOVE_UP', 3),
                    getattr(xbmcgui, 'ACTION_MOVE_DOWN', 4),
                    getattr(xbmcgui, 'ACTION_SELECT_ITEM', 7),
                    getattr(xbmcgui, 'ACTION_ENTER', 13)):
            if self._garantir_foco() is not None:
                # primeiro toque so devolve o foco; o proximo ja navega
                return
        # Toque longo no 121 preserva o compartilhamento nativo que existia
        # antes de o botao virar o atalho do Dropbox (o visual nao muda).
        if acao == getattr(xbmcgui, 'ACTION_CONTEXT_MENU', 117):
            foco = self._foco_atual()
            if foco == 121:
                self._compartilhar()
                return
        if acao in (getattr(xbmcgui, 'ACTION_NAV_BACK', 92),
                    getattr(xbmcgui, 'ACTION_PREVIOUS_MENU', 10)):
            if self.getProperty(PROP_DIALOGO) == 'ads':
                self._fechar_dialogo(312)
                return
            if self.getProperty(PROP_DIALOGO) == 'status':
                if getattr(self, '_validando', False):
                    _log('[SMARTEDTV] VOLTAR ignorado: validacao em andamento.')
                    return
                self._fechar_dialogo()
                return
            self._sair()

    def onInit(self):
        # a tela desenhou: o vigia `seguro=1` pode dormir (nao ha mais alarme
        # de 30 s no Startup.xml — era ele que deixava a tela preta)
        self.saiu = False
        _limpar(MARCA_SAIU)
        _limpar_guarda_de_saida()
        _limpar(PROP_TECLADO)      # propriedade antiga; o overlay nao existe mais
        _sinalizar_abertura()
        try:
            # o Startup.xml deixa um alarme de Home para o caso de este addon
            # estar desabilitado; a tela viva cancela para nao cobrir a entrada.
            xbmc.executebuiltin('CancelAlarm(%s,silent)' % ALARME_SEGURO)
        except Exception:
            pass
        _log('tela de entrada carregada (antes da Home)')
        # O foco tambem era negado enquanto o XML ainda nao tinha desenhado;
        # a tela abria sem destino para o D-pad ate um toque.
        self._focar(310)


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


def _ir_para_home(motivo='', forcar=False):
    """Abre a Home DEPOIS que a tela saiu de cena. Nunca deixa tela preta.

    1. `ActivateWindow(Home)` — caminho normal (o Kodi carrega a janela ao
       ativa-la, mesmo com a Home ainda nao criada);
    2. `ReplaceWindow(Home)` — se a ativacao nao pegou;
    3. confirma por ate 5 s olhando `System.CurrentWindow`;
    4. se nada funcionou, tenta a Home mais uma vez e avisa o usuario — NAO
       reinicia o app (o pedido expresso e que o app nunca feche sozinho).

    O antigo comando do Startup.xml
    (`ReplaceWindow($INFO[System.StartupWindow])`) NAO e usado aqui: ele aponta
    para a janela de startup, que ja morreu — era a causa da tela preta.
    """
    if motivo:
        _log('abrindo a Home: %s' % motivo, xbmc.LOGWARNING)
    if _propriedade(MARCA_HOME) == 'ok' and _tela_da_home():
        return True
    if _propriedade(MARCA_HOME) == 'abrindo' and not forcar:
        # Outro processo ja esta abrindo; nao dispara comandos concorrentes.
        limite = time.time() + 3.0
        while time.time() < limite:
            if _tela_da_home() or _propriedade(MARCA_HOME) == 'ok':
                return True
            try:
                xbmc.sleep(250)
            except Exception:
                pass
    # O Kodi nao pode continuar com o alarme de seguranca do Startup.xml: ele
    # abriria a Home 25 s depois do boot, por cima do que o usuario estiver
    # fazendo (inclusive por cima de um video aberto).
    _comando_ok('CancelAlarm(%s,silent)' % ALARME_SEGURO, espera=0)
    # guarda da SAIDA: se este processo foi reutilizado de uma sessao encerrada,
    # o timer antigo continuaria contando e mataria a sessao nova.
    _limpar_guarda_de_saida()
    _definir(MARCA_HOME, 'abrindo')
    _definir(MARCA_ABERTA, '1')      # a partir daqui o vigia nao age sozinho

    # `ActivateWindow(Home,return)` NAO e o comando certo: o segundo argumento
    # e um caminho, e "return" nao e caminho valido. Usa a forma oficial.
    # O ``ActivateWindow`` e RECUSADO pelo Kodi enquanto existe dialogo modal na
    # tela ("Activate of window '10000' refused because there are active modal
    # dialogs"). Foi assim que a Home nao abriu no projetor: a janela de entrada
    # estava fechando e um dialogo modal ainda estava no ar. Fechar os dialogos
    # sem conteudo do app antes de pedir a Home nao esconde erro nenhum: o
    # dialogo em questao e de outro addon, e o app segue com a Home dele.
    _comando_ok('Dialog.Close(all,true)', espera=0.3)
    _comando_ok('ActivateWindow(Home)', espera=1.2)
    if _tela_da_home():
        _log('Home ativa (ActivateWindow)')
        _definir(MARCA_HOME, 'ok')
        return True

    _log('ActivateWindow(Home) nao apareceu; tentando ReplaceWindow(Home)',
         xbmc.LOGWARNING)
    _comando_ok('Dialog.Close(all,true)', espera=0.2)
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

    # Ultima tentativa sem reiniciar: uma Home ja carregada pode estar apenas
    # escondida atras da janela que acabou de fechar.
    _log('a Home nao apareceu; tentando ActivateWindow(Home) novamente',
         xbmc.LOGERROR)
    _comando_ok('Dialog.Close(all,true)', espera=0.2)
    _comando_ok('ActivateWindow(Home)', espera=1.0)
    if _tela_da_home():
        _log('Home ativa (segunda tentativa)')
        _definir(MARCA_HOME, 'ok')
        return True
    # NUNCA RestartApp/close aqui: isso era o "app fecha sozinho". O aviso fica
    # na tela e o vigia da tela de entrada ainda pode abrir a Home; se nada
    # funcionar, o usuario usa VOLTAR em vez de perder o app.
    _definir(MARCA_HOME, 'falhou')
    _definir(MARCA_ABERTA, '1')
    try:
        xbmc.executebuiltin('Notification(SMARTEDTV, Toque em VOLTAR para abrir o menu, 8000)')
    except Exception:
        pass
    _log('Home nao abriu; o app foi mantido aberto (sem RestartApp).',
         xbmc.LOGERROR)
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


def _vigiar_depois_da_tela(prazo=30):
    """A tela assumiu: se ela sair de cena sem a Home, abre a Home.

    Espera a Home normal antes de assumir. O ``_sair()`` marca
    ``smartedtv.welcome.home=abrindo`` antes de fechar; o vigia so age se,
    depois de 6 s, ninguem concluiu a troca (script morreu/travou). Assim nao
    existem dois ``ActivateWindow(Home)`` concorrentes, outra causa de preto.
    """
    limite = time.time() + prazo
    saiu_em = None
    while time.time() < limite:
        if _propriedade(MARCA_HOME) == 'ok' or _tela_da_home():
            return True
        if _propriedade(MARCA_SAIU):
            if saiu_em is None:
                saiu_em = time.time()
            elif time.time() - saiu_em >= 6.0:
                _log('vigia: a tela saiu e a Home nao veio em 6 s; assumindo',
                     xbmc.LOGWARNING)
                _ir_para_home('vigia (troca de janela travou)', forcar=True)
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
        janela = WelcomeDialog(_xml_da_tela(pasta), pasta, 'Default', '1080i')
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
        _comando_ok('ActivateWindow(Home)', espera=0.6)
    _limpar(MARCA_SAIU)
    _definir(MARCA_HOME, 'ok')      # a Home ja estava no ar: troca concluida
    return True


# Saida do aplicativo.
#
# Historico (o que causou "fechar e nao abrir mais"):
#
#   * o ultimo recurso da saida era um thread com `time.sleep(15)` e
#     encerrar o processo a forca. Se o Android reabria o app antes dos 15 s - o caso tipico,
#     sair e abrir em seguida -, o thread antigo matava a sessao NOVA;
#   * depois virou um `AlarmClock` do Kodi. Mas o `RunScript` que o alarme
#     dispara executa o script do comeco: `seguro_quit` tambem casa com a
#     verificacao `if 'seguro' in argumento` do topo do `main`. Ou seja, 15 s
#     depois de sair, o que rodava era o VIGIA DE BOOT (`vigiar_inicializacao`)
#     num processo que estava morrendo;
#   * e o encerramento a forca continuava existindo: se o Quit nao terminasse,
#     o app era morto por dentro. Processo morto assim nao e reaberto em estado
#     limpo no Android: o `Splash` reusa a tarefa velha e o app volta preto ou
#     nao volta.
#
# Agora NAO existe mais nenhum caminho de codigo que encerre o processo:
#   * o pedido e o `Quit` nativo do Kodi, que e o caminho que o proprio Kodi
#     usa (e que a versao do Kodi deste APK, 21.x Omega, tem corrigido: o
#     "tela preta ao voltar de minimizado" foi consertado no 21.2);
#   * a saida GRAVA a marca `smarted-saindo`, e o boot seguinte sabe que veio
#     de uma saida e entra direto na Home, sem reabrir a tela de entrada;
#   * quem reabre o app e o Android; nenhum script nosso mata nem reinicia o
#     processo. Se o sistema demorar a encerrar o processo antigo, isso e
#     resolvido esperando: nada de encerrar a forca, `Kill`, `Shutdown` ou
#     `RestartApp`.
MARCA_SAIDA = 'smarted-saindo'
JANELA_SAIDA = 60      # segundos: reabrir antes disso = sessao nova (nao bloqueia nada)

# Marca de "a tela de entrada JA foi vista E a ativacao foi concluida".
#
# Regra do aplicativo: abrir direto na Home SO com codigo de ativacao ativado.
# Sem essa marca (aparelho novo, ou saida pela tela sem ativar) o boot abre a
# tela de ativacao; com ela, o boot vai direto para a Home. A marca so e
# gravada no caminho de sucesso da ativacao (`_concluir_validacao`, ok=True).
# Quem decide de fato e `vip.ativa()`: se a licenca vencer ou for apagada, a
# tela volta a aparecer mesmo com a marca no disco.
MARCA_ENTRADA_VISTA = 'smarted-entrada-vista'


def _caminho_marca_saida():
    """Caminho da marca (``special://profile`` ja traduzido pelo Kodi)."""
    try:
        return xbmcvfs.translatePath('special://profile/addon_data/' +
                                     ADDON_ID + '/' + MARCA_SAIDA)
    except Exception:
        return ''


def _instante_de_saida():
    """Quando a sessao anterior pediu para sair (0 se nunca/arquivo ilegivel)."""
    caminho = _caminho_marca_saida()
    if not caminho or not xbmcvfs.exists(caminho):
        return 0.0
    try:
        arquivo = xbmcvfs.File(caminho)
        try:
            texto = arquivo.read() or ''
        finally:
            arquivo.close()
        if isinstance(texto, bytes):
            texto = texto.decode('utf-8', 'replace')
        return float(str(texto).strip().split()[0])
    except Exception:
        return 0.0


def _caminho_entrada_vista():
    try:
        return xbmcvfs.translatePath('special://profile/addon_data/' +
                                     ADDON_ID + '/' + MARCA_ENTRADA_VISTA)
    except Exception:
        return ''


def entrada_ja_vista():
    """A tela de ativacao ja foi vista neste aparelho (nao e 1a abertura)?"""
    caminho = _caminho_entrada_vista()
    if not caminho:
        return False
    try:
        return bool(xbmcvfs.exists(caminho))
    except Exception:
        return False


def ativacao_concluida():
    """Abrir direto na Home? So com codigo de ativacao ativado e valido.

    A prova e o `vip.ativa()`: licenca gravada em vip.json e dentro do prazo -
    ou seja, um codigo de ativacao foi aceito pelo servidor neste aparelho.
    Sem licenca (aparelho novo, ou quem saiu pela tela sem ativar) a tela de
    ativacao aparece. Licenca vencida tambem traz a tela de volta.

    A marca `smarted-entrada-vista` NAO libera nada sozinha: ela existe como
    registro de quando a ativacao concluiu neste aparelho (fica no log e serve
    para diagnostico), mas quem decide e a licenca.
    """
    vip = _vip()
    if vip is None or not callable(getattr(vip, 'ativa', None)):
        # sem o modulo de licenca nao ha como confirmar ativacao: mantem a tela
        return False
    try:
        return bool(vip.ativa())
    except Exception as erro:
        _log('ativacao_concluida: falha ao consultar a licenca (%s)' % erro,
             xbmc.LOGWARNING)
        return False


def marcar_entrada_vista():
    """Grava a marca que faz os proximos boots irem direto para a Home."""
    caminho = _caminho_entrada_vista()
    if not caminho or not os.path.isabs(caminho):
        return False
    pasta = os.path.dirname(caminho)
    try:
        if pasta and not xbmcvfs.exists(pasta):
            xbmcvfs.mkdirs(pasta)
        arquivo = xbmcvfs.File(caminho, 'w')
        try:
            arquivo.write('%d\n' % int(time.time()))
        finally:
            arquivo.close()
        return True
    except Exception as erro:
        _log('entrada vista: nao foi possivel gravar a marca (%s)' % erro,
             xbmc.LOGWARNING)
        return False


def _marcar_saida(quando=None):
    """Grava QUANDO esta sessao pediu para sair (sobrevive ao processo).

    Esta escrita e o que o proximo boot usa para saber que o app foi reaberto
    (e nao recem-instalado). Uma falha aqui NAO pode impedir a saida - mas
    tambem nao pode passar em silencio: fica no log.
    """
    caminho = _caminho_marca_saida()
    if not caminho or not os.path.isabs(caminho):
        # caminho nao resolvido (fora do Kodi): nao grava nada em lugar nenhum
        return False
    linha = '%d %d\n' % (int(quando or time.time()), os.getpid())
    pasta = os.path.dirname(caminho)
    if pasta:
        # xbmcvfs.mkdirs cria a pasta do addon no perfil real; em teste (vfs de
        # mentira) nao faz nada. Nada de os.makedirs com caminho 'special://'.
        try:
            if not xbmcvfs.exists(pasta):
                xbmcvfs.mkdirs(pasta)
        except Exception:
            pass
    try:
        arquivo = xbmcvfs.File(caminho, 'w')
        try:
            arquivo.write(linha)
        finally:
            arquivo.close()
        return True
    except Exception as erro:
        # Nao impede a saida: sem a marca o proximo boot apenas abre a tela de
        # entrada normalmente (comportamento antigo). Fica registrado porque e
        # exatamente esta escrita que faz a reabertura cair na Home.
        _log('marca de saida: nao foi possivel gravar %s (%s)'
             % (caminho, erro), xbmc.LOGWARNING)
        return False


def _limpar_marca_de_saida():
    caminho = _caminho_marca_saida()
    if not caminho:
        return False
    try:
        if xbmcvfs.exists(caminho):
            xbmcvfs.delete(caminho)
        return True
    except Exception:
        return False


def _limpar_guarda_de_saida():
    """Boot: desarma o ultimo recurso de uma saida anterior, se ainda valer.

    Chamado quando a interface aparece. Se o app foi reaberto ha menos de
    JANELA_SAIDA segundos, o alarme da sessao anterior e cancelado para nao
    derrubar esta sessao. O arquivo-marca e sempre removido.
    """
    desde = _instante_de_saida()
    if desde:
        # De uma versao anterior (que ainda tinha alarme) pode ter sobrado um
        # alarme armado: cancelar por precaucao nao custa nada. Versao nova nao
        # arma nenhum.
        try:
            xbmc.executebuiltin('CancelAlarm(smartedtv_sair_guarda,silent)')
        except Exception:
            pass
        _log('saida anterior ha %.0f s: marca da sessao limpa' %
             max(0.0, time.time() - desde))
    _limpar_marca_de_saida()
    return desde

def _veio_de_uma_saida(janela=None):
    """O boot atual e o do app reaberto depois de SAIR?

    O Android pode eliminar o processo e recriar a Activity do zero (o caso
    normal de "fechar e abrir de novo", principalmente em Android antigo). A
    marca `smarted-saindo` fica em disco e sobrevive a isso: quando ela existe e
    e recente, este boot NAO e uma primeira instalacao. Sem essa informacao o
    boot abria a tela de entrada de novo, com o QR/codigo, e o usuario tinha a
    impressao de que "o app nao abriu".
    """
    desde = 0.0
    caminho = _caminho_marca_saida()
    # le SEM apagar: quem apaga e o caminho de boot depois de decidir
    texto = ''
    try:
        if caminho and os.path.isabs(caminho) and xbmcvfs.exists(caminho):
            arquivo = xbmcvfs.File(caminho)
            try:
                texto = arquivo.read() or ''
            finally:
                arquivo.close()
    except Exception:
        texto = ''
    if isinstance(texto, bytes):
        texto = texto.decode('utf-8', 'replace')
    try:
        desde = float(str(texto).strip().split()[0])
    except (IndexError, ValueError):
        desde = 0.0
    if not desde:
        return False
    # Entre a saida e a reabertura so passou isso: reabertura, nao instalacao.
    return (time.time() - desde) < (janela or JANELA_SAIDA)




def nao_encerrar_o_processo(*_args, **_kwargs):
    """Mantido por compatibilidade: NAO encerra mais nada.

    Antes esta funcao (chamada ``_soltar_processo_se_quit_travar``) encerrava o
    processo a forca quando o Quit demorava. Era ela que deixava o app morto por
    dentro - e o Android nao reabre em estado limpo um processo encerrado dessa
    forma: o Splash reusa a tarefa velha, e aparece tela preta ou o app nao
    abre. Nao existe mais nenhum caminho de codigo aqui que encerre o processo,
    nem que chame Kill/Shutdown/RestartApp. O pedido de saida sai pelo ``Quit``
    nativo, que e o caminho do proprio Kodi.

    A funcao continua existindo (com o nome novo) para o argumento antigo
    ``seguro_quit`` de uma versao anterior nao quebrar: ela apenas registra e
    nao toca no processo.
    """
    _log('saida: pedido antigo de ultimo recurso ignorado (o app nao encerra '
         'processo por conta propria)')
    # A marca de saida NAO e apagada aqui: ela e a informação que faz o proximo
    # boot ir direto para a Home (em vez de reabrir a tela do QR).
    return False


# nome antigo: mantido para testes/versões anteriores que chamem por ele
_soltar_processo_se_quit_travar = nao_encerrar_o_processo


def sair_do_aplicativo():
    """Encerra o SMARTEDTV/Kodi de forma limpa (menu Energia -> Sair).

    Fecha dialogos, para a reproducao, grava a marca de saida e pede o ``Quit``
    nativo do Kodi. Nao existe mais ultimo recurso que encerre o processo: era
    ele que impedia o app de abrir de novo depois de fechado. Nunca usa Kill,
    Shutdown ou RestartApp.
    """
    _log('saindo do aplicativo: fechando dialogos e liberando a reproducao')
    try:
        xbmc.executebuiltin('Dialog.Close(all,true)')
    except Exception:
        pass
    try:
        player = xbmc.Player()
        if player.isPlaying():
            player.stop()
    except Exception:
        pass
    for chave in (MARCA_VOLTAR, MARCA_ABERTA, MARCA_SAIU, MARCA_HOME):
        _limpar(chave)
    try:
        xbmc.sleep(250)       # deixa o Kodi processar o stop/close
    except Exception:
        pass
    # A marca e o que impede o guarda de uma sessao ANTIGA de agir: o boot novo
    # a encontra, cancela o alarme e segue normalmente.
    quando = int(time.time())
    _marcar_saida(quando)
    try:
        # Nenhum alarme de "ultimo recurso": ele disparava o vigia de boot num
        # processo que estava saindo e, junto com o antigo encerramento a forca,
        # era o que impedia o app de abrir de novo. Quem encerra e o Quit.
        _log('saindo do aplicativo: Quit() do Kodi (sem matar processo)')
        xbmc.executebuiltin('Quit')
        return True
    except Exception as erro:
        _log('falha ao encerrar pelo Quit: %s' % erro, xbmc.LOGERROR)
        return False


def reiniciar_aplicativo():
    """Menu Energia -> Reiniciar aplicativo: estado limpo e so entao restart.

    ``RestartApp`` sozinho reinicia o Kodi mantendo as marcas da tela de
    entrada e o alarme da saida: a sessao nova nascia com ``home=ok``/``saiu``
    presos e a Home aparecia preta. Aqui a limpeza vem antes.
    """
    _log('reiniciando o aplicativo: limpando marcas da sessao atual')
    for chave in (MARCA_VOLTAR, MARCA_ABERTA, MARCA_SAIU, MARCA_HOME):
        _limpar(chave)
    _limpar_guarda_de_saida()
    try:
        xbmc.executebuiltin('CancelAlarm(smartedtv_home_seguro,silent)')
    except Exception:
        pass
    try:
        xbmc.sleep(250)
    except Exception:
        pass
    try:
        _log('reiniciando o aplicativo: RestartApp')
        xbmc.executebuiltin('RestartApp')
        return True
    except Exception as erro:
        _log('falha ao reiniciar: %s' % erro, xbmc.LOGERROR)
        return False


def abrir_tela_entrada():
    """Abre a tela do pacote no lugar da Home. Devolve True quando abriu."""
    # Quem salva o boot se o Python travar antes de desenhar e o vigia
    # `seguro=1` do Startup.xml (8 s). Aqui limpamos qualquer trava do modo
    # `voltar` e abrimos a Home em todos os caminhos de falha.
    _limpar(MARCA_VOLTAR)
    # Sessao nova: o ultimo recurso da SAIDA anterior nao pode continuar
    # armado (era ele que encerrava o app logo depois de reabrir).
    _limpar_guarda_de_saida()
    # ABERTURA: a tela de ativacao aparece em todo boot, EXCETO quando este
    # aparelho ja concluiu a ativacao por codigo e a licenca continua valida
    # (`ativacao_concluida()`). Nesse caso a abertura cai direto na Home, como
    # qualquer app - antes o QR voltava em toda abertura e parecia que o app
    # "nao abria". Mesmo vindo de uma saida, sem ativacao a tela aparece.
    if ativacao_concluida():
        _log('abertura normal: ativacao concluida, indo direto para a Home')
        _limpar_marca_de_saida()
        _ir_para_home('abertura normal')
        return True
    # REENTRADA (saiu e abriu de novo ha instantes) sem ativacao concluida:
    # a tela de ativacao NAO pode ser reaberta por cima de uma sessao que
    # acabou de sair. Era este o caminho da "tela preta ao sair e entrar":
    # o `Quit` derruba o Kodi, o Android recria a Activity, o Startup.xml
    # dispara o script e a tela (doModal) subia enquanto o startup ainda estava
    # morrendo - quadro preto sem Home e sem tela. `_veio_de_uma_saida()`
    # responde isso pela marca `smarted-saindo` (escrita por
    # `sair_do_aplicativo` e apagada aqui, depois de usada). Indo para a Home,
    # o usuario continua de onde estava e VOLTAR na Home reabre a ativacao
    # quando ele quiser.
    if _veio_de_uma_saida():
        _log('abertura: reentrada apos SAIR (sem ativacao concluida); indo para '
             'a Home em vez de reabrir a tela de ativacao')
        _limpar_marca_de_saida()
        _ir_para_home('reentrada apos saida')
        return True
    pasta = _pasta_da_tela()
    if not pasta:
        _log('pasta da tela nao encontrada', xbmc.LOGERROR)
        _ir_para_home('tela de entrada indisponivel')
        return False
    try:
        janela = WelcomeDialog(_xml_da_tela(pasta), pasta, 'Default', '1080i')
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
    if any(a.startswith('seguro_quit') for a in argumentos):
        # Argumento de versao ANTIGA (alarme de ultimo recurso da saida). Fica
        # ANTES da checagem de 'seguro': 'seguro_quit' contem 'seguro' e, na
        # ordem antiga, isto abria o VIGIA DE BOOT num Kodi que estava saindo.
        nao_encerrar_o_processo()
    elif any('seguro' in a for a in argumentos):
        vigiar_inicializacao()
    elif any(ARG_REINICIAR in a for a in argumentos):
        reiniciar_aplicativo()
    elif any(ARG_SAIR in a for a in argumentos):
        sair_do_aplicativo()
    elif any(ARG_VOLTAR in a for a in argumentos):
        voltar_para_a_tela()
    else:
        abrir_tela_entrada()
