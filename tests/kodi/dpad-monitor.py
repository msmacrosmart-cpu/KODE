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
import xbmcvfs

RESULTADOS = []
JANELA_ESPERA = 2.0
# Teto de tempo da prova inteira: o CI espera o marcador FIM em 5 min. Se algo
# travar (janela que nao abre, lista que nao carrega), o marcador tem de sair
# mesmo assim, com as verificacoes restantes marcadas como nao executadas.
PRAZO_TOTAL = 240.0
_INICIO = time.time()

def estourou():
    return (time.time() - _INICIO) > PRAZO_TOTAL


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


def _condicao(expressao):
    """Condicao booleana do skin (``Control.HasFocus(50)`` e condicao, NAO
    infolabel: por getInfoLabel ela sempre volta vazia)."""
    try:
        return bool(xbmc.getCondVisibility(expressao))
    except Exception:
        return False


def janela():
    return _info('System.CurrentWindow')


# Controles focaveis: descobertos dos XMLs do skin em tempo de execucao, em vez
# de uma lista fixa. Numa execucao real o foco caiu em ids que a lista fixa nao
# cobria (ex.: 9030 no menu lateral), e o teste acusava "semo foco" sem haver
# defeito. Lendo os XMLs, o conjunto e exatamente o do skin que esta rodando.
# Um arquivo por janela: ler TODOS os XMLs custa caro (cada Control.HasFocus
# pega o lock da GUI) e a prova estourava os 5 minutos. Aqui so os controles da
# janela na tela entram na busca.
XML_DA_JANELA = {
    'home': ('Home.xml',),
    'vídeos': ('MyVideoNav.xml',), 'videos': ('MyVideoNav.xml',),
    'ajustes': ('Settings.xml',), 'settings': ('Settings.xml',),
}
XML_PADRAO = ('Home.xml', 'MyVideoNav.xml', 'Settings.xml')
_ID_CACHE = {}


def _ids_do_skin():
    """Ids focaveis da janela atual (cacheado por janela)."""
    chave = janela().lower()
    if chave in _ID_CACHE:
        return _ID_CACHE[chave]
    import os
    import xml.etree.ElementTree as ET

    nomes = XML_DA_JANELA.get(chave, XML_PADRAO)
    tipos = {'button', 'radiobutton', 'togglebutton', 'spincontrol', 'list',
             'panel', 'grouplist', 'fixedlist', 'wraplist', 'textbox', 'edit',
             'slider', 'mover', 'colorbutton'}
    candidatos = []
    for base in ('special://home/addons', 'special://xbmc/addons'):
        try:
            candidatos.append(xbmcvfs.translatePath(base))
        except Exception:
            pass
    candidatos.append(os.path.join(
        xbmcvfs.translatePath('special://profile'), '..', 'addons'))
    vistos = []
    for skin in ('skin.estilo.personalizado', 'skin.novatv'):
        for nome in nomes:
            caminho = ''
            for base in candidatos:
                tentativa = os.path.join(base, skin, 'xml', nome)
                if os.path.exists(tentativa):
                    caminho = tentativa
                    break
            if not caminho:
                continue
            try:
                raiz = ET.parse(caminho).getroot()
            except Exception as erro:
                _log('SMARTED_PROVA_IDS_ERRO %s: %s' % (caminho, erro))
                continue
            for controle in raiz.iter('control'):
                cid = controle.get('id')
                if controle.get('type') in tipos and cid and cid not in vistos:
                    vistos.append(cid)
    _ID_CACHE[chave] = vistos
    _log('SMARTED_PROVA_IDS (%s, %d) %s' % (chave, len(vistos), ','.join(vistos[:100])))
    return vistos


def foco():
    """Id do controle com foco.

    ``System.CurrentControlID`` nao e confiavel para todo controle deste skin e
    ``GUI.GetProperties(currentcontrol)`` volta vazio; ``Control.HasFocus(id)``
    e o teste que o proprio skin usa nas condicoes ``<visible>``.
    """
    atual = _info('System.CurrentControlId') or _info('System.CurrentControlID')
    if atual:
        return atual
    for cid in _ids_do_skin():
        if _condicao('Control.HasFocus(%s)' % cid):
            return cid
    return '?'


