# -*- coding: utf-8 -*-
"""Anuncios do AdMob disparados pelo Kodi (ponte nativa StartAndroidActivity).

O Kodi do APK e um binario pronto: o SDK do AdMob nao pode ser injetado nele sem
recompilar o Kodi inteiro. Por isso o anuncio e exibido pelas activities que ja
vivem no MESMO APK (pacote ``smartedtv.full``), e o Kodi as abre por um builtin
nativo:

    StartAndroidActivity(smartedtv.full,smartedtv.ads.PREROLL,,,,,,,smartedtv.full.PreRollActivity)

ATENCAO a ordem dos parametros do builtin (Kodi v20+):

    StartAndroidActivity(package, intent, dataType, dataURI, flags, extras,
                         action, category, className)

O className e o NONO parametro, nao o segundo. Passar a classe em segundo lugar
faz o Kodi montar um intent com action = nome da classe e sem componente — o
Android nao acha ninguem e a tela de anuncio nunca abre (foi exatamente o bug
que deixou os anuncios "sem preencher": na verdade nem eram pedidos).

SEGUNDO BLOQUEIO (1.0.63): o parametro "intent" (posicao 2) NAO pode ser vazio.
No codigo do Kodi (CXBMCApp::StartActivity):

    newIntent = intent.empty() ? getLaunchIntentForPackage(package) : Intent(intent);
    if (!newIntent) return false;              // sai aqui, antes do className
    ...
    if (!className.empty()) newIntent.setClassName(package, className);

Com intent vazio o Kodi procura a activity de LAUNCHER do pacote; o app de
anuncios nao tem launcher, entao getLaunchIntentForPackage devolve null e o
builtin retorna false sem nunca olhar o className. Por isso vai sempre uma
action nossa na posicao 2 (e o app tambem ganhou um launcher como plano B).

Dois gatilhos:

1. ABERTURA — uma unica vez, poucos segundos depois de a Home carregar
   (bloco ca-app-pub-2066014755407744/4214378379);
2. PRE-ROLL — sempre que um canal, filme ou serie comeca a tocar
   (bloco ca-app-pub-2066014755407744/3572039686). A tela do anuncio cobre o
   player enquanto o buffer acontece atras.

Nada aqui pode quebrar a reproducao: se o app de anuncios nao estiver
instalado, se o Kodi nao for Android ou se o builtin falhar, o video segue
normalmente.
"""
from __future__ import absolute_import, unicode_literals

import os
import time

import xbmc
import xbmcvfs

# PACKAGE = applicationId do app de anuncios (android/smarted-ads/app-id.txt).
# Precisa ser um pacote proprio: org.xbmc.kodi e o pacote do Kodi e o Android
# nao aceita dois apps com o mesmo nome — um sobrescreveria o outro.
# As classes ficam no MESMO pacote do app (smartedtv.full): o className
# explicito aponta para a activity que ja existe no DEX do APK.
PACKAGE = 'smartedtv.full'
ATIVIDADE_ABERTURA = 'smartedtv.full.AppOpenActivity'
ATIVIDADE_PREROLL = 'smartedtv.full.PreRollActivity'

# action propria de cada tela: vai na posicao 2 do StartAndroidActivity (o
# "intent" nao pode ser vazio, senao o Kodi procura o launcher do pacote e
# desiste). Tambem serve de intent-filter no manifesto do app de anuncios.
ACAO_ABERTURA = 'smartedtv.ads.APPOPEN'
ACAO_PREROLL = 'smartedtv.ads.PREROLL'

# marcas para o relatorio do boot
MARKER = 'smartedtv-ads-v2'

# quanto esperar a Home desenhar antes do pop-up de abertura
ABERTURA_DELAY = 6

# O intersticial e OBRIGATORIO em toda troca de conteudo (1.0.73): nao existe
# mais intervalo minimo entre anuncios. O que fica e so uma janela curta
# anti-duplicidade: o Kodi chama onPlay e onAVStarted para o MESMO inicio de
# stream, e sem essa janela o mesmo filme levaria dois anuncios seguidos.
PREROLL_INTERVALO = 10


