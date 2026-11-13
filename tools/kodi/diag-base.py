#!/usr/bin/env python3
"""Diagnóstico de um APK base antes do reempacotamento.

Imprime só o que o repack-skins.py precisa e que pode divergir entre um APK
sintético e o compilado de verdade: manifesto binário, cores das skins e
presença do userdata inicial.
"""
import struct
import sys
import zipfile
from pathlib import Path

apk = Path(sys.argv[1])
with zipfile.ZipFile(apk) as z:
    nomes = z.namelist()
    print(f"entradas: {len(nomes)}")
    print(f"tamanho:  {apk.stat().st_size} bytes")
    print(f"integridade: {'ok' if z.testzip() is None else 'CORROMPIDO'}")

    for obrigatorio in ("AndroidManifest.xml", "assets/system/addon-manifest.xml"):
        print(f"{obrigatorio}: {'presente' if obrigatorio in nomes else 'AUSENTE'}")

    cores = [n for n in nomes if n.endswith("colors/defaults.xml")]
    print(f"colors/defaults.xml: {cores}")

    gui = [n for n in nomes if n.endswith("guisettings.xml")]
    print(f"guisettings.xml: {gui or 'nenhum'}")

    if "AndroidManifest.xml" in nomes:
        man = z.read("AndroidManifest.xml")
        v = "21.4-Omega".encode("utf-16le")
        c = struct.pack("<I", 2104000)
        print(f"  versionName 21.4.0: {man.count(v)} ocorrência(s)")
        print(f"  versionCode 2104000: {man.count(c)} ocorrência(s)")
        # se a versão não estiver literalmente no manifesto, o build anterior
        # não gravou o versionName como string do pool
        # Onde o versionName realmente mora? O Gradle referencia
        # @string/xbmc_version; o texto pode estar em resources.arsc ou em
        # res/values/strings.xml compilado.
        achados_arsc = 0
        if "resources.arsc" in nomes:
            arsc = z.read("resources.arsc")
            achados_arsc = arsc.count(v) + arsc.count(b"21.4.0")
            print(f"  versionName no resources.arsc: {achados_arsc} ocorrência(s) "
                  f"({len(arsc)} bytes)")
        em_res = []
        for nome in nomes:
            if nome.startswith("res/") and nome.endswith(".xml"):
                dados = z.read(nome)
                if dados.count(v) or dados.count(b"21.4.0"):
                    em_res.append(nome)
        print(f"  versionName em res/*.xml: {em_res[:5] or 'nenhum'}")

        if man.count(v) != 1:
            achados = [t.decode("utf-16-le", "ignore") for t in
                       __import__("re").findall(rb"(?:[\x20-\x7e]\x00){4,}", man)]
            print(f"  strings do manifesto: {achados[:20]}")