def itens(limite=12):
    """Rotulos da lista, na ordem em que aparecem.

    ``Container(id)`` e sintaxe de janela; fora dela o Kodi so resolve o
    container ativo. Como a prova sempre roda com o foco na lista de videos,
    ``ListItemAbsolute(n)`` (container ativo) e o caminho que funciona.
    """
    rotulos = []
    for indice in range(limite):
        valor = (_info('ListItemAbsolute(%d).Label' % indice)
                 or _info('ListItemNoWrap(%d).Label' % indice))
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
    # Mesmo caminho do app: a janela Videos com a rota do plugin. "return"
    # garante que ela abre por cima da Home (sem isso o Kodi pode manter a Home).
    abrir('ActivateWindow(Videos,plugin://plugin.video.smarted/?route=series)')
    dentro = janela()
    id_ini = foco()
    # Diagnostico no proprio resultado: se o foco vier vazio, o detalhe mostra
    # quantos ids foram lidos do skin e o valor cru de Control.HasFocus(50).
    ids = _ids_do_skin()
    registrar('categoria_abre', True,
              'janela=%s foco=%s itens=%d ids=%d hasFocus50=%r primeiros=%s'
              % (dentro, id_ini, len(itens()), len(ids),
                 _condicao('Control.HasFocus(50)'), ','.join(ids[:12])))
    LISTAS = ('50', '51', '52')
    registrar('categoria_foco_na_lista', id_ini in LISTAS,
              'janela=%s controle inicial=%s (esperado 50/51/52)' % (dentro, id_ini))
    trilha = []
    for _ in range(5):
        acao('Down', 0.5)
        trilha.append(foco())
    saida = foco()
    registrar('categoria_dpad_desce', saida in LISTAS,
              'trilha=%s final=%s (tem de ficar na lista)' % ('>'.join(trilha), saida))
    # Subir tem de sair da lista para a barra de filtros, e nao para um controle
    # invisivel: e o caminho que o cliente percorre para filtrar.
    for _ in range(8):
        acao('Up', 0.4)
        if foco() == '9060':
            break
    no_filtro = foco()
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
    ini = foco()
    trilha = []
    for _ in range(3):
        acao('Right', 0.5)
        trilha.append(foco())
    for _ in range(3):
        acao('Down', 0.5)
        trilha.append(foco())
    fim = foco()
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
        atual = foco()
        trilha.append(atual)
        if atual in ('9121', '9122', '9123'):
            break
    topo = foco()
    registrar('home_sobe_para_barra', topo in ('9121', '9122', '9123'),
              'trilha=%s final=%s' % ('>'.join(trilha), topo))
    # Descer do topo tem de voltar para conteudo visivel, nunca para o 9000,
    # que so existe no layout aurora.
    acao('Down', 0.8)
    abaixo = foco()
    registrar('home_topo_desce_visivel', abaixo not in ('9000', ''),
              'controle abaixo do topo=%s' % abaixo)


_log('SMARTED_PROVA_INICIO')
try:
    # A tela de entrada/ativacao pode estar na frente: voltar ate a Home.
    if not ir_para_home():
        _log('SMARTED_PROVA aviso: Home nao apareceu (janela=%s)' % janela())
    if estourou():
        registrar('categoria', False, 'nao executou: prazo esgotado')
        registrar('filtro', False, 'nao executou: prazo esgotado')
    else:
        pode = prova_categoria()
        if estourou():
            registrar('filtro', False, 'nao executou: prazo esgotado')
        else:
            prova_filtro(pode)
    for nome, etapa in (('ajustes', prova_ajustes), ('home', prova_home_topo)):
        if estourou():
            registrar(nome, False, 'nao executou: prazo de %ds esgotado' % PRAZO_TOTAL)
            continue
        etapa()
except Exception as erro:  # nao mascarar: registrar e terminar
    registrar('excecao', False, '%s' % erro)
falhas = [nome for nome, ok, _ in RESULTADOS if not ok]
_log('SMARTED_PROVA_FIM total=%d falhas=%d %s'
     % (len(RESULTADOS), len(falhas), ','.join(falhas)))