def intervalo_configurado(padrao=PREROLL_INTERVALO):
    """Janela anti-duplicidade (segundos) — configurável em ads_intervalo."""
    try:
        import xbmcaddon
        bruto = xbmcaddon.Addon().getSetting('ads_intervalo')
        valor = int(float(bruto))
        return valor if 6 <= valor <= 15 else padrao
    except Exception:
        return padrao


def _marker_path():
    try:
        perfil = xbmcvfs.translatePath('special://profile')
    except Exception:
        return None
    return os.path.join(perfil, 'addon_data', 'service.smarted.bootstrap',
                        'ads-abertura.txt')


def abertura_ja_mostrada():
    """So vale marca escrita por ESTA versao da ponte.

    As versoes 1.0.60/1.0.61 gravavam a marca mesmo sem a tela abrir (o builtin
    estava errado); sem a checagem de versao o pop-up nunca mais apareceria.
    """
    caminho = _marker_path()
    if not caminho:
        return False
    try:
        # os.path (e nao xbmcvfs): o caminho ja vem traduzido e o arquivo e
        # escrito por nos mesmos
        if not os.path.exists(caminho):
            return False
        with open(caminho) as arquivo:
            return MARKER in arquivo.read()
    except Exception:
        return False


def marcar_abertura(quando=None):
    caminho = _marker_path()
    if not caminho:
        return False
    try:
        pasta = os.path.dirname(caminho)
        if pasta and not os.path.isdir(pasta):
            os.makedirs(pasta)
        with open(caminho, 'w') as arquivo:
            arquivo.write('%s abertura disparada em %s\n'
                          % (MARKER, time.strftime('%Y-%m-%d %H:%M:%S',
                                                   time.localtime(quando))))
        return True
    except Exception:
        return False


def android():
    """So tenta a ponte nativa quando o Kodi esta rodando no Android."""
    try:
        return bool(xbmc.getCondVisibility('System.Platform.Android'))
    except Exception:
        return False


def builtin_para(atividade, package=None, acao=None, uri=''):
    """Builtin com os 9 parametros na ordem do Kodi.

    (package, intent, dataType, dataURI, flags, extras, action, category,
     className)

    - ``intent`` (posicao 2) NAO pode ser vazio: com ele vazio o Kodi usa o
      launcher do pacote e desiste quando o app nao tem um.
    - ``className`` (posicao 9) e o que torna a abertura explicita, sem depender
      da visibilidade de pacotes do Android 11+.
    """
    if acao is None:
        acao = ACAO_PREROLL if atividade == ATIVIDADE_PREROLL else ACAO_ABERTURA
    campos = [package or PACKAGE, acao, '', uri, '', '', '', '', atividade]
    return 'StartAndroidActivity(%s)' % ','.join(campos)


def tocar_anuncio(atividade, log=None, uri=''):
    """Abre a tela de anuncio do app SMARTEDTV Ads.

    Tenta o componente explicito (className) e, se o app tiver launcher, o data
    URI como plano B. Devolve True se ao menos um disparo foi enviado.
    """
    if not android():
        if log:
            log('[SmartAds] ignorado (nao e Android)')
        return False
    builtin = builtin_para(atividade, uri=uri)
    try:
        xbmc.executebuiltin(builtin)
    except Exception as erro:
        if log:
            log('[SmartAds] %s falhou (%s)' % (builtin, erro), xbmc.LOGWARNING)
        return False
    if log:
        # este e o log que aparece no kodi.log quando o disparo acontece
        log('[SmartAds] disparando %s -> %s/%s'
            % (builtin, PACKAGE, atividade))
    # Sem plano B: a classe do anuncio vive no MESMO pacote (smartedtv.full),
    # entao o componente explicito e suficiente. O antigo plano B apontava para
    # uma LauncherActivity que nao existe neste APK.
    return True


def _kodi_em_foco(limite=2.5, passo=0.1):
    """Espera o Kodi recuperar o foco da janela (volta do anuncio/browser)."""
    fim = time.time() + limite
    while time.time() < fim:
        try:
            if xbmc.getCondVisibility('System.HasFocus | Window.IsActive(10000)'):
                return True
        except Exception:
            return True
        time.sleep(passo)
    return False


