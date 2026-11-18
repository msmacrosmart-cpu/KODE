# -*- coding: utf-8 -*-
"""Ordenacao real das pastas do addon (barra "Todos / A a Z / ...").

Por que isso existe aqui e nao no skin: o Kodi 21 so aplica
``Container.SetSortMethod(id)`` quando o ``id`` existe em ``m_sortMethods``
da janela (``CGUIViewState::SetSortMethod``). Diretorio de plugin nasce com um
unico metodo -- ``SortByNone`` (``CPluginDirectory::EndOfDirectory`` adiciona
``AddSortMethod(SortByNone, 552, ...)`` quando o addon nao declara nenhum).
Logo, os botoes da barra de filtros chamavam um metodo inexistente e nada
acontecia: a lista continuava na ordem que o Brazuca publicou.

Aqui a ordem e aplicada nos proprios itens, antes de entregar o diretorio:
o botao da barra pede ``route=ordenar&ordem=...``, este modulo rele o
diretorio atual (``Container.FolderPath``), reordena e reabre pela rota
``pasta``, que devolve os mesmos itens -- com as URLs nativas do addon
preservadas -- na ordem escolhida.
"""
from __future__ import absolute_import, unicode_literals

# ``todos`` mantem exatamente a ordem publicada pelo addon.
ORDENS = ('todos', 'az', 'za', 'adicionados', 'votados', 'recentes')

ROTULO = {
    'todos': 'Todos',
    'az': 'A a Z',
    'za': 'Z a A',
    'adicionados': 'Últimos adicionados',
    'votados': 'Mais votados',
    'recentes': 'Mais recentes',
}

MARCA = 'plugin://plugin.video.smarted/'


def normalizar(ordem):
    """Ordem valida (qualquer outra coisa vira ``todos``)."""
    texto = (ordem or '').strip().lower()
    return texto if texto in ORDENS else 'todos'


def etiqueta(ordem):
    """Rotulo humano da ordem (para a notificacao da troca)."""
    return ROTULO.get(normalizar(ordem), ROTULO['todos'])


def _texto(item, *chaves):
    for chave in chaves:
        valor = item.get(chave)
        if isinstance(valor, str) and valor.strip():
            return valor.strip()
    return ''


def chave(item, ordem):
    """Chave de comparacao do item para a ordem pedida."""
    if ordem == 'az':
        return (_texto(item, 'label').casefold(),)
    if ordem == 'za':
        return (_texto(item, 'label').casefold(),)
    if ordem == 'adicionados':
        return (_texto(item, 'dateadded'), _texto(item, 'premiered'),
                _texto(item, 'label').casefold())
    if ordem == 'recentes':
        return (_texto(item, 'premiered', 'dateadded'), _texto(item, 'label').casefold())
    if ordem == 'votados':
        votos = item.get('votes')
        return (votos if isinstance(votos, int) else 0,
                item.get('rating') if isinstance(item.get('rating'), (int, float)) else 0,
                _texto(item, 'label').casefold())
    return ()


def aplicar(items, ordem):
    """Devolve os itens na ordem pedida (``todos`` nao mexe em nada)."""
    ordem = normalizar(ordem)
    lista = list(items or [])
    if ordem == 'todos':
        return lista
    # reverse=True para que "adicionados/recentes/votados" mostrem o maior
    # primeiro; "za" e o inverso alfabetico.
    invertido = ordem in ('za', 'adicionados', 'recentes', 'votados')
    return sorted(lista, key=lambda item: chave(item, ordem), reverse=invertido)


def url_da_pasta(url):
    """URL interna do Brazuca a partir do que esta na janela.

    Aceita tanto a URL nativa (``plugin://plugin.video.BrazucaPlay.Matrix/...``)
    quanto a rota ``pasta`` ja reescrita por este modulo, para o filtro poder
    ser trocado varias vezes sem empilhar parametros.
    """
    from urllib.parse import parse_qs, urlencode, urlsplit

    texto = (url or '').strip()
    if not texto:
        return ''
    if texto.startswith(MARCA):
        dados = parse_qs(urlsplit(texto).query, keep_blank_values=True)
        if dados.get('route', [''])[0] == 'pasta':
            return dados.get('url', [''])[0]
    # Qualquer diretorio de plugin e ordenavel: a pasta do Brazuca (uso real) e
    # as proprias rotas deste addon (util para conferir no aparelho sem rede).
    if texto.startswith('plugin://'):
        return texto
    return ''


def url_da_rota(url, ordem):
    """URL da rota ``pasta`` com a ordem aplicada (vazia se nao houver pasta)."""
    from urllib.parse import urlencode

    pasta = url_da_pasta(url)
    if not pasta:
        return ''
    return MARCA + '?' + urlencode({'route': 'pasta', 'url': pasta,
                                    'ordem': normalizar(ordem)})


def ordem_da_url(url):
    """Ordem que ja esta aplicada na URL da janela (``todos`` por padrao)."""
    from urllib.parse import parse_qs, urlsplit

    texto = (url or '').strip()
    if not texto.startswith(MARCA):
        return 'todos'
    dados = parse_qs(urlsplit(texto).query, keep_blank_values=True)
    if dados.get('route', [''])[0] != 'pasta':
        return 'todos'
    return normalizar(dados.get('ordem', ['todos'])[0])
