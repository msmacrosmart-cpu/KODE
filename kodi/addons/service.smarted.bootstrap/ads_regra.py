# -*- coding: utf-8 -*-
"""Regra central de frequencia dos anuncios (um unico lugar decide).

Pedido do usuario, item por item:

* anuncio SO na troca de conteudo (canal, filme, episodio). O mesmo conteudo
  que continua tocando - ou que volta depois do anuncio - nao pede outro;
* UM anuncio por conteudo por sessao de reproducao. Mesmo que o intervalo
  tenha terminado, enquanto o usuario continuar naquele conteudo nao aparece
  outro anuncio. Reiniciar, pausar, retomar, reconectar ou recarregar o mesmo
  conteudo NAO e troca de conteudo;
* depois de um anuncio efetivamente exibido (concluido ou pulado), 2 minutos
  sem anuncio: dentro deles qualquer conteudo novo abre direto;
* passados os 2 minutos, so a proxima troca REAL de conteudo pode receber
  anuncio;
* anuncio que falha/nao existe/nao carrega NAO bloqueia a reproducao nem faz
  tentativa repetida: uma tentativa por troca, e o conteudo segue na hora;
* VIP nunca recebe anuncio, em nenhum estado;
* uma unica porta de entrada para todos os gatilhos (sem anuncio duplicado
  por eventos diferentes do mesmo inicio de reproducao).

Tres estados SEPARADOS - nunca um unico temporizador:

``conteudo``
    A identidade do conteudo da sessao atual de reproducao. Serve para
    responder "mudou de conteudo?" (troca real) e "este conteudo ja recebeu
    o anuncio dele nesta sessao?".
``ultimo_anuncio``
    Quando o ultimo anuncio EXIBIDO terminou. Serve para o intervalo de 2
    minutos.
``em_exibicao`` / ``piso``
    Controle de um disparo em andamento, para desfazer o piso caso o anuncio
    nao tenha aberto e para nao contar sinal de volta atrasado.

Cada troca real tem um "bilhete" (``abrir_troca``) que dura ate o conteudo
terminar; dentro do bilhete so cabe UMA tentativa de anuncio
(``pode_anunciar`` devolve False depois da primeira). Recarregar/reconectar o
mesmo conteudo reaproveita o bilhete, entao nao gera anuncio novo.

Estado em DISCO: o Android mata o processo em TV box/stick com pouca RAM e o
app reabre em segundos. So em memoria, o intervalo de 2 minutos (e o "um por
conteudo") seria esquecido e o anuncio voltaria na primeira troca.

Este modulo NAO abre tela de anuncio: so responde "pode?" e recebe "mostrou".
"""
from __future__ import absolute_import, unicode_literals

import json
import os
import time

import xbmc
import xbmcvfs

# Intervalo minimo entre anuncios exibidos: 2 minutos (pedido do usuario).
INTERVALO = 120

# Quanto tempo um anuncio pode ficar "em exibicao". Passado isso, o sinal de
# volta nao veio (SDK travou/tela fechou sozinha) e o intervalo fica contado a
# partir do disparo - nunca a partir de "agora", senao um sinal atrasado
# empurraria o proximo anuncio para depois do tempo.
EXIBICAO_MAXIMA = 300

ARQUIVO = 'ads-regra.json'

# Quantos conteudos ja anunciados ficam lembrados. 60 canais/filmes cobrem uma
# sessao inteira de uso normal sem o arquivo crescer sem limite.
ANUNCIADOS_MAXIMO = 60

# Reserva em memoria: usada quando o profile nao resolve para um caminho real
# (harness/testes e o caso raro de o Kodi ainda nao ter profile no boot). O
# app real sempre escreve em disco.
_MEMORIA = {}


def _caminho():
    """Arquivo de estado dentro do profile (sobrevive a reinicio do servico)."""
    try:
        perfil = xbmcvfs.translatePath('special://profile')
    except Exception:
        return None
    # Caminho nao traduzido (harness/teste) nao vira pasta no diretorio atual.
    if not perfil or not os.path.isabs(perfil):
        return None
    return os.path.join(perfil, 'addon_data', 'service.smarted.bootstrap',
                        ARQUIVO)


