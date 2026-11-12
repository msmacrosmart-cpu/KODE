"""Valida, no emulador, que as linhas da Home trazem CONTEUDO real.

Roda dentro do Kodi do emulador (F10 pelo keymap de teste) e usa o mesmo
JSON-RPC que a skin usa. Perfil sintetico, addon publico 2.1.4, sem dados
pessoais. Cada verificacao deixa um marcador no log:

    SMARTED_TEST_CARROSSEL_<ALVO> total=N midia=N arte=N menu=N
    SMARTED_TEST_CARROSSEL_OK
    SMARTED_TEST_CARROSSEL_FAILED <motivo>
"""
import json
import os
import sys
from urllib.parse import urlencode

import xbmc

sys.path.insert(0, os.path.dirname(__file__))
from search import TAGS, normalize  # noqa: E402

MARK = 'SMARTED_TEST_CARROSSEL'
ADDONS = ('script.module.six', 'script.module.kodi-six', 'script.module.certifi',
          'script.module.chardet', 'script.module.idna', 'script.module.urllib3',
          'script.module.requests', 'script.module.simplejson',
          'plugin.video.BrazucaPlay.Matrix', 'plugin.video.smarted')
MENU_HINTS = ('categoria', 'pesquis', 'ordem', 'todas', 'menu', 'configura', 'verificar')
ALVOS = ('canais', 'filmes', 'series')


def brazuca(mode, path):
    """URL do addon no mesmo formato da skin.

    O Brazuca 2.1.4 faz quote_plus em iconimage/fanart; quando o parametro nao
    vem na URL o valor e None e o menu estoura com
    "quote_from_bytes() expected bytes". A skin sempre manda DefaultFolder.png.
    """
    query = urlencode({'url': path, 'mode': mode, 'name': '',
                       'iconimage': 'DefaultFolder.png', 'fanart': 'DefaultFolder.png',
                       'description': 'Menu'})
    return 'plugin://plugin.video.BrazucaPlay.Matrix/?' + query
# abas superiores: o botao da skin abre o menu nativo do addon (nao o
# carrossel), entao basta o menu responder com as pastas do Brazuca Play
ABAS = {'novelas': 25, 'animes': 22, 'doramas': 31, 'desenhos': 28}


def log(message):
    xbmc.log('%s %s' % (MARK, message), xbmc.LOGINFO)


def ok(message):
    """Marcador sem espaco: o script do emulador procura <MARK>_OK no logcat."""
    xbmc.log('%s_OK %s' % (MARK, message), xbmc.LOGINFO)


def fail(message):
    xbmc.log('%s_FAILED %s' % (MARK, message), xbmc.LOGERROR)
    raise SystemExit(1)


def rpc(method, params):
    response = json.loads(xbmc.executeJSONRPC(json.dumps(
        {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})))
    if 'error' in response:
        raise RuntimeError('%s: %s' % (method, response['error'].get('message', 'error')))
    return response.get('result') or {}


PROPS = ('title', 'thumbnail', 'fanart', 'art')
HERO_PROPS = PROPS + ('plot', 'genre', 'rating', 'premiered', 'year', 'duration')


def directory(path, tentativas=1, espera=2.0, propriedades=PROPS):
    """Files.GetDirectory com novas tentativas (o Kodi pode estar ocupado)."""
    import time
    ultimo = None
    for tentativa in range(max(1, tentativas)):
        try:
            files = rpc('Files.GetDirectory', {'directory': path, 'media': 'video',
                                               'properties': list(propriedades)}).get('files', [])
            if not isinstance(files, list):
                raise RuntimeError('resposta inesperada para ' + path)
            return files
        except Exception as error:  # noqa: BLE001
            ultimo = error
            if tentativa + 1 < tentativas:
                time.sleep(espera)
    raise ultimo


def art_of(item):
    art = item.get('art') or {}
    return item.get('thumbnail') or art.get('poster') or art.get('thumb') or art.get('icon') or ''


def perfis_addons():
    """Diagnostico: o que existe em special://home/addons e no addon manager."""
    import xbmcvfs
    pasta = xbmcvfs.translatePath('special://home/addons')
    try:
        nomes = sorted(xbmcvfs.listdir(pasta)[0])
    except Exception as error:  # noqa: BLE001
        nomes = ['ERRO ' + repr(error)]
    presentes = [n for n in nomes if n.startswith('plugin.video.Brazuca')]
    log('ADDONS pasta=%s total=%d brazuca=%s' % (pasta, len(nomes), presentes))
    try:
        detalhes = rpc('Addons.GetAddonDetails', {'addonid': 'plugin.video.BrazucaPlay.Matrix',
                                                  'properties': ['version', 'enabled', 'broken']})
        log('ADDONS manager=%s' % json.dumps(detalhes.get('addon', {}), ensure_ascii=False))
    except Exception as error:  # noqa: BLE001
        log('ADDONS manager=ausente (%s)' % error)