def abrir_anuncio(atividade, log=None, uri=''):
    """Dispara a tela e espera o Kodi voltar a frente antes de liberar o video."""
    disparou = tocar_anuncio(atividade, log, uri)
    if disparou:
        _kodi_em_foco()
    return disparou


def tocar_anuncio_com_aviso(atividade, log=None):
    """Igual a tocar_anuncio, mas avisa na tela do Kodi (fica no log e na TV).

    A notificacao so aparece quando o builtin realmente foi enviado. Antes ela
    aparecia tambem quando o Android recusava o componente e o usuario via
    "Abrindo anuncio" sem anuncio nenhum (tela vazia) no projetor.
    """
    disparou = abrir_anuncio(atividade, log)
    if log:
        log('[SmartAds] aviso na tela: %s (%s)'
            % ('enviado' if disparou else 'nao enviado', atividade))
    if disparou:
        try:
            xbmc.executebuiltin(
                'Notification(SMARTEDTV Anuncios, Abrindo anuncio (%s), 2500)'
                % ('video' if atividade == ATIVIDADE_PREROLL else 'abertura'))
        except Exception:
            pass
    return disparou


def vip_ativo():
    """Licença VIP desliga todos os gatilhos (a checagem também existe no Java)."""
    try:
        import vip
        return bool(vip.ativa())
    except Exception:
        return False


def _chave_conteudo(caminho=None):
    """Chave do conteudo: caminho + canal/titulo quando existirem.

    Live TV pode repetir o mesmo caminho em canais diferentes; o nome do canal
    entra na chave para que a troca de canal realmente conte como novo conteudo.
    """
    partes = []
    if caminho:
        partes.append(str(caminho))
    for rotulo in ('VideoPlayer.ChannelName', 'VideoPlayer.Title',
                   'VideoPlayer.OriginalTitle', 'Player.Title'):
        try:
            valor = xbmc.getInfoLabel(rotulo) or ''
        except Exception:
            valor = ''
        if valor and valor not in partes:
            partes.append(valor)
            break
    return '|'.join(partes) if partes else '?'


def esquecer():
    """Zera a memoria do ultimo conteudo (parar/terminar libera o proximo)."""
    globals()['_ultimo_momento'] = 0.0
    globals()['_ultimo_caminho_preroll'] = None
    globals()['_ultimo_caminho_base'] = None
    globals()['_ultima_sessao'] = None


def mostrar_preroll(log=None, intervalo=None, agora=None, caminho=None,
                    chave=None, sessao=None, disparar=None, forcar=False):
    """Intersticial em TODA troca de conteudo (exceto VIP).

    ``intervalo`` e so a janela anti-duplicidade do MESMO inicio: o Kodi avisa
    ``onPlayBackStarted`` e ``onAVStarted`` para o mesmo stream (as vezes com
    segundos de buffer entre os dois). Troca de canal, filme, episodio ou serie
    tem chave diferente e dispara na hora, mesmo dentro da janela.
    """
    if intervalo is None:
        intervalo = intervalo_configurado()
    agora = time.time() if agora is None else agora
    if vip_ativo():
        if log:
            log('[SmartAds] VIP ativo: nenhum anuncio')
        return False
    chave = chave or _chave_conteudo(caminho)
    # Sessao de reproducao: o Kodi chama onPlayBackStarted E onAVStarted para
    # o mesmo inicio. Sem caminho/canal (alguns projetores/PVR nao entregam
    # metadados) a chave era '?' e o anuncio NUNCA era pedido. A sessao resolve
    # o mesmo inicio sem depender dos metadados.
    if forcar:
        # Botao "Testar anuncio" dos Ajustes: mesmo caminho do player, sem
        # inventar exibicao (o retorno do Java ainda e o unico recibo).
        sessao = None
        chave = 'teste:%d' % agora
    elif sessao is not None:
        if sessao == globals().get('_ultima_sessao'):
            if log:
                log('[SmartAds] mesmo inicio de reproducao (sessao %s), sem anuncio'
                    % sessao)
            return False
    elif chave == globals().get('_ultimo_caminho_preroll') and agora - globals().get('_ultimo_momento', 0) < intervalo:
        return False
    disparou = (disparar or tocar_anuncio_com_aviso)(ATIVIDADE_PREROLL, log)
    if disparou:
        globals()['_ultimo_momento'] = agora
        globals()['_ultimo_caminho_preroll'] = chave
        globals()['_ultima_sessao'] = sessao
    if log:
        log('[SmartAds] pré-roll: %s (sessão %s)' % ('pedido' if disparou else 'indisponível', sessao))
    return disparou