def _ler():
    caminho = _caminho()
    if not caminho:
        return dict(_MEMORIA)
    try:
        with open(caminho) as arquivo:
            dados = json.load(arquivo)
        return dados if isinstance(dados, dict) else {}
    except Exception:
        # arquivo ausente/corrompido: comeca do zero (nunca levanta)
        return {}


def _gravar(dados):
    caminho = _caminho()
    if not caminho:
        _MEMORIA.clear()
        _MEMORIA.update(dados)
        return True
    pasta = os.path.dirname(caminho)
    try:
        if pasta and not os.path.isdir(pasta):
            os.makedirs(pasta)
        temporario = caminho + '.tmp'
        with open(temporario, 'w') as arquivo:
            json.dump(dados, arquivo)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
        return True
    except Exception:
        return False


def chave_do_conteudo(caminho=None, canal=None, titulo=''):
    """Identidade do conteudo que esta tocando.

    Troca de canal no mesmo stream, filme -> filme e episodio -> episodio
    precisam dar chaves diferentes; o mesmo conteudo retomado depois do
    anuncio precisa dar a MESMA chave (para nao pedir outro anuncio).
    """
    partes = []
    for valor in (caminho, canal, titulo):
        texto = (valor or '')
        if texto and texto not in partes:
            partes.append(texto)
    return '|'.join(partes) or '?'


def _sem_metadados(chave):
    """Conteudo sem identidade (projetor/PVR que nao informa caminho/canal)."""
    return not chave or chave == '?'


def ultimo_anuncio(agora=None):
    """Instante (epoch) do ultimo anuncio EFETIVAMENTE exibido, ou 0."""
    dados = _ler()
    try:
        quando = float(dados.get('ultimo_anuncio') or 0)
    except Exception:
        quando = 0.0
    agora = time.time() if agora is None else agora
    # Relogio para tras (ajuste de hora/NTP no aparelho) nao pode prender o
    # anuncio para sempre: um instante no futuro e lixo, nao "acabou de
    # mostrar". Tratar como lixo libera o anuncio na hora; tratar como "agora"
    # deixaria o intervalo renovado a cada consulta, ou seja, sem anuncio nunca.
    if quando > agora + 60:
        return 0.0
    return quando


def decorrido(agora=None):
    """Segundos desde o ultimo anuncio exibido (None se nunca houve)."""
    quando = ultimo_anuncio(agora)
    if not quando:
        return None
    agora = time.time() if agora is None else agora
    return max(0.0, agora - quando)


def conteudo_atual():
    """Chave do conteudo da sessao atual de reproducao (None se nao houver)."""
    return _ler().get('conteudo') or None


def anunciado_no_conteudo():
    """O conteudo da sessao atual ja recebeu o anuncio dele?"""
    return bool(_ler().get('anunciado'))


def ja_anunciado(chave):
    """Este conteudo JA recebeu o anuncio dele na sessao ATUAL em reproducao?

    Enquanto o usuario continua assistindo o mesmo conteudo (pausa, retomada,
    retorno do anuncio ou reconexao), devolve True para que possa assistir ate
    o final sem novo anuncio. Ao sair do conteudo (Stop/Voltar) ou trocar para
    outro conteudo, libera novamente respeitando o intervalo de 2 minutos.
    """
    if _sem_metadados(chave):
        return False
    dados = _ler()
    return bool(dados.get('anunciado')) and (dados.get('conteudo') or '') == chave


def marcar_anunciado(chave, dados=None):
    """Marca que o conteudo atual recebeu anuncio (limpando lista legada)."""
    if not chave or _sem_metadados(chave):
        return False
    dados = _ler() if dados is None else dados
    dados.pop('anunciados', None)
    dados['conteudo'] = chave
    dados['anunciado'] = True
    return True


def tentativa_feita(chave=None):
    """Este conteudo ja consumiu a UNICA tentativa de anuncio da troca?

    Vale mesmo quando o anuncio falhou: uma troca de conteudo dispara no maximo
    UMA tentativa, nunca um laco de tentativas repetidas.
    """
    if _sem_metadados(chave):
        return False      # sem identidade quem controla e a sessao do player
    dados = _ler()
    marca = dados.get('tentativa')
    if not marca:
        return False
    return marca == chave == (dados.get('conteudo') or '')


