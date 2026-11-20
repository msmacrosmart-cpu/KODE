# -*- coding: utf-8 -*-
"""Retomada do conteudo depois do anuncio (sem alterar o APK nem o Kodi).

O Kodi do APK e um binario pronto: quando o anuncio abre, o proprio Kodi pausa
o player (``CXBMCApp::onPause``) e, ao voltar, so manda tocar de novo se foi ele
que pausou. Nada disso devolve ao Python um recibo de "anuncio exibido".

Por isso este modulo NAO chuta tempo de anuncio e NAO pausa duas vezes:

* antes de disparar, guarda identidade e posicao do item que esta tocando;
* **TV ao vivo nunca recebe seek**: um canal continuo nao tem ponto de
  retomada; buscar a posicao guardada reinicia o fluxo e deixa a tela preta
  (era o defeito "filme toca, canal fica preto"). No ao vivo o video volta
  so no ponto ATUAL da transmissao;
* depois do anuncio, quando o Kodi reinicia a reproducao (``onAVStarted`` do
  MESMO conteudo), devolve o video para a posicao guardada, se ela tiver se
  perdido (retomada do zero, por exemplo);
* a volta NAO pede outro pre-roll;
* se o conteudo mudou (troca de canal, outro filme, VIP, stop do usuario),
  nada e tocado.

Isto vale para celular, TV, box, projetor e stick: tudo roda no mesmo player do
Kodi, sem depender de tela sensivel ao toque.
"""
from __future__ import absolute_import, unicode_literals

import json
import threading
import time

import xbmc

TOLERANCIA = 1.0        # segundos de diferenca que ainda contam como "mesmo ponto"
ESPERA_MINIMA = 0.6     # o player pode ser recriado depois do anuncio
ESPERA_MAXIMA = 12.0    # tempo para a posicao ficar legivel
VIGIA_MAXIMO = 900.0    # desiste depois de 15 min (anuncio longo/erro)


def _rpc(method, **params):
    pedido = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})
    resposta = json.loads(xbmc.executeJSONRPC(pedido))
    if 'error' in resposta:
        raise RuntimeError('%s recusado' % method)
    return resposta['result']


def _video_id():
    for player in _rpc('Player.GetActivePlayers'):
        if player.get('type') == 'video':
            return player.get('playerid')
    return None


def _canal():
    for rotulo in ('VideoPlayer.ChannelName', 'Player.ChannelName'):
        try:
            valor = xbmc.getInfoLabel(rotulo) or ''
        except Exception:
            valor = ''
        if valor:
            return valor
    return ''


def _ao_vivo(caminho=''):
    """O conteudo guardado e um canal continuo (TV ao vivo)?"""
    try:
        import ao_vivo
        return bool(ao_vivo.eh_ao_vivo(caminho))
    except Exception:
        return False


def _url_base(caminho=''):
    """Normaliza URL de stream desencapsulando proxy temporario ``?url=...``."""
    texto = str(caminho or '').strip()
    if not texto:
        return ''
    try:
        import ao_vivo
        real = ao_vivo.extrair_url_proxy(texto)
        if real:
            texto = real
    except Exception:
        pass
    return texto.split('|', 1)[0].strip()


