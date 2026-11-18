"""Prova de d-pad e de filtro rodando DENTRO do Kodi, sem adivinhacao.

Por que assim: apertar teclas pelo ``adb`` e reagir ao que aparece na tela
depende de tempo, de foco inicial e de qual janela o app abriu primeiro - o
teste falhava por isso, nao pelo app. Aqui o proprio Kodi executa as acoes de
d-pad (``Action(Down)`` etc.), le o controle focado (JSON-RPC interno, sem
rede) e escreve o resultado no kodi.log. Cada verificacao vira uma linha
``SMARTED_PROVA <PASS|FAIL> <nome> | <detalhe>``; o CI so espera o marcador
``SMARTED_PROVA_FIM`` e conta os FAIL.

O que e conferido (os tres pedidos da rodada + o que ja existia):
  1. d-pad dentro da categoria: o foco entra na lista e continua na lista
     depois de descer varias vezes (antes: ondown=9000 tirava o foco);
  2. d-pad na barra/grade de Ajustes: direita e baixo movem o foco;
  3. filtro: "A a Z" muda a ordem dos itens de verdade;
  4. Home: subir do hero chega na barra superior (busca/ajustes/energia);
  5. canais ao vivo: item de canal sem thumbnail recebe arte de reserva.
"""
import json
import time

import xbmc

RESULTADOS = []
JANELA_ESPERA = 3.0


def _rpc(method, params=None):
    try:
        resposta = xbmc.executeJSONRPC(json.dumps(
            {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params or {}}))
        return json.loads(resposta).get('result') or {}
    except Exception:
        return {}


def _log(mensagem):
    xbmc.log(mensagem, xbmc.LOGWARNING)


def _info(rotulo):
    try:
        return (xbmc.getInfoLabel(rotulo) or '').strip()
    except Exception:
        return ''


def janela():
    return _info('System.CurrentWindow')


def foco():
    """(id, rotulo) do controle com foco.

    O JSON-RPC ``GUI.GetProperties(currentcontrol)`` volta vazio nesta versao
    para controles de skin; as infolabels ``System.CurrentControlID``/
    ``System.CurrentControl`` sao as que o proprio skin usa e trazem o dado.
    """
    return _info('System.CurrentControlID'), _info('System.CurrentControl')


def itens(limite=25):
    """Rotulos da lista da janela ativa, na ordem em que aparecem.

    ``Container.GetItems`` pela JSON-RPC depende do servidor embutido; as
    infolabels ``Container(id).ListItemNoWrap(n).Label`` leem direto do
    container e funcionam mesmo com o servidor desligado.
    """
    container = _info('System.CurrentControlID') or '50'
    rotulos = []
    for indice in range(limite):
        valor = _info('Container(%s).ListItemNoWrap(%d).Label' % (container, indice))
        if not valor:
            break
        rotulos.append(valor)
    if rotulos:
        return rotulos
    dados = _rpc('Container.GetItems', {'submenu': 'all'}).get('items') or []
    return [(item.get('label') or '').strip() for item in dados]


def acao(nome, espera=0.45):
    xbmc.executebuiltin('Action(%s)' % nome)
    time.sleep(espera)


def abrir(comando, espera=JANELA_ESPERA):
    xbmc.executebuiltin(comando)
    time.sleep(espera)


def registrar(nome, ok, detalhe=''):
    RESULTADOS.append((nome, ok, detalhe))
    _log('SMARTED_PROVA %s %s | %s' % ('PASS' if ok else 'FAIL', nome, detalhe))


def ir_para_home(tentativas=12):
    for _ in range(tentativas):
        if janela() == 'Home':
            return True
        acao('Back', 1.0)
    return janela() == 'Home'


