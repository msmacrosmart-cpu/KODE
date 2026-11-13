#!/usr/bin/env python3
"""Baixa o Vikings Repo e prepara o add-on de repositorio para o build.

O que ele faz, em ordem:

1. tenta baixar o zip oficial do repositorio (``repository.vikings.zip``) numa
   lista de URLs candidatas (a primeira que responder vale);
2. confere que o zip tem **um** add-on ``repository.*`` no topo e que o
   ``addon.xml`` declara o mesmo id da pasta;
3. extrai esse add-on para ``DEST/repository.vikings`` — o
   ``build-release-apk.py`` recolhe essa pasta em ``assets/addons/`` e registra
   no ``addon-manifest.xml``, ou seja, o Kodi instala e ativa o repositorio no
   primeiro boot, sem nenhuma acao do usuario;
4. guarda o zip original em ``DEST/_payload/repository.vikings.zip`` para o
   ``service.smarted.bootstrap`` (reparo pos-instalacao, sem rede);
5. opcionalmente extrai tambem o add-on de video
   ``plugin.video.BrazucaPlay.Matrix`` do mesmo repositorio (``--plugin``), para
   o caso do perfil semeado nao trazer o pacote.

Nada disso e inventado: se o zip nao vier, o script escreve o motivo em
``DEST/vikings-report.txt`` e sai com codigo 1 só quando ``--strict`` é usado.

Uso:
    python3 tools/kodi/fetch-vikings-repo.py /tmp/extra [--strict] [--url URL]
"""
from __future__ import annotations

import argparse
import io
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

# Ordem de tentativa. A primeira que devolver um zip valido e usada.
#
# O endereco divulgado (vkodi.net) sai do ar de tempos em tempos — foi o que
# aconteceu em dez/2025 e de novo agora. O repositorio oficial do time Vikings
# tambem vive no GitHub (repo ``vikingsbuild/vikings.repo``), e o add-on de
# repositorio ``vkkodi.repo`` e o que aponta para a arvore ``matrix`` usada pelo
# Kodi 19+/21. Por isso o GitHub vem primeiro: e estavel, versionado e o build
# nao depende de um dominio de terceiro fora do ar.
VIKINGS_GITHUB = ('https://github.com/vikingsbuild/vikings.repo/raw/master/'
                  'vkkodi.repo/vkkodi.repo-3.00.zip')
URLS_PADRAO = (
    VIKINGS_GITHUB,
    'https://vkodi.net/repo/repository.vikings.zip',
    'https://vkodi.net/repo/zips/repository.vikings/repository.vikings.zip',
    'http://vkodi.net/repo/repository.vikings.zip',
)
URL_PLUGIN = ('https://github.com/vikingskoditeam/vikingskoditeam.github.io/raw/'
              'master/matrix/plugin.video.BrazucaPlay.Matrix/')
ADDON_VIDEO = 'plugin.video.BrazucaPlay.Matrix'
TENTATIVAS = 3
TIMEOUT = 30
UA = {'User-Agent': 'SMARTEDTV build/1.0 (+reempacotamento)'}


def baixar(url: str, tentativas: int = TENTATIVAS) -> bytes | None:
    for tentativa in range(1, tentativas + 1):
        try:
            pedido = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(pedido, timeout=TIMEOUT) as resposta:
                dados = resposta.read(32 * 1024 * 1024)
            if dados[:2] == b'PK':
                return dados
            print('  %s: resposta nao e um zip (%d bytes)' % (url, len(dados)))
            return None
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as erro:
            print('  %s: tentativa %d/%d falhou (%s)' % (url, tentativa, tentativas, erro))
            if tentativa < tentativas:
                time.sleep(2 * tentativa)
    return None


def abrir_addon_repositorio(dados: bytes) -> tuple[str, dict[str, bytes]]:
    """Valida o zip e devolve (addon_id, {caminho_relativo: bytes})."""
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        nomes = [n for n in z.namelist() if not n.endswith('/')]
        if not nomes:
            raise SystemExit('zip do repositorio vazio')
        xmls = [n for n in nomes if n.endswith('addon.xml') and n.count('/') == 1]
        if len(xmls) != 1:
            raise SystemExit('zip nao tem exatamente um addon.xml na raiz: %s' % xmls[:5])
        raiz = xmls[0].split('/', 1)[0]
        bruto = z.read(xmls[0])
        addon = ET.fromstring(bruto)
        addon_id = addon.get('id') or ''
        if not (addon_id.startswith('repository.') or addon_id.endswith('.repo')):
            raise SystemExit('addon do zip nao e um repositorio: %s' % addon_id)
        if addon_id != raiz:
            raise SystemExit('pasta %s nao combina com o id %s' % (raiz, addon_id))
        arquivos = {}
        for nome in nomes:
            if not nome.startswith(raiz + '/'):
                continue
            relativo = nome[len(raiz) + 1:]
            if not relativo or relativo.startswith('/') or '..' in relativo.split('/'):
                raise SystemExit('caminho inseguro no zip: %s' % nome)
            arquivos[relativo] = z.read(nome)
        if 'addon.xml' not in arquivos:
            raise SystemExit('addon.xml ausente apos extracao')
        return addon_id, arquivos