def testar_anuncio(log=None):
    """Pede UM pré-roll pelo mesmo builtin, para conferir no aparelho/log."""
    if vip_ativo():
        if log:
            log('[SmartAds] teste ignorado: VIP ativo')
        return False
    # forcar=True ignora a janela anti-duplicidade, mas usa o MESMO caminho do
    # player (ponte + retorno). Sem player tocando, so o disparo é testado.
    return bool(mostrar_preroll(log, sessao=None, forcar=True))


def mostrar_abertura(log=None):
    """Pop-up de abertura: exatamente uma vez por instalacao."""
    if vip_ativo():
        if log:
            log('[SmartAds] VIP ativo: sem pop-up de abertura')
        return False
    if abertura_ja_mostrada():
        if log:
            log('[SmartAds] abertura ja exibida nesta instalacao')
        return False
    if not tocar_anuncio_com_aviso(ATIVIDADE_ABERTURA, log):
        return False
    marcar_abertura()
    if log:
        log('[SmartAds] pop-up de abertura disparado (uma vez por instalacao)')
    return True


def abertura_depois_do_boot(monitor, log=None, espera_home=90):
    """Espera a Home aparecer e mostra o pop-up (roda em thread propria).

    Nao abre o app-open por cima da tela de entrada: primeiro espera a Home
    ficar ativa. Se o usuario demorar mais que ``espera_home`` ou ja estiver
    reproduzindo video, este inicio pula o pop-up (a proxima abertura tenta).
    """
    try:
        if monitor.waitForAbort(ABERTURA_DELAY):
            return False
    except Exception:
        time.sleep(ABERTURA_DELAY)
    limite = time.time() + max(6, int(espera_home))
    while time.time() < limite:
        try:
            if monitor.abortRequested():
                return False
        except Exception:
            pass
        try:
            if xbmc.Player().isPlayingVideo():
                if log:
                    log('[SmartAds] abertura adiada (video ja em reproducao)')
                return False
        except Exception:
            pass
        try:
            if xbmc.getCondVisibility('Window.IsActive(Home)'):
                break
        except Exception:
            break
        try:
            if monitor.waitForAbort(1):
                return False
        except Exception:
            time.sleep(1)
    else:
        if log:
            log('[SmartAds] abertura nao exibida: Home nao ficou ativa em %d s'
                % espera_home)
        return False
    return mostrar_abertura(log)


def _e_video(player):
    try:
        return bool(player.isPlayingVideo())
    except Exception:
        return False


# Dentro do Kodi isto e xbmc.Player; fora dele (testes, PC sem Kodi) vira
# object, para o modulo poder ser importado em qualquer lugar.
_BasePlayer = getattr(xbmc, 'Player', object)