def marcar_conteudo(chave):
    """Registra o conteudo atual (sem consumir o intervalo).

    Usado quando o anuncio NAO pode ser exibido: o conteudo continua sendo o
    mesmo da sessao, para que pausar/retomar nao pareca troca.
    """
    if not chave:
        return False
    dados = _ler()
    if dados.get('conteudo') == chave and 'conteudo' in dados:
        return True
    dados['conteudo'] = chave
    dados.pop('anunciado', None)   # conteudo novo: bilhete novo
    dados.pop('tentativa', None)   # e a tentativa da troca anterior nao conta
    dados.pop('anunciados', None)
    return _gravar(dados)


def abrir_troca(chave):
    """Abre o bilhete de UMA tentativa para este conteudo.

    Devolve True quando o conteudo MUDOU (troca real) e False quando e o
    mesmo conteudo da sessao (retomada, recarga, reconexao, pausa/volta):
    nesse caso nada e reiniciado e o anuncio ja dado continua dado.
    """
    if not chave:
        return False
    dados = _ler()
    if dados.get('conteudo') == chave and 'conteudo' in dados:
        return False
    dados['conteudo'] = chave
    dados.pop('anunciado', None)
    dados.pop('tentativa', None)
    dados.pop('anunciados', None)
    return _gravar(dados)


def pode_anunciar(chave=None, agora=None):
    """(pode, motivo). Nunca bloqueia: e uma consulta pura.

    Tres perguntas, nesta ordem - nunca um temporizador sozinho:

    1. este conteudo ja recebeu o anuncio dele nesta sessao?  -> nao
    2. o intervalo de 2 minutos desde o ultimo anuncio exibido acabou?  -> nao
    3. e uma troca real de conteudo?  -> sim
    """
    agora = time.time() if agora is None else agora
    dados = _ler()
    atual = dados.get('conteudo')
    anunciado = bool(dados.get('anunciado'))

    # Conteudo SEM identidade (projetor/PVR que nao informa caminho nem canal):
    # nao da para dizer "e o mesmo conteudo". Quem separa os inicios e a sessao
    # do player (anti-duplicidade) e o intervalo de 2 minutos.
    if _sem_metadados(chave):
        quando = ultimo_anuncio(agora)
        if quando and (agora - quando) < INTERVALO:
            restante = INTERVALO - (agora - quando)
            return False, ('intervalo de %d s: faltam %d s para o proximo '
                           'anuncio' % (INTERVALO, int(restante + 0.5)))
        return True, 'troca de conteudo liberada (sem metadados)'

    # (0) esta troca ja gastou a tentativa dela, mesmo tendo falhado:
    #     UMA tentativa por troca de conteudo (nada de tentativa repetida).
    if tentativa_feita(chave):
        return False, 'esta troca de conteudo ja tentou o anuncio (sem repetir)'

    # (1) um anuncio por conteudo por sessao de reproducao. Mesmo depois dos
    #     2 minutos, e mesmo que o usuario pare e reabra o mesmo conteudo.
    if ja_anunciado(chave):
        return False, 'este conteudo ja recebeu o anuncio desta sessao'
    if anunciado and atual and chave == atual:
        return False, 'mesmo conteudo do ultimo anuncio (sem troca)'

    # (2) intervalo de 2 minutos desde o anuncio exibido
    quando = ultimo_anuncio(agora)
    if quando and (agora - quando) < INTERVALO:
        restante = INTERVALO - (agora - quando)
        return False, ('intervalo de %d s: faltam %d s para o proximo anuncio'
                       % (INTERVALO, int(restante + 0.5)))

    # (3) troca real de conteudo. Ja tratada por quem chama, que abre o bilhete
    # de UMA tentativa para o conteudo atual ANTES de perguntar; aqui a mesma
    # chave e o mesmo conteudo, nao "sem troca".
    return True, 'troca de conteudo liberada'