class Retomada(object):
    """Um ponto de retorno por anuncio; nunca mexe em conteudo que nao seja ele."""

    def __init__(self, log=None):
        self.log = log or (lambda *a, **k: None)
        self.lock = threading.RLock()
        self.pendente = None
        self.volta = None

    # ---------------------------------------------------------------- armacao
    def armar(self, player):
        """Guarda o que esta tocando. Devolve o estado ou ``None``."""
        try:
            pid = _video_id()
            if pid is None or not player.isPlayingVideo():
                return None
            caminho = player.getPlayingFile()
            try:
                posicao = float(player.getTime()) or 0.0
            except Exception:
                posicao = 0.0
            estado = {
                'playerid': pid,
                'caminho': caminho or '',
                'canal': _canal(),
                'posicao': posicao,
                'ao_vivo': _ao_vivo(caminho),
                'quando': time.monotonic(),
            }
            with self.lock:
                self.pendente = estado
            if self.log:
                self.log('[SmartAds] retomada armada em %.1fs de %r'
                         % (posicao, (caminho or '')[-60:]))
            return estado
        except Exception as erro:
            if self.log:
                self.log('[SmartAds] sem ponto de retomada (%s)'
                         % type(erro).__name__)
            return None

    def cancelar(self):
        with self.lock:
            self.pendente = None

    def guardado(self):
        with self.lock:
            return self.pendente

    # --------------------------------------------------------------- retorno
    def mesmo_conteudo(self, caminho=None, canal=None):
        with self.lock:
            estado = self.pendente
        if not estado:
            return False
        canal = _canal() if canal is None else canal
        if estado['canal'] and canal and estado['canal'] != canal:
            return False
        if caminho is None:
            try:
                caminho = xbmc.Player().getPlayingFile()
            except Exception:
                caminho = ''
        if estado['caminho'] and caminho:
            if _url_base(estado['caminho']) != _url_base(caminho):
                return False
        return True

    def consumir(self, player):
        """Marca a volta do anuncio e devolve o estado (uma vez só)."""
        with self.lock:
            estado, self.pendente = self.pendente, None
        if estado:
            self.volta = (estado['caminho'], estado['canal'], time.monotonic() + 20)
        return estado

    def e_volta(self, caminho=None, canal=None):
        """A reproducao que comecou agora e a volta do anuncio?"""
        with self.lock:
            volta = self.volta
            if not volta:
                return False
            if time.monotonic() > volta[2]:
                self.volta = None
                return False
            if volta[1] and canal and volta[1] != canal:
                return False
            if volta[0] and caminho and _url_base(volta[0]) != _url_base(caminho):
                return False
            self.volta = None
        return True

    # ------------------------------------------------------------- vigia
    def vigiar(self, player, estado):
        """Acompanha o player ate ele voltar; corrige o ponto se ele se perdeu.

        Nao depende de evento de ciclo de vida: vale igual para celular, TV,
        box, projetor e stick. Para quando o conteudo muda, quando o usuario
        para ou quando o video ja voltou sozinho no ponto certo.
        """
        inicio = time.monotonic()
        limite = inicio + VIGIA_MAXIMO
        pausado_visto = False
        while time.monotonic() < limite:
            time.sleep(0.5)
            with self.lock:
                if self.pendente is not estado:
                    return None
            try:
                if not player.isPlayingVideo():
                    # No canal ao vivo, o fluxo pode cair enquanto a tela do
                    # anuncio esteve aberta (mesmo antes do poll ver Paused).
                    # Marca a volta ANTES de reabrir o canal para que o retorno
                    # ao canal inicie o intervalo de 2 min sem novo anuncio.
                    if (estado.get('ao_vivo')
                            and (pausado_visto or time.monotonic() - inicio >= 1.0)):
                        if self.mesmo_conteudo('', _canal()):
                            self.consumir(player)
                            try:
                                import ao_vivo
                                if ao_vivo._tocar_de_novo(estado['caminho']):
                                    if self.log:
                                        self.log('[SmartAds] canal reaberto apos '
                                                 'o anuncio (ao vivo)')
                            except Exception:
                                pass
                        else:
                            self.cancelar()
                        return None
                    if pausado_visto:
                        self.cancelar()
                        return None
                    continue
                caminho = player.getPlayingFile()
                canal = _canal()
                if not self.mesmo_conteudo(caminho, canal):
                    self.cancelar()
                    return None
                try:
                    pausado = bool(xbmc.getCondVisibility('Player.Paused'))
                except Exception:
                    pausado = False
                atual = float(player.getTime()) or 0.0
            except Exception:
                continue
            if pausado and atual <= estado['posicao'] + TOLERANCIA:
                pausado_visto = True
                continue
            # Player livre de novo: ou continuou no ponto, ou perdeu o ponto.
            return self.corrigir(player, estado)
        self.cancelar()
        return None

    # -------------------------------------------------------------- correcao
    def corrigir(self, player, estado):
        """Devolve o player a posicao guardada, se ele perdeu o ponto."""
        if estado.get('ao_vivo'):
            # Canal continuo: seek aqui derruba o fluxo (tela preta). O canal
            # volta no ponto atual da transmissao e inicia o intervalo de 2 min.
            self.consumir(player)
            try:
                import ads_regra
                ads_regra.concluir_anuncio()
            except Exception:
                pass
            if self.log:
                self.log('[SmartAds] TV ao vivo: sem retomada por posicao')
            return None
        alvo = estado['posicao']
        if alvo <= 0:
            return None
        limite = time.monotonic() + ESPERA_MAXIMA
        inicio = time.monotonic()
        while time.monotonic() < limite:
            if not player.isPlayingVideo():
                return None
            try:
                atual = float(player.getTime()) or 0.0
            except Exception:
                atual = 0.0
            # Posicao 0 pode ser "ainda carregando" ou "reiniciou": so espera
            # alguns segundos por um valor legivel antes de decidir.
            if atual <= 0 and time.monotonic() - inicio < 3.0:
                time.sleep(0.25)
                continue
            if abs(atual - alvo) <= TOLERANCIA:
                return None
            if abs(atual - alvo) <= 3 and atual > alvo:
                return None  # alguns segundos a frente e o proprio buffer
            pausado = False
            try:
                pausado = bool(xbmc.getCondVisibility('Player.Paused'))
            except Exception:
                pass
            try:
                _rpc('Player.Seek', playerid=_video_id(), value={'seconds': alvo})
            except Exception as erro:
                try:
                    player.seekTime(alvo)
                except Exception:
                    if self.log:
                        self.log('[SmartAds] nao foi possivel voltar a %.1fs (%s)'
                                 % (alvo, type(erro).__name__))
                    return None
            if pausado:
                try:
                    _rpc('Player.PlayPause', playerid=_video_id(), play=True)
                except Exception:
                    pass
            if self.log:
                self.log('[SmartAds] retomado em %.1fs (estava em %.1fs)'
                         % (alvo, atual))
            return alvo
        return None