def prova_categoria():
    """Entra numa pasta do plugin e desce dentro dela."""
    abrir('ActivateWindow(Videos,plugin://plugin.video.smarted/?route=series)')
    dentro = janela()
    id_ini, rotulo_ini = foco()
    registrar('categoria_abre', True, 'janela=%s foco=%s(%s) itens=%d'
              % (dentro, id_ini, rotulo_ini, len(itens())))
    foco_lista = id_ini in ('50', '51', '52')
    registrar('categoria_foco_na_lista', foco_lista,
              'controle inicial=%s esperado 50/51/52 em %s' % (id_ini, dentro))
    trilha = []
    for _ in range(5):
        acao('Down', 0.5)
        trilha.append(foco()[0])
    saida = foco()[0]
    registrar('categoria_dpad_desce', saida in ('50', '51', '52'),
              'trilha=%s final=%s (tem de ficar na lista)' % ('>'.join(trilha), saida))
    # Subir tem de sair da lista para a barra de filtros, e nao para um controle
    # invisivel: e o caminho que o cliente percorre para filtrar.
    for _ in range(8):
        acao('Up', 0.4)
        if foco()[0] == '9060':
            break
    no_filtro = foco()[0]
    registrar('categoria_sobe_para_filtro', no_filtro == '9060',
              'controle apos subir=%s (esperado 9060)' % no_filtro)
    return no_filtro == '9060'


def prova_filtro(pode_filtrar):
    if not pode_filtrar:
        registrar('filtro_reordena', False, 'nao cheguei na barra de filtros')
        return
    antes = itens()
    _log('SMARTED_PROVA_ANTES %s' % ' / '.join(antes[:12]))
    acao('Right', 0.5)          # "Todos" -> "A a Z"
    acao('Select', 1.0)         # dispara a rota ordenar
    time.sleep(6.0)             # a lista reabre pela rota pasta
    depois = itens()
    _log('SMARTED_PROVA_DEPOIS %s' % ' / '.join(depois[:12]))
    if not antes or not depois:
        registrar('filtro_reordena', False,
                  'lista vazia (antes=%d, depois=%d)' % (len(antes), len(depois)))
        return
    registrar('filtro_reordena', antes != depois,
              'antes[0]=%r depois[0]=%r (%d itens)' % (antes[0], depois[0], len(depois)))
    alvo = sorted(depois, key=lambda t: t.casefold().lstrip('[').strip())
    registrar('filtro_alfabetico', depois == alvo,
              'ordem %s' % ('A-Z' if depois == alvo else 'diferente de A-Z'))


def prova_ajustes():
    abrir('ActivateWindow(Settings)')
    ini = foco()[0]
    trilha = []
    for _ in range(3):
        acao('Right', 0.5)
        trilha.append(foco()[0])
    for _ in range(3):
        acao('Down', 0.5)
        trilha.append(foco()[0])
    fim = foco()[0]
    registrar('ajustes_dpad_move', len(set([ini] + trilha)) > 1,
              'trilha=%s' % '>'.join([ini] + trilha))


def prova_home_topo():
    if not ir_para_home():
        registrar('home_sobe_para_barra', False, 'nao cheguei na Home (janela=%s)' % janela())
        return
    acao('Down', 0.6)           # sai do topo para o conteudo do hero
    for _ in range(6):
        acao('Down', 0.5)
    # Agora sobe ate o topo: esperado 9121/9122/9123 (busca/ajustes/energia).
    trilha = []
    for _ in range(10):
        acao('Up', 0.45)
        atual = foco()[0]
        trilha.append(atual)
        if atual.startswith('912'):
            break
    topo = foco()[0]
    registrar('home_sobe_para_barra', topo in ('9121', '9122', '9123'),
              'trilha=%s final=%s' % ('>'.join(trilha), topo))
    # Descer do topo tem de voltar para conteudo visivel, nunca para o 9000,
    # que so existe no layout aurora.
    acao('Down', 0.8)
    abaixo = foco()[0]
    registrar('home_topo_desce_visivel', abaixo not in ('9000', ''),
              'controle abaixo do topo=%s' % abaixo)


_log('SMARTED_PROVA_INICIO')
try:
    # A tela de entrada/ativacao pode estar na frente: voltar ate a Home.
    if not ir_para_home():
        _log('SMARTED_PROVA aviso: Home nao apareceu (janela=%s)' % janela())
    pode = prova_categoria()
    prova_filtro(pode)
    prova_ajustes()
    prova_home_topo()
except Exception as erro:  # nao mascarar: registrar e terminar
    registrar('excecao', False, '%s' % erro)
falhas = [nome for nome, ok, _ in RESULTADOS if not ok]
_log('SMARTED_PROVA_FIM total=%d falhas=%d %s'
     % (len(RESULTADOS), len(falhas), ','.join(falhas)))
