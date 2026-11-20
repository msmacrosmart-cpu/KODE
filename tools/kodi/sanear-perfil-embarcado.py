#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tira do perfil EMBARCADO os addons de terceiros e revalida o pin do dex.

POR QUE ISTO EXISTE (medido no emulador de projetor, APK 1.0.141)
-----------------------------------------------------------------
Mesmo com a limpeza no aparelho funcionando (11 addons retirados, "perfil limpo
(rodada 1): restantes=nenhum"), o `kodi.log` do projetor continuava mostrando:

    [COLOR limegreen][B]Open[/B][/COLOR]Wizard: [First Run] Skipping Save Data
    [plugin.video.youtube] ModuleNotFoundError: youtube_plugin.kodion.exceptions

O Kodi inicia os addons de SERVICO de todos os addons instalados durante
`CServiceManager::InitStageTwo`, ANTES de qualquer Python do app rodar (a
limpeza só acontece ~12 s depois). Ou seja: limpar depois é tarde - o erro na
tela já apareceu. A origem é o perfil que o APK instala no primeiro arranque,
que traz `plugin.video.youtube`, `plugin.program.openwizard`,
`plugin.audio.mp3streams`, `service.subtitles.legendei` e cinco repositórios de
terceiros (herança da base do Brazuca Play).

O QUE ESTE SCRIPT FAZ
---------------------
1. tira esses addons de `assets/smarted/profile/addons/`;
2. refaz `assets/smarted/profile-manifest.txt` (formato sha256\\tbytes\\tcaminho);
3. troca, NO DEX, o pin de 64 hex que o `ProfileDirectorySeed` confere.

O passo 3 é obrigatório: sem ele o dex recusa instalar o perfil ("Perfil
existente preservado") e a Home fica sem dados - o outro defeito relatado. O pin
é uma string ASCII de 64 bytes no dex; trocar 64 caracteres por 64 caracteres
não muda offset nem tamanho de nada, por isso a troca por byte é segura. O
script FALHA se o pin antigo não aparecer exatamente uma vez (dex recompilado,
string comprimida etc.), para nunca entregar um APK que recusa o próprio perfil.
"""
from __future__ import print_function

import hashlib
import io
import struct
import zlib
import os
import re
import sys
import zipfile

PERFIL = 'assets/smarted/profile/'
# fica AO LADO da pasta, nao dentro: assets/smarted/profile-manifest.txt
MANIFESTO = 'assets/smarted/profile-manifest.txt'
# O pin vive no codigo Java do bootstrap (que vai para o dex). Ele e a fonte da
# verdade: o script le daqui, confere no dex e grava o novo valor de volta.
ORIGEM_DO_PIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'android', 'src', 'org', 'smartedtv', 'bootstrap',
                             'ProfileDirectoryBootstrap.java')
PIN_ANTIGO = '1447de816a44ecc11c42c2c315cf20e61c9baa037e914a13293711cf152d1ede'
_HEX64 = re.compile(r'\b[0-9a-f]{64}\b')


def pin_publicado(origem=None):
    """Pin de 64 hex que o dex confere (lido do codigo Java)."""
    caminho = origem or ORIGEM_DO_PIN
    try:
        with io.open(caminho, encoding='utf-8') as arquivo:
            achados = _HEX64.findall(arquivo.read())
    except IOError:
        return PIN_ANTIGO
    return achados[0] if achados else PIN_ANTIGO


def gravar_pin_na_origem(pin_novo, origem=None):
    """Mantem o Java igual ao dex (senao a proxima compilacao volta o pin velho)."""
    caminho = origem or ORIGEM_DO_PIN
    antigo = pin_publicado(caminho)
    if antigo == pin_novo:
        return False
    with io.open(caminho, encoding='utf-8') as arquivo:
        texto = arquivo.read()
    if antigo not in texto:
        raise SystemExit('pin %s nao esta em %s' % (antigo, caminho))
    with io.open(caminho, 'w', encoding='utf-8') as arquivo:
        arquivo.write(texto.replace(antigo, pin_novo))
    return True

# Addons de terceiros que vieram no perfil embarcado (evidência: kodi.log do
# projetor e Addons33.db do perfil). Nenhum é usado pelo app.
ADDONS_DE_TERCEIROS = (
    'plugin.video.youtube',
    'plugin.program.openwizard',
    'plugin.program.openwizard2',
    'plugin.video.openwizard',
    'plugin.audio.mp3streams',
    'service.subtitles.legendei',
    'plugin.program.super.favourites',
    'script.module.bingie',
    'skin.bingie',
    'repository.alado.tv',
    'repository.elementumorg',
    'repository.nostr-oneplay',
    'repository.redwizard',
    'repository.openwizard',
    'repository.streamxtv.matrix',
    'repository.resolveurl',
    'vkkodi.repo',
    'One.repo',
)

# Addons que o motor do Kodi exige: NUNCA saem (sem eles o CAddonMgr não inicia).
PROTEGIDOS = (
    'audioencoder.kodi.builtin.',
    'screensaver.xbmc.builtin.',
    'kodi.binary.',
    'kodi.resource',
    'xbmc.',
    'game.controller.',
    'metadata.',
    'resource.',
    'webinterface.',
    'vfs.',
    'inputstream.',
    'skin.',
    'script.module.',
    'repository.xbmc.org',
    'plugin.video.BrazucaPlay.Matrix',
    'plugin.video.smarted',
    'script.smartedtv.',
    'service.smarted.',
)


def addons_do_perfil(nomes):
    achados = set()
    for nome in nomes:
        if not nome.startswith(PERFIL + 'addons/'):
            continue
        partes = nome[len(PERFIL):].split('/')
        if len(partes) > 2 and partes[1]:
            achados.add(partes[1])
    return achados


def protegido(addon):
    return any(addon == p or addon.startswith(p) for p in PROTEGIDOS)


def planejar(apk):
    """(arquivos_a_remover, addons_removidos, addons_mantidos)."""
    with zipfile.ZipFile(apk) as z:
        nomes = set(z.namelist())
    if MANIFESTO not in nomes:
        raise SystemExit('APK sem perfil embarcado (%s)' % MANIFESTO)
    addons = addons_do_perfil(nomes)
    remover_addons = set(a for a in addons
                         if a in ADDONS_DE_TERCEIROS and not protegido(a))
    arquivos = set()
    for nome in nomes:
        if not nome.startswith(PERFIL + 'addons/'):
            continue
        partes = nome[len(PERFIL):].split('/')
        if len(partes) > 1 and partes[1] in remover_addons:
            arquivos.add(nome)
    return arquivos, remover_addons, sorted(addons - remover_addons)


def manifesto_de(z, nomes_restantes):
    linhas = []
    for nome in sorted(nomes_restantes):
        if not nome.startswith(PERFIL) or nome == MANIFESTO:
            continue
        dados = z.read(nome)
        caminho = nome[len(PERFIL):]
        if not caminho:
            continue
        linhas.append('%s\t%d\t%s' % (hashlib.sha256(dados).hexdigest(),
                                      len(dados), caminho))
    return ('\n'.join(linhas) + '\n').encode('utf-8')


def consertar_cabecalho_do_dex(dados):
    """Recalcula assinatura (SHA-1) e checksum (Adler-32) do cabecalho do dex.

    O dex tem, nos bytes 8..12, o Adler-32 de tudo a partir do byte 12, e nos
    bytes 12..32 o SHA-1 de tudo a partir do byte 32. Trocar o pin sem refazer
    os dois deixa o dex invalido: no emulador de projetor (APK 1.0.143) o ART
    recusou o classes4.dex e o app morreu com
        NoClassDefFoundError: Failed resolution of Lsmartedtv/full/XBMCJsonRPC
    """
    if dados[:4] != b'dex\n' or len(dados) < 112:
        return dados
    corpo = dados[32:]
    dados = dados[:12] + hashlib.sha1(corpo).digest() + dados[32:]
    corpo = dados[12:]
    dados = dados[:8] + struct.pack('<I', zlib.adler32(corpo) & 0xffffffff) + dados[12:]
    return dados


def cabecalho_do_dex_confere(dados):
    if dados[:4] != b'dex\n' or len(dados) < 112:
        return True
    assinatura = dados[12:32]
    checksum = struct.unpack('<I', dados[8:12])[0]
    return (assinatura == hashlib.sha1(dados[32:]).digest() and
            checksum == (zlib.adler32(dados[12:]) & 0xffffffff))


def trocar_pin_no_dex(dados, antigo, novo):
    """Troca o pin ASCII no dex. Só aceita exatamente uma ocorrência."""
    de = antigo.encode('ascii')
    para = novo.encode('ascii')
    if len(de) != len(para):
        raise SystemExit('pin novo com tamanho diferente')
    total = dados.count(de)
    if total == 0:
        return dados, 0          # este dex nao carrega o pin; nada a trocar
    if total != 1:
        raise SystemExit('pin aparece %d vez(es) no dex (esperado 1)' % total)
    return consertar_cabecalho_do_dex(dados.replace(de, para)), total


def executar(apk_entrada, apk_saida, atualizar_origem=True):
    arquivos, removidos, mantidos = planejar(apk_entrada)
    pin_antigo = pin_publicado()
    with zipfile.ZipFile(apk_entrada) as z:
        nomes = set(z.namelist())
        restantes = {n for n in nomes if n not in arquivos}
        manifesto = manifesto_de(z, restantes)
        pin_novo = hashlib.sha256(manifesto).hexdigest()
        trocados = 0
        with zipfile.ZipFile(apk_saida, 'w', allowZip64=True) as saida:
            for item in z.infolist():
                if item.is_dir() or item.filename in arquivos:
                    continue
                if item.filename == MANIFESTO:
                    dados = manifesto
                else:
                    dados = z.read(item)
                if item.filename.endswith('.dex'):
                    dados, quantos = trocar_pin_no_dex(dados, pin_antigo, pin_novo)
                    if quantos:
                        trocados += quantos
                        print('pin trocado em %s (%d ocorrencia)'
                              % (item.filename, quantos))
                info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
                info.compress_type = item.compress_type
                info.external_attr = item.external_attr
                info.comment = item.comment
                saida.writestr(info, dados)
    if trocados != 1:
        raise SystemExit('pin trocado %d vez(es) no dex; esperado 1' % trocados)
    # conferir o resultado no arquivo final
    with zipfile.ZipFile(apk_saida) as z:
        final = z.read(MANIFESTO)
        if hashlib.sha256(final).hexdigest() != pin_novo:
            raise SystemExit('manifesto final nao corresponde ao pin')
        sobrando = [a for a in addons_do_perfil(set(z.namelist()))
                    if a in ADDONS_DE_TERCEIROS]
        if sobrando:
            raise SystemExit('ainda no perfil: %s' % ', '.join(sobrando))
        dex_com_pin = [n for n in z.namelist() if n.endswith('.dex')
                       and pin_novo.encode('ascii') in z.read(n)]
        if not dex_com_pin:
            raise SystemExit('nenhum dex tem o pin novo')
    if atualizar_origem and gravar_pin_na_origem(pin_novo):
        print('pin atualizado no codigo Java do bootstrap: %s' % pin_novo)
    return {
        'pin_antigo': pin_antigo,
        'removidos': sorted(removidos),
        'mantidos': mantidos,
        'arquivos_removidos': len(arquivos),
        'pin': pin_novo,
    }


def pin_do_dex(z):
    """Pin de 64 hex que o dex do APK realmente confere.

    E a fonte da verdade do que o aparelho verifica: o `conferir` do APK
    publicado tem de olhar o proprio APK, nao o Java do repositorio (o build
    atualiza o Java no runner, mas o repositorio continua com o pin anterior).
    """
    candidatos = set()
    for nome in z.namelist():
        if not nome.endswith('.dex'):
            continue
        candidatos.update(_HEX64.findall(z.read(nome).decode('latin-1')))
    if len(candidatos) == 1:
        return candidatos.pop()
    return None


def conferir(apk, pin_esperado=None):
    """Checagem final do APK assinado: perfil limpo e pin batendo no dex."""
    problemas = []
    with zipfile.ZipFile(apk) as z:
        pin_java = pin_esperado or pin_do_dex(z) or pin_publicado()
    with zipfile.ZipFile(apk) as z:
        nomes = set(z.namelist())
        manifesto = z.read(MANIFESTO) if MANIFESTO in nomes else b''
        resumo = hashlib.sha256(manifesto).hexdigest()
        if resumo != pin_java:
            problemas.append('manifesto %s != pin do dex %s' % (resumo, pin_java))
        sobrando = sorted(a for a in addons_do_perfil(nomes)
                          if a in ADDONS_DE_TERCEIROS)
        if sobrando:
            problemas.append('addon de terceiro no perfil: %s' % ', '.join(sobrando))
        dexs = [n for n in nomes if n.endswith('.dex')
                and pin_java.encode('ascii') in z.read(n)]
        if not dexs:
            problemas.append('nenhum dex carrega o pin %s' % pin_java)
        elif pin_publicado() != pin_java:
            print('aviso: pin do Java no repositorio e %s (o build regrava o '
                  'arquivo no runner)' % pin_publicado())
        for nome in sorted(nomes):
            if nome.endswith('.dex') and not cabecalho_do_dex_confere(z.read(nome)):
                problemas.append('cabecalho do dex invalido (checksum/assinatura): %s'
                                 % nome)
        for linha in manifesto.decode('utf-8').splitlines():
            partes = linha.split('\t')
            if len(partes) != 3:
                problemas.append('linha invalida no manifesto: %r' % linha[:40])
                continue
            sha, tamanho, caminho = partes
            completo = PERFIL + caminho
            if completo not in nomes:
                problemas.append('manifesto cita arquivo ausente: %s' % caminho)
                continue
            dados = z.read(completo)
            if hashlib.sha256(dados).hexdigest() != sha or str(len(dados)) != tamanho:
                problemas.append('arquivo nao bate com o manifesto: %s' % caminho)
    if problemas:
        raise SystemExit('perfil embarcado: ' + '; '.join(problemas))
    return True


def main(argv):
    if len(argv) >= 3 and argv[1] == '--conferir':
        conferir(argv[2])
        print('perfil embarcado conferido: nenhum addon de terceiro, pin do dex bate')
        return 0
    if len(argv) < 3:
        print(__doc__)
        return 2
    resultado = executar(argv[1], argv[2])
    print('addons de terceiros removidos do perfil: %s'
          % (', '.join(resultado['removidos']) or 'nenhum'))
    print('addons que ficam no perfil (%d): %s'
          % (len(resultado['mantidos']), ', '.join(resultado['mantidos'])))
    print('arquivos removidos: %d' % resultado['arquivos_removidos'])
    print('pin novo do manifesto: %s' % resultado['pin'])
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
