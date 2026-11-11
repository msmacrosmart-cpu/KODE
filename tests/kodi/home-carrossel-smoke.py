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


def log(message):
    xbmc.log('%s %s' % (MARK, message), xbmc.LOGINFO)


def fail(message):
    xbmc.log('%s_FAILED %s' % (MARK, message), xbmc.LOGERROR)
    raise SystemExit(1)


def rpc(method, params):
    response = json.loads(xbmc.executeJSONRPC(json.dumps(
        {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params})))
    if 'error' in response:
        raise RuntimeError('%s: %s' % (method, response['error'].get('message', 'error')))
    return response.get('result') or {}


def directory(path):
    files = rpc('Files.GetDirectory', {'directory': path, 'media': 'video',
                                       'properties': ['title', 'thumbnail', 'fanart', 'art']}).get('files', [])
    if not isinstance(files, list):
        raise RuntimeError('resposta inesperada para ' + path)
    return files


def art_of(item):
    art = item.get('art') or {}
    return item.get('thumbnail') or art.get('poster') or art.get('thumb') or art.get('icon') or ''


def main():
    for addon in ADDONS:
        rpc('Addons.SetAddonEnabled', {'addonid': addon, 'enabled': True})

    problemas = []
    for alvo in ALVOS:
        rota = 'plugin://plugin.video.smarted/?route=carrossel&alvo=%s' % alvo
        files = directory(rota)
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
    brazuca = 'plugin://plugin.video.BrazucaPlay.Matrix/?mode=27&url=%23filmes_menu'
    xbmc.executebuiltin('ActivateWindow(Videos, "%s", return)' % brazuca)
    monitor = xbmc.Monitor()
    ativo = False
    for _ in range(40):
        if xbmc.getCondVisibility('Window.IsActive(videos)'):
            ativo = True
            break
        if monitor.waitForAbort(0.5):
            break
    interno = directory(brazuca)
    log('NAVEGACAO janela=%s itens=%d' % ('videos' if ativo else 'nao', len(interno)))
    if not ativo:
        problemas.append('ActivateWindow(Videos) nao abriu a janela de videos')
    if len(interno) < 4:
        problemas.append('menu de filmes com %d itens' % len(interno))

    # Favoritos: linha nativa da Home precisa listar algo quando houver favoritos
    try:
        favoritos = directory('plugin://plugin.video.smarted/?route=favoritos-filmes')
        log('FAVORITOS itens=%d' % len(favoritos))
    except RuntimeError:
        log('FAVORITOS nenhum (aceitavel em perfil sem favoritos)')

    if problemas:
        fail('; '.join(problemas))
    log('_OK todas as linhas com conteudo real')


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as error:  # noqa: BLE001 - relatar no log do Kodi
        fail(repr(error))