def registrar_anuncio(chave=None, quando=None):
    """Anuncio ENVIADO para a tela: ja vale como exibido (piso conservador).

    O intervalo comeca a contar aqui por seguranca; quando o sinal de volta do
    anuncio chega, ``concluir_anuncio`` reinicia a contagem naquele instante -
    que e o "depois de concluido ou pulado" pedido.
    """
    quando = time.time() if quando is None else quando
    dados = _ler()
    dados['ultimo_anuncio'] = float(quando)
    if chave:
        dados['conteudo'] = chave
    dados['anunciado'] = True          # bilhete deste conteudo usado
    if chave:
        dados['tentativa'] = chave     # troca consumida (nao tenta de novo)
        marcar_anunciado(chave, dados)
    dados['intervalo'] = INTERVALO
    dados['em_exibicao'] = float(quando)
    # Piso: se o anuncio falhar em seguida, `cancelar_anuncio` apaga so o que
    # ESTE disparo gravou (nunca um intervalo de um anuncio realmente exibido).
    dados['piso'] = float(quando)
    return _gravar(dados)


def concluir_anuncio(quando=None):
    """O anuncio terminou (concluido ou pulado): comeca o intervalo AGORA.

    Chamado quando o player volta a tocar o conteudo. E o sinal mais fiel de
    "o anuncio acabou": a tela de anuncio fica na frente e o player so volta
    quando ela fecha, seja por conclusao, seja por pulo. Sem esse sinal (o
    Android matou a activity, o player nunca parou), o piso gravado em
    ``registrar_anuncio`` continua valendo e nada fica bloqueado.
    """
    quando = time.time() if quando is None else quando
    dados = _ler()
    inicio = dados.get('em_exibicao')
    if not inicio:
        return False          # nenhum anuncio em exibicao: nada a concluir
    try:
        inicio = float(inicio)
    except Exception:
        inicio = 0.0
    if inicio and (quando - inicio) > EXIBICAO_MAXIMA:
        # sinal atrasado demais: mantem o piso (nao empurra o anuncio adiante)
        dados.pop('em_exibicao', None)
        return _gravar(dados)
    dados['ultimo_anuncio'] = float(quando)
    dados.pop('em_exibicao', None)
    dados['anunciado'] = True
    dados['intervalo'] = INTERVALO
    return _gravar(dados)


def cancelar_anuncio(chave=None):
    """Anuncio NAO foi exibido (falhou/indisponivel): nao consome o intervalo.

    Devolve o bilhete: a proxima troca real de conteudo pode tentar de novo -
    o usuario nao fica sem monetizacao por causa de uma falha do SDK - e nada
    fica bloqueado. Nao ha tentativa repetida: quem chama so tenta de novo na
    proxima troca de conteudo.
    """
    dados = _ler()
    mudou = False
    if dados.pop('anunciados', None) is not None:
        mudou = True
    if chave and dados.get('conteudo') == chave:
        if dados.pop('anunciado', None) is not None:
            mudou = True
    # O disparo nao virou exibicao: desfaz o piso daquele disparo. Se ja havia
    # um anuncio de verdade contado antes deste, ele fica (o intervalo dele
    # continua valendo).
    piso = dados.get('piso')
    if piso and float(dados.get('ultimo_anuncio') or 0) == float(piso):
        dados.pop('ultimo_anuncio', None)
        mudou = True
    if piso:
        dados.pop('piso', None)
        mudou = True
    if dados.pop('em_exibicao', None) is not None:
        mudou = True
    if mudou:
        return _gravar(dados)
    return False


def encerrar_conteudo():
    """Fim da reproducao (PARAR / Voltar / Quadrado): fecha a sessao atual.

    Depois de sair do conteudo e passados os 2 minutos desde o ultimo anuncio
    exibido, entrar em qualquer conteudo (inclusive reabrir este mesmo filme
    ou canal) volta a exibir anuncio normalmente.
    """
    dados = _ler()
    mudou = False
    for chave in ('conteudo', 'anunciado', 'tentativa', 'anunciados'):
        if dados.pop(chave, None) is not None:
            mudou = True
    return _gravar(dados) if mudou else False


def esquecer_tudo():
    """Zera o estado (usado por testes/depuracao; nao roda no app)."""
    return _gravar({})


def espera_maxima():
    """Teto (segundos) que o gatilho pode ficar ocupado antes de liberar.

    O anuncio e assincrono: quem chama nao espera a tela fechar. Este teto
    existe so para o caso de o bind da activity travar - passado ele, a
    reproducao segue e o proximo conteudo tenta de novo.
    """
    return 8