def main():
    perfis_addons()
    for addon in ADDONS:
        try:
            rpc('Addons.SetAddonEnabled', {'addonid': addon, 'enabled': True})
        except Exception as error:  # noqa: BLE001
            log('ADDONS enable falhou %s: %s' % (addon, error))
    xbmc.executebuiltin('UpdateLocalAddons()')
    perfis_addons()

    problemas = []
    for alvo in ALVOS:
        rota = 'plugin://plugin.video.smarted/?route=carrossel&alvo=%s' % alvo
        try:
            files = directory(rota, tentativas=3, espera=3.0)
        except Exception as error:  # noqa: BLE001
            log('%s vazio (%s)' % (alvo.upper(), error))
            problemas.append('%s: linha vazia (%s)' % (alvo, error))
            continue
        midia = [f for f in files if f.get('filetype') == 'file']
        arte = [f for f in files if art_of(f)]
        menu = [f for f in files
                if any(hint in normalize(TAGS.sub('', f.get('label', ''))) for hint in MENU_HINTS)]
        log('%s total=%d midia=%d arte=%d menu=%d' % (alvo.upper(), len(files), len(midia), len(arte), len(menu)))
        for item in files[:8]:
            log('  %s | %s | %s' % (TAGS.sub('', item.get('label', ''))[:52].replace('|', '/'),
                                    item.get('filetype'), art_of(item)[:60].replace('|', '/')))
        if not files:
            problemas.append(alvo + ': linha vazia')
            continue
        if len(arte) < min(3, len(files)):
            problemas.append('%s: %d/%d itens sem arte' % (alvo, len(files) - len(arte), len(files)))
        if alvo in ('canais', 'filmes') and len(midia) < max(1, len(files) // 2):
            problemas.append('%s: apenas %d de %d itens reproduzem' % (alvo, len(midia), len(files)))
        if menu and len(menu) == len(files):
            problemas.append('%s: linha só com pastas de menu' % alvo)

    # Navegacao interna em tela cheia: a janela de videos abre o diretorio real
    menu_filmes = brazuca(27, '#filmes_menu')
    # confere o diretorio antes de abrir a janela: com a janela de videos ativa
    # o addon fica ocupado e a mesma chamada volta vazia
    try:
        interno = directory(menu_filmes, tentativas=4, espera=3.0)
        log('MENU FILMES itens=%d' % len(interno))
    except Exception as error:  # noqa: BLE001
        interno = []
        log('MENU FILMES falhou (%s)' % error)
    if len(interno) < 4:
        problemas.append('menu de filmes com %d itens' % len(interno))
    xbmc.executebuiltin('ActivateWindow(Videos, "%s", return)' % menu_filmes)
    monitor = xbmc.Monitor()
    ativo = False
    for _ in range(40):
        if xbmc.getCondVisibility('Window.IsActive(videos)'):
            ativo = True
            break
        if monitor.waitForAbort(0.5):
            break
    log('NAVEGACAO janela=%s' % ('videos' if ativo else 'nao'))
    if not ativo:
        problemas.append('ActivateWindow(Videos) nao abriu a janela de videos')

    # Abas superiores (9013-9016): cada botao abre o menu nativo do addon; o
    # menu precisa responder com as pastas do Brazuca Play, senao a tela fica
    # vazia no aparelho.
    for aba, modo in sorted(ABAS.items()):
        raiz = brazuca(modo, '#%s_menu' % aba)
        try:
            menu = directory(raiz, tentativas=2, espera=2.0)
            log('ABA %s itens=%d' % (aba.upper(), len(menu)))
            if not menu:
                problemas.append('aba %s vazia' % aba)
        except Exception as error:  # noqa: BLE001
            log('ABA %s falhou (%s)' % (aba.upper(), error))
            problemas.append('aba %s: %s' % (aba, error))

    # Linha nova da Home (9203): rota de series recentes precisa responder
    rota_recentes = 'plugin://plugin.video.smarted/?route=recent-series'
    try:
        recentes = directory(rota_recentes, tentativas=3, espera=3.0)
        log('RECENTES total=%d' % len(recentes))
        if not recentes:
            problemas.append('series recentes: linha vazia')
    except Exception as error:  # noqa: BLE001
        log('RECENTES falhou (%s)' % error)
        problemas.append('series recentes: %s' % error)

    # HERO (linha 9201): a pasta Lancamentos do proprio Brazuca precisa render
    # pelo menos 7 filmes reais, com arte e ficha (ano/genero/nota/data)
    try:
        hero = directory('plugin://plugin.video.smarted/?route=recent-movies',
                         tentativas=3, espera=3.0, propriedades=HERO_PROPS)
        filmes = [f for f in hero if f.get('filetype') == 'file']
        com_arte = [f for f in filmes if art_of(f)]
        com_ficha = [f for f in filmes if f.get('plot') and f.get('genre')]
        log('HERO total=%d filmes=%d arte=%d ficha=%d'
            % (len(hero), len(filmes), len(com_arte), len(com_ficha)))
        for item in filmes[:10]:
            log('  HERO %s | ano=%s | nota=%s | data=%s | genero=%s | %s'
                % (TAGS.sub('', item.get('label', ''))[:44].replace('|', '/'),
                   item.get('year'), item.get('rating'), item.get('premiered'),
                   (item.get('genre') or [''])[0] if isinstance(item.get('genre'), list)
                   else item.get('genre'), art_of(item)[:52].replace('|', '/')))
        if len(filmes) < 7:
            problemas.append('HERO: apenas %d filmes reais (minimo 7)' % len(filmes))
        if len(com_ficha) < 7:
            problemas.append('HERO: %d de %d filmes com ficha' % (len(com_ficha), len(filmes)))
        if len(com_arte) < len(filmes):
            problemas.append('HERO: %d de %d filmes sem arte'
                             % (len(filmes) - len(com_arte), len(filmes)))
    except Exception as error:  # noqa: BLE001
        log('HERO falhou (%s)' % error)
        problemas.append('HERO: %s' % error)

    # BARRA superior: sync-nav publica os favoritos do Brazuca; navegacao lista
    # exatamente as opcoes usadas pela skin (destino real, nunca lista inventada)
    try:
        directory('plugin://plugin.video.smarted/?route=sync-nav', tentativas=2, espera=2.0)
    except Exception as error:  # noqa: BLE001
        log('BARRA sync-nav falhou (%s)' % error)
        problemas.append('BARRA: sync-nav %s' % error)
    try:
        barra = directory('plugin://plugin.video.smarted/?route=navegacao')
        reais = [b for b in barra if 'plugin.video.BrazucaPlay' in (b.get('file') or '')]
        log('BARRA opcoes=%d destinos_reais=%d' % (len(barra), len(reais)))
        for item in barra[:10]:
            log('  BARRA %s -> %s' % (TAGS.sub('', item.get('label', ''))[:40].replace('|', '/'),
                                      (item.get('file') or '')[:70].replace('|', '/')))
        try:
            rotulos = rpc('XBMC.GetInfoLabels', {'labels': [
                'Skin.String(smarted_nav_%d)' % slot for slot in range(1, 11)]})
            preenchidos = [valor for chave, valor in rotulos.items()
                           if chave.startswith('Skin.String') and valor]
            log('BARRA skin_strings=%s' % [r for r in preenchidos][:10])
        except Exception as error:  # noqa: BLE001
            log('BARRA skin_strings indisponiveis (%s)' % error)
        if not barra:
            problemas.append('BARRA: nenhuma opcao')
        if len(reais) != len(barra):
            problemas.append('BARRA: %d de %d opcoes sem destino do addon'
                             % (len(barra) - len(reais), len(barra)))
    except Exception as error:  # noqa: BLE001
        log('BARRA falhou (%s)' % error)
        problemas.append('BARRA: %s' % error)

    # Favoritos: linha nativa da Home precisa listar algo quando houver favoritos
    try:
        favoritos = directory('plugin://plugin.video.smarted/?route=favoritos-filmes')
        log('FAVORITOS itens=%d' % len(favoritos))
    except RuntimeError:
        log('FAVORITOS nenhum (aceitavel em perfil sem favoritos)')

    if problemas:
        fail('; '.join(problemas))
    ok('todas as linhas com conteudo real')


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as error:  # noqa: BLE001 - relatar no log do Kodi
        fail(repr(error))