class MonitorPreRoll(_BasePlayer):
    """Escuta o inicio de QUALQUER stream e chama o pre-roll.

    Vale para canal de TV, filme e serie, venha do Brazuca ou de outro addon:
    o gancho e o proprio xbmc.Player, nao a rota do addon.

    Regra: TODO inicio de reproducao conta como troca de conteudo e pede
    anuncio — canal->canal, filme->filme, serie->filme e voltar para o MESMO
    conteudo depois de parar. O unico filtro e o par
    ``onPlayBackStarted``/``onAVStarted`` do mesmo inicio (janela curta).
    """

    def __init__(self, log=None, intervalo=None):
        if _BasePlayer is not object:
            _BasePlayer.__init__(self)
        self.log = log
        self.intervalo = intervalo
        self.ultimo_caminho = None
        self.sessao = 0
        self.retomada = None

    def _retomada(self):
        if self.retomada is None:
            try:
                from ad_return import Retomada
                self.retomada = Retomada(self.log)
            except Exception:
                self.retomada = False
        return self.retomada

    def _disparar(self, atividade, log):
        # Guarda o ponto ANTES de a tela do anuncio pausar o player. Sem isso,
        # a volta do anuncio recomecaria o filme do zero em qualquer aparelho.
        retomada = self._retomada()
        if retomada:
            try:
                retomada.armar(self)
            except Exception as erro:
                if log:
                    log('[SmartAds] ponto de retomada falhou (%s)'
                        % type(erro).__name__)
        disparou = abrir_anuncio(atividade, log)
        if not disparou:
            if retomada:
                retomada.cancelar()
            return False
        if retomada:
            estado = retomada.guardado()
            if estado:
                threading.Thread(target=retomada.vigiar, args=(self, estado),
                                 name='volta-anuncio', daemon=True).start()
        return True

    def _caminho(self):
        try:
            caminho = xbmc.Player().getPlayingFile()
        except Exception:
            caminho = None
        if not caminho:
            # alguns streams (principalmente PVR) so aparecem no info label
            for rotulo in ('Player.FilenameAndPath', 'Player.Url'):
                try:
                    caminho = xbmc.getInfoLabel(rotulo) or ''
                except Exception:
                    caminho = ''
                if caminho:
                    break
        return caminho or None

    def _talvez_mostrar(self):
        try:
            if not _e_video(self):
                return
            caminho = self._caminho() or self.ultimo_caminho
            retomada = self._retomada()
            canal = xbmc.getInfoLabel('VideoPlayer.ChannelName') or ''
            if retomada and retomada.e_volta(caminho, canal):
                # A reproducao que acabou de comecar e a volta do anuncio: nao
                # gera outro pre-roll e devolve o video ao ponto guardado.
                globals()['_ultima_sessao'] = self.sessao
                if self.log:
                    self.log('[SmartAds] volta do anuncio: sem novo pre-roll')
                return
            chave = _chave_conteudo(caminho)
            self.ultimo_caminho = caminho
            mostrar_preroll(self.log, self.intervalo, caminho=caminho,
                            chave=chave, sessao=self.sessao, disparar=self._disparar)
        except Exception as erro:  # nunca derrubar o servico por causa do anuncio
            if self.log:
                self.log('[SmartAds] pre-roll falhou (%s)' % erro, xbmc.LOGWARNING)

    # Kodi 21 chama onPlayBackStarted; onAVStarted vem em seguida para o mesmo
    # stream. Os dois passam pela mesma janela anti-duplicidade.
    def onPlayBackStarted(self):
        self.sessao += 1
        # Wait for AVStarted: the addon may still be resolving/resuming the item.


    def onAVStarted(self):
        # Mesma sessao de onPlayBackStarted: nao pede o segundo anuncio.
        # Tambem e aqui que a volta do anuncio e reconhecida (Kodi retoma o
        # player) e o ponto guardado e restaurado.
        self._talvez_mostrar()

    # Compatibilidade com versoes que ainda chamam onPlay.
    def onPlay(self, **kwargs):
        self._talvez_mostrar()

    def onPlayBackStopped(self):
        self._limpar_retomada()
        self.ultimo_caminho = None
        self.sessao += 1
        esquecer()

    def onPlayBackEnded(self):
        self._limpar_retomada()

    def _limpar_retomada(self):
        # Stop/troca de conteudo: nada de ressuscitar player nem posicao.
        retomada = self._retomada()
        if retomada:
            retomada.cancelar()
        self.ultimo_caminho = None
        self.sessao += 1
        esquecer()


_monitor = None


def iniciar_monitor(log=None, intervalo=None):
    """Liga o gancho de reproducao uma vez por sessao."""
    global _monitor
    if _monitor is not None or not android():
        return _monitor
    if intervalo is None:
        intervalo = intervalo_configurado()
    try:
        _monitor = MonitorPreRoll(log, intervalo)
        if log:
            log('[SmartAds] gancho de intersticial ligado (%s, obrigatorio em toda '
                'troca; anti-duplicidade %d s)' % (MARKER, intervalo))
    except Exception as erro:
        if log:
            log('[SmartAds] nao foi possivel ligar o pre-roll (%s)' % erro, xbmc.LOGWARNING)
        _monitor = None
    return _monitor


def monitor():
    return _monitor