def extrair(destino: Path, addon_id: str, arquivos: dict[str, bytes]) -> Path:
    alvo = destino / addon_id
    if alvo.exists():
        shutil.rmtree(alvo)
    for relativo, dados in arquivos.items():
        caminho = alvo / relativo
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(dados)
    return alvo


def versao(texto: str) -> list[int]:
    import re
    return [int(p) for p in re.split(r'[^0-9]+', texto or '') if p]


ADDONS_XML = ('https://github.com/vikingskoditeam/vikingskoditeam.github.io/raw/'
              'master/matrix/addons.xml')


def versao_do_plugin() -> str:
    """Le o addons.xml do repositorio e devolve a versao publicada do add-on."""
    try:
        pedido = urllib.request.Request(ADDONS_XML, headers=UA)
        with urllib.request.urlopen(pedido, timeout=TIMEOUT) as resposta:
            bruto = resposta.read(8 * 1024 * 1024)
        raiz = ET.fromstring(bruto)
    except Exception as erro:  # noqa: BLE001 - opcional, so relata
        print('  addons.xml do repositorio indisponivel (%s)' % erro)
        return ''
    for addon in raiz.iter('addon'):
        if addon.get('id') == ADDON_VIDEO:
            return addon.get('version') or ''
    return ''


def baixar_plugin(destino: Path, report: list[str]) -> str:
    """Baixa o zip do add-on de video que o repositorio publica (opcional).

    Guarda com o nome que o ``repair.py`` sabe procurar na pasta de pacotes:
    ``plugin.video.BrazucaPlay.Matrix-<versao>.zip``.
    """
    versao = versao_do_plugin()
    if not versao:
        report.append('plugin: versao nao encontrada no addons.xml do repositorio')
        return ''
    nome = '%s-%s.zip' % (ADDON_VIDEO, versao)
    dados = baixar(URL_PLUGIN + nome)
    if not dados:
        report.append('plugin: falha ao baixar %s' % (URL_PLUGIN + nome))
        return ''
    alvo = destino / nome
    alvo.parent.mkdir(parents=True, exist_ok=True)
    alvo.write_bytes(dados)
    report.append('plugin: %s (%d bytes) de %s' % (nome, len(dados), URL_PLUGIN + nome))
    return nome


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('destino', type=Path, help='pasta de addons extras do build')
    p.add_argument('--strict', action='store_true',
                   help='falha o build quando o repositorio nao puder ser baixado')
    p.add_argument('--url', action='append', default=[],
                   help='URL candidata do zip (pode repetir; tem prioridade)')
    p.add_argument('--plugin', action='store_true',
                   help='baixa tambem o zip do add-on de video do repositorio')
    args = p.parse_args(argv)

    destino = args.destino.resolve()
    destino.mkdir(parents=True, exist_ok=True)
    urls = list(args.url) or ([os.environ['VIKINGS_REPO_ZIP']] if os.environ.get('VIKINGS_REPO_ZIP') else [])
    urls += list(URLS_PADRAO)

    report: list[str] = []
    dados = None
    usado = ''
    for url in urls:
        print('tentando %s' % url)
        candidato = baixar(url)
        if candidato:
            dados, usado = candidato, url
            break

    if dados is None:
        report.append('repositorio: NAO foi possivel baixar o Vikings Repo')
        report.append('urls tentadas: ' + ', '.join(urls))
        if args.plugin:
            escolhido = baixar_plugin(destino / '_payload', report)
            report.append('plugin: %s' % (escolhido or 'nao baixado'))
        (destino / 'vikings-report.txt').write_text('\n'.join(report) + '\n', encoding='utf-8')
        print('\n'.join(report))
        return 1 if args.strict else 0

    addon_id, arquivos = abrir_addon_repositorio(dados)
    pasta = extrair(destino, addon_id, arquivos)
    info = ET.parse(pasta / 'addon.xml').getroot()
    report.append('repositorio: %s %s (%d arquivos, %.1f KB) de %s'
                  % (addon_id, info.get('version'), len(arquivos),
                     sum(len(v) for v in arquivos.values()) / 1024.0, usado))
    for ponto in info.iter('extension'):
        if ponto.get('point') == 'xbmc.addon.repository':
            for campo in ponto.iter():
                if campo.text and campo.text.strip().startswith('http'):
                    report.append('  fonte %s: %s' % (campo.tag, campo.text.strip()))
    payload = destino / '_payload'
    payload.mkdir(parents=True, exist_ok=True)
    (payload / (addon_id + '.zip')).write_bytes(dados)
    report.append('zip guardado em %s' % (payload / (addon_id + '.zip')))

    if args.plugin:
        escolhido = baixar_plugin(destino / '_payload', report)
        report.append('plugin: %s' % (escolhido or 'nao baixado'))

    (destino / 'vikings-report.txt').write_text('\n'.join(report) + '\n', encoding='utf-8')
    print('\n'.join(report))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
