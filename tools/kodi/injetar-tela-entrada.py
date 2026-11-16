#!/usr/bin/env python3
"""Injeta SOMENTE a tela inicial do ZIP num APK SMARTEDTV ja existente.

Nao troca skin, nao muda versao, nao recompila nada e nao altera nenhum outro
arquivo: todas as entradas do APK original sao copiadas como estao (exceto as
assinaturas META-INF, que sao refeitas depois), e sao acrescentados apenas:

* ``assets/addons/script.smartedtv.welcome/`` (os 15 arquivos do ZIP);
* uma linha no ``assets/system/addon-manifest.xml``;
* o gancho de inicializacao dentro do ``service.smarted.bootstrap/service.py``
  que JA existe no APK (nenhuma funcao nova de negocio e criada).

O perfil semeado ``assets/smarted/profile/`` e intocado: o dex confere o SHA-256
de cada arquivo dele contra o profile-manifest, e qualquer alteracao ali
impediria o boot.

Uso:
    python3 tools/kodi/injetar-tela-entrada.py --apk ATUAL.apk --saida BRUTO.apk
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDON_DIR = ROOT / "kodi" / "addons" / "script.smartedtv.welcome"
ADDON_ID = ADDON_DIR.name
ADDON_PREFIX = "assets/addons/%s/" % ADDON_ID
BOOTSTRAP = "assets/addons/service.smarted.bootstrap/service.py"
MANIFEST = "assets/system/addon-manifest.xml"
PROFILE_PREFIX = "assets/smarted/profile/"
SIG = re.compile(r"^META-INF/(?:MANIFEST\.MF|[^/]+\.(?:SF|RSA|DSA|EC))$", re.I)

# Espelho do gancho que ja esta integrado em
# kodi/addons/service.smarted.bootstrap/service.py neste branch. Reaproveita as
# funcoes existentes no servico (log/jsonrpc/enable_addons) e o builtin RunScript.
HOOK_DEFS = '''# --- Tela de entrada entregue no ZIP (integracao, sem recriar interface) ---
WELCOME_ADDON = 'script.smartedtv.welcome'
WELCOME_TENTATIVAS = 6
WELCOME_ESPERA = 1


def abrir_tela_entrada(monitor):
    """Abre a tela do ZIP uma unica vez por inicializacao, sem substituir a Home."""
    instalado = False
    for tentativa in range(WELCOME_TENTATIVAS):
        if monitor.abortRequested():
            return
        enable_addons([WELCOME_ADDON])
        instalado = bool(xbmc.getCondVisibility('System.HasAddon(%s)' % WELCOME_ADDON))
        if instalado:
            break
        xbmc.executebuiltin('UpdateLocalAddons()')
        if monitor.waitForAbort(WELCOME_ESPERA):
            return
    if not instalado:
        log('tela de entrada indisponivel: addon %s nao encontrado' % WELCOME_ADDON,
            xbmc.LOGWARNING)
        return
    for tentativa in range(WELCOME_TENTATIVAS):
        if monitor.abortRequested():
            return
        if xbmc.getCondVisibility('Window.IsActive(10000)'):
            break
        if monitor.waitForAbort(WELCOME_ESPERA):
            return
    xbmc.executebuiltin('RunScript(%s)' % WELCOME_ADDON)
    log('tela de entrada aberta: %s' % WELCOME_ADDON)
'''

HOOK_CALL = '''    entrada = threading.Thread(target=abrir_tela_entrada, args=(monitor,),
                               name='welcome-entry')
    entrada.daemon = True
    entrada.start()
'''


def arquivos_do_addon():
    arquivos = {}
    for caminho in sorted(ADDON_DIR.rglob("*")):
        if not caminho.is_file() or "__pycache__" in caminho.parts or caminho.suffix == ".pyc":
            continue
        arquivos[ADDON_PREFIX + caminho.relative_to(ADDON_DIR).as_posix()] = caminho.read_bytes()
    if len(arquivos) != 15:
        raise SystemExit("addon da tela incompleto: %d arquivos (esperado 15)" % len(arquivos))
    return arquivos


def patch_service(dados: bytes) -> bytes:
    texto = dados.decode("utf-8")
    if "def abrir_tela_entrada(" in texto:
        raise SystemExit("service.py do APK ja tem o gancho da tela de entrada")
    ancora_main = "def main():\n    monitor = xbmc.Monitor()\n"
    ancora_fim = "if __name__ == '__main__':"
    if texto.count(ancora_main) != 1 or texto.count(ancora_fim) != 1:
        raise SystemExit("anchors do main()/__main__ nao encontrados no service.py do APK")
    if not re.search(r"^import threading$", texto, re.M) or "def enable_addons(" not in texto:
        raise SystemExit("service.py do APK nao tem threading/enable_addons")
    texto = texto.replace(ancora_main, ancora_main + "\n" + HOOK_CALL + "\n", 1)
    texto = texto.replace(ancora_fim, HOOK_DEFS + "\n\n" + ancora_fim, 1)
    compile(texto, BOOTSTRAP, "exec")  # nunca entregar Python quebrado
    return texto.encode("utf-8")


def patch_manifest(dados: bytes) -> bytes:
    texto = dados.decode("utf-8")
    if ">%s<" % ADDON_ID in texto:
        raise SystemExit("addon ja registrado no addon-manifest.xml")
    if texto.count("</addons>") != 1:
        raise SystemExit("formato inesperado do addon-manifest.xml")
    novo = texto.replace(
        "</addons>",
        '  <addon optional="true">%s</addon>\n</addons>' % ADDON_ID, 1)
    ET.fromstring(novo)
    return novo.encode("utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", required=True, type=Path, help="APK atual (integro)")
    parser.add_argument("--saida", required=True, type=Path, help="APK com a tela injetada, sem assinar")
    args = parser.parse_args(argv)
    if args.apk.resolve() == args.saida.resolve():
        raise SystemExit("entrada e saida precisam ser diferentes")
    extras = arquivos_do_addon()

    with zipfile.ZipFile(args.apk) as origem, \
            zipfile.ZipFile(args.saida, "w", allowZip64=True) as destino:
        nomes = set()
        perfil = {}
        for item in origem.infolist():
            if item.is_dir() or SIG.fullmatch(item.filename):
                continue
            if item.filename in nomes:
                raise SystemExit("entrada duplicada no APK: %s" % item.filename)
            nomes.add(item.filename)
            dados = origem.read(item)
            if item.filename.startswith(PROFILE_PREFIX):
                perfil[item.filename] = hashlib.sha256(dados).hexdigest()
            if item.filename == BOOTSTRAP:
                dados = patch_service(dados)
                print("  service.py: gancho da tela de entrada injetado")
            elif item.filename == MANIFEST:
                dados = patch_manifest(dados)
                print("  addon-manifest.xml: %s registrado" % ADDON_ID)
            info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
            info.compress_type = item.compress_type
            info.external_attr = item.external_attr
            info.comment = item.comment
            destino.writestr(info, dados)

        if BOOTSTRAP not in nomes:
            raise SystemExit("APK atual sem %s - ponto de entrada nao localizado" % BOOTSTRAP)
        if MANIFEST not in nomes:
            raise SystemExit("APK atual sem %s" % MANIFEST)
        if not perfil:
            raise SystemExit("APK atual sem perfil semeado (assets/smarted/profile/)")

        for nome, dados in extras.items():
            if nome in nomes:
                raise SystemExit("addon ja presente no APK: %s" % nome)
            info = zipfile.ZipInfo(nome, date_time=(2026, 11, 16, 13, 44, 0))
            # sem compressao, como os demais addons de sistema do APK: o Kodi
            # le assets/addons direto do APK e align-apk.py realinha entradas
            # stored a 4 bytes antes da assinatura.
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o644 << 16
            destino.writestr(info, dados)

    # o perfil semeado precisa sair byte a byte identico (dex verifica hashes)
    with zipfile.ZipFile(args.saida) as conferido:
        for nome, resumo in perfil.items():
            if hashlib.sha256(conferido.read(nome)).hexdigest() != resumo:
                raise SystemExit("perfil semeado alterado: %s" % nome)
        for nome in extras:
            if nome not in conferido.namelist():
                raise SystemExit("arquivo da tela ausente: %s" % nome)

    print("APK com a tela: %s (%d entradas, %d arquivos novos, perfil intacto)"
          % (args.saida, len(nomes) + len(extras), len(extras)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
