#!/usr/bin/env python3
"""Simulador de primeiro boot: monta um "Kodi portátil" e valida a Home 3x.

LIMITE HONESTO: este sandbox não tem KVM, `adb`, `emulator`, `java` nem acesso
aos repositórios do SDK Android, então **não é possível rodar um AVD aqui**.
O que este simulador faz é reproduzir, em Python, o mesmo encadeamento que o
aparelho executa no primeiro boot:

    APK base (assets/smarted/profile + assets/addons)
      -> perfil em disco (userdata/guisettings.xml, favourites.xml, addons/)
      -> service.smarted.bootstrap (repair + enable + favoritos + performance
         + skin/nós da Home)                       [código real do repositório]
      -> skin SMARTEDTV instalada como add-on de sistema (id skin.novatv)
      -> execução REAL do plugin.video.BrazucaPlay.Matrix para cada nó da Home
         (mesmos parâmetros que a skin usa)       [addon real do perfil semeado]
      -> asserções: skin ativa, 10 atalhos, cada botão/linha da Home devolve
         itens reais do addon.

Uso:
    python3 tools/kodi/simulate-first-boot.py --passes 3 [--base APK] [--workdir DIR]
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from urllib.parse import unquote
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / 'tools' / 'kodi'
REPO_SKIN = ROOT / 'kodi' / 'skin.estilo.personalizado'
BUILD_SCRIPT = TOOLS / 'build-release-apk.py'
RUNNER = TOOLS / 'kodi_plugin_runner.py'
BOOT_RUNNER = TOOLS / 'kodi_boot_runner.py'
DEFAULT_BASE = Path('/tmp/base/SMARTED-TV-v1.0.22-arm64.apk')
PLUGIN_ID = 'plugin.video.BrazucaPlay.Matrix'
SKIN_ID = 'skin.novatv'


def skin_version():
    match = re.search(r'SKIN_VERSION\s*=\s*"([^"]+)"', BUILD_SCRIPT.read_text(encoding='utf-8'))
    return match.group(1) if match else '1.0.3'


def stage_base(base_apk, stage):
    """Extrai assets/smarted/profile e assets/addons do APK base (uma vez)."""
    marker = stage / '.staged'
    if marker.is_file():
        return
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    wanted = []
    with zipfile.ZipFile(base_apk) as archive:
        for name in archive.namelist():
            if name.startswith('assets/smarted/profile/') or name.startswith('assets/addons/'):
                wanted.append(name)
        archive.extractall(stage, members=wanted)
    # cópia "pristina" dos XML que o bootstrap reescreve: as passagens usam
    # hardlinks, e escrita em disco vazaria de volta para o stage.
    pristino = stage / '.pristine-userdata'
    if pristino.exists():
        shutil.rmtree(pristino)
    origem_userdata = stage / 'assets' / 'smarted' / 'profile' / 'userdata'
    if origem_userdata.is_dir():
        shutil.copytree(origem_userdata, pristino, copy_function=shutil.copy2)
    marker.write_text('ok', encoding='utf-8')


def clone(src, dst):
    """Cópia com hardlinks (rápida) para isolar cada passagem."""
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, copy_function=os.link)


def install_skin(xbmc_dir):
    """Instala a skin do repositório como add-on de sistema (id skin.novatv)."""
    destino = xbmc_dir / 'addons' / SKIN_ID
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(REPO_SKIN, destino,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.bak'))
    addon_xml = destino / 'addon.xml'
    texto = addon_xml.read_text(encoding='utf-8')
    texto = re.sub(r'id="skin\.estilo\.personalizado"', 'id="%s"' % SKIN_ID, texto, count=1)
    texto = re.sub(r'version="[^"]+"', 'version="%s"' % skin_version(), texto, count=1)
    addon_xml.write_text(texto, encoding='utf-8')


def home_xml(xbmc_dir):
    path = xbmc_dir / 'addons' / SKIN_ID / 'xml' / 'Home.xml'
    return path if path.is_file() else None


def routes_from_home(path):
    """Extrai os nós da Home: botões (ActivateWindow 10025) e linhas (<content>)."""
    texto = path.read_text(encoding='utf-8')
    texto = texto.replace('&amp;', '&')
    botoes, linhas = {}, {}
    for match in re.finditer(r'<control type="button" id="(\d+)">(.*?)</control>', texto, re.S):
        cid, bloco = match.group(1), match.group(2)
        alvo = re.search(r'ActivateWindow\(10025,\s*"([^"]+)"', bloco)
        if not alvo:
            continue
        label = re.search(r'<label>(.*?)</label>', bloco)
        botoes[cid] = {'label': label.group(1) if label else cid, 'url': alvo.group(1)}
    for match in re.finditer(r'<control type="list" id="(92\d\d)">(.*?)</control>\n', texto, re.S):
        cid, bloco = match.group(1), match.group(2)
        alvo = re.search(r'<content[^>]*>(plugin://[^<]+)</content>', bloco)
        if not alvo:
            continue
        labels = [l for l in re.findall(r'<label>(.*?)</label>', bloco) if '$INFO[' not in l]
        linhas[cid] = {'label': labels[0] if labels else cid, 'url': alvo.group(1)}
    return botoes, linhas


def run_route(profile, url, timeout=420):
    """Executa o add-on real com os parâmetros que a skin passa."""
    query = url.split('?', 1)[1] if '?' in url else ''
    proc = subprocess.run([sys.executable, str(RUNNER), str(profile), query],
                          capture_output=True, text=True, timeout=timeout)
    try:
        data = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {'count': 0, 'items': [], 'error': 'sem saída JSON: %s' % proc.stderr[-300:]}
    data['error'] = data.get('error') or (None if proc.returncode == 0 else 'exit %d' % proc.returncode)
    return data


def run_boot(profile, xbmc_dir, timeout=900):
    env = dict(os.environ)
    env['SMARTED_STUB_HOME'] = str(profile)
    env['SMARTED_STUB_XBMC'] = str(xbmc_dir)
    proc = subprocess.run([sys.executable, str(BOOT_RUNNER), str(profile)],
                          capture_output=True, text=True, timeout=timeout, env=env)
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {'error': 'sem saída JSON: %s' % proc.stderr[-300:]}


def check_pass(number, stage, workdir, deep):
    profile_src = stage / 'assets' / 'smarted' / 'profile'
    xbmc_src = stage / 'assets'
    base = workdir / ('pass-%d' % number)
    clone(profile_src, base / 'profile')
    pristino = stage / '.pristine-userdata'
    if pristino.is_dir():
        for arquivo in pristino.iterdir():
            if arquivo.is_file():
                shutil.copy2(arquivo, base / 'profile' / 'userdata' / arquivo.name)
    xbmc_dir = base / 'xbmc'
    if xbmc_dir.exists():
        shutil.rmtree(xbmc_dir)
    xbmc_dir.mkdir(parents=True)
    (xbmc_dir / 'addons').mkdir()
    # addons de sistema que já vêm no APK (o resto é grande: copiamos só o que importa)
    origem = xbmc_src / 'addons'
    if origem.is_dir():
        for item in origem.iterdir():
            if item.is_dir():
                shutil.copytree(item, xbmc_dir / 'addons' / item.name, copy_function=os.link)
    install_skin(xbmc_dir)

    resultado = {'pass': number, 'checks': [], 'routes': {}}

    gui_antes = (base / 'profile' / 'userdata' / 'guisettings.xml').read_text(encoding='utf-8')

    def check(nome, ok, detalhe=''):
        resultado['checks'].append({'nome': nome, 'ok': bool(ok), 'detalhe': detalhe})
        return ok

    boot = run_boot(base / 'profile', xbmc_dir)
    resultado['boot'] = {k: v for k, v in boot.items() if k not in ('xbmc_log', 'jsonrpc')}
    check('bootstrap sem exceção', boot.get('error') is None, str(boot.get('error')))
    check('ponto de partida: skin.estuary (semeada pelo APK)',
          'skin.estuary' in gui_antes, 'guisettings inicial sem skin.estuary')
    check('reparo do Brazuca Play ok', boot.get('repair_ok'), str(boot.get('required')))
    check('100% dos atalhos gravados', boot.get('favourites_total') == 10,
          'total=%s' % boot.get('favourites_total'))
    check('skin SMARTEDTV ativa', (boot.get('skin') or {}).get('skin') == SKIN_ID,
          json.dumps(boot.get('skin')))
    skin = boot.get('skin') or {}
    check('skin aplicada de fato', skin.get('installed') and skin.get('skin') == SKIN_ID,
          'installed=%s changed=%s' % (skin.get('installed'), skin.get('changed')))
    nodes = boot.get('home_nodes') or {}
    check('nós da Home ligados às rotas', nodes.get('ok'), json.dumps(nodes.get('missing_home')))

    gui = (base / 'profile' / 'userdata' / 'guisettings.xml').read_text(encoding='utf-8')
    check('guisettings aponta para skin.novatv',
          bool(re.search(r'<setting id="lookandfeel.skin"[^>]*>skin\.novatv</setting>', gui)))

    fav = base / 'profile' / 'userdata' / 'favourites.xml'
    fav_text = fav.read_text(encoding='utf-8') if fav.is_file() else ''
    entradas = len(ET.fromstring(fav_text)) if fav_text.strip() else 0
    check('favourites.xml com 10 atalhos', entradas == 10, 'total=%d' % entradas)
    for rotulo, rota in (('TV ao vivo', 'mode=21'), ('Filmes', 'mode=27'), ('Séries', 'mode=27')):
        check('atalho %s aponta para %s' % (rotulo, rota), rota in fav_text)

    home = home_xml(xbmc_dir)
    if not check('Home.xml da skin encontrado', home is not None):
        return resultado
    botoes, linhas = routes_from_home(home)
    check('Home tem os 4 botões da barra + nós', len(botoes) >= 4, 'botões=%s' % sorted(botoes))
    check('Home tem as 3 linhas de conteúdo', set(linhas) >= {'9200', '9201', '9202'},
          'linhas=%s' % sorted(linhas))

    obrigatorios = {'9200': '#menu_canais', '9201': '#filmes_menu', '9202': '#series_menu'}
    for cid, marcador in obrigatorios.items():
        linha = linhas.get(cid)
        if not linha:
            check('linha %s existe' % cid, False)
            continue
        alvo_url = unquote(linha['url'])
        check('linha %s usa a rota %s' % (cid, marcador), marcador in alvo_url, alvo_url[:90])

    # --- execução real do add-on para os nós que importam ---
    alvos = dict(linhas)
    if deep:
        alvos.update({'btn-%s' % cid: dado for cid, dado in botoes.items()})
    else:
        for cid in ('9010', '9011', '9012', '9022'):
            if cid in botoes:
                alvos['btn-%s' % cid] = botoes[cid]

    vistos, finais = set(), {}
    for nome, dado in alvos.items():
        if not dado['url'].startswith('plugin://%s/' % PLUGIN_ID):
            resultado['routes'][nome] = {'label': dado['label'], 'url': dado['url'],
                                        'count': 0, 'error': None, 'skipped': 'não é rota do Brazuca'}
            continue
        if dado['url'] in vistos:
            resultado['routes'][nome] = {'label': dado['label'], 'url': dado['url'],
                                        'count': 0, 'error': None,
                                        'skipped': 'mesma rota de outro botão'}
            continue
        vistos.add(dado['url'])
        finais[nome] = dado

    for nome, dado in finais.items():
        info = run_route(base / 'profile', dado['url'])
        resultado['routes'][nome] = {
            'label': dado['label'], 'url': dado['url'],
            'count': info.get('count', 0), 'error': info.get('error'),
            'sample': [item['label'] for item in info.get('items', [])[:3]],
        }
        check('%s (%s) devolve itens do addon' % (nome, dado['label'][:26]),
              info.get('count', 0) > 0 and not info.get('error'),
              'itens=%s erro=%s' % (info.get('count', 0), info.get('error')))

    resultado['ok'] = all(c['ok'] for c in resultado['checks'])
    return resultado


def write_report(resultados, dest):
    linhas = ['# Simulação de primeiro boot — validação da Home (SMARTEDTV)', '',
              'Executado por `tools/kodi/simulate-first-boot.py`. '
              'Cada passagem monta o perfil semeado do APK base, roda o bootstrap real '
              '(repair, favoritos, performance, skin/nós), instala a skin do repositório '
              'como add-on de sistema e executa **o add-on real** para cada nó da Home.',
              '', '## Resultado por passagem', '',
              '| Passagem | Checks | Falhas | Resultado |', '|---|---|---|---|']
    for r in resultados:
        falhas = [c['nome'] for c in r['checks'] if not c['ok']]
        linhas.append('| %d | %d | %d | %s |' % (
            r['pass'], len(r['checks']), len(falhas),
            'OK' if not falhas else 'FALHOU: ' + '; '.join(falhas)))
    linhas += ['', '## Rotas executadas (última passagem)', '',
               '| Nó | Item da skin | Rota | Itens | Amostra |', '|---|---|---|---|---|']
    ultima = resultados[-1]
    for nome, dado in sorted(ultima.get('routes', {}).items()):
        amostra = ', '.join(re.sub(r'\[/?[^\]]+\]', '', s)[:24] for s in dado.get('sample', []))
        nota = dado.get('skipped') or amostra
        linhas.append('| %s | %s | `%s` | %d | %s |' % (
            nome, dado['label'][:30], dado['url'][:72], dado['count'], nota))
    linhas += ['', '## Checks por passagem', '']
    for r in resultados:
        linhas.append('### Passagem %d' % r['pass'])
        for c in r['checks']:
            linhas.append('- [%s] %s%s' % ('OK' if c['ok'] else 'FALHA', c['nome'],
                                           (' — ' + c['detalhe']) if c['detalhe'] else ''))
        linhas.append('')
    linhas += ['## Limite do ambiente', '',
               'Este sandbox não tem KVM, `adb`, `emulator`, `java` nem acesso ao repositório '
               'do SDK Android (`dl.google.com`), então um AVD real não pode ser iniciado aqui. '
               'A simulação acima usa o **perfil semeado real**, a **skin real do repositório** '
               'e o **add-on real instalado no perfil**, com os mesmos parâmetros que a skin '
               'passa ao Kodi — é o mais próximo de um emulador que o ambiente permite.']
    Path(dest).write_text('\n'.join(linhas) + '\n', encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--passes', type=int, default=3)
    parser.add_argument('--base', type=Path, default=DEFAULT_BASE)
    parser.add_argument('--workdir', type=Path, default=Path('/tmp/sim-smarted'))
    parser.add_argument('--deep', action='store_true',
                        help='executa também todos os botões da Home na primeira passagem')
    parser.add_argument('--report', type=Path,
                        default=ROOT / 'docs' / 'simulacao-primeiro-boot.md')
    args = parser.parse_args(argv)

    if not args.base.is_file():
        print('APK base ausente: %s' % args.base)
        return 2
    stage = args.workdir / 'stage'
    args.workdir.mkdir(parents=True, exist_ok=True)
    print('extraindo perfil semeado de %s ...' % args.base.name)
    stage_base(args.base, stage)

    resultados = []
    for numero in range(1, args.passes + 1):
        print('\n=== passagem %d/%d ===' % (numero, args.passes))
        resultado = check_pass(numero, stage, args.workdir, deep=args.deep and numero == 1)
        resultados.append(resultado)
        for c in resultado['checks']:
            print('  [%s] %s%s' % ('OK' if c['ok'] else 'FALHA', c['nome'],
                                   (' — ' + c['detalhe']) if (c['detalhe'] and not c['ok']) else ''))
        print('  => %s' % ('OK' if resultado.get('ok') else 'FALHOU'))

    write_report(resultados, args.report)
    print('\nrelatório: %s' % args.report)
    sucesso = all(r.get('ok') for r in resultados)
    print('RESULTADO FINAL: %s' % ('TODAS AS PASSAGENS OK' if sucesso else 'HÁ FALHAS'))
    return 0 if sucesso else 1


if __name__ == '__main__':
    sys.exit(main())
