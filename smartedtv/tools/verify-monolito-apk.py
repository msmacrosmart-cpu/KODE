#!/usr/bin/env python3
"""Confere o APK único (smartedtv.full) e imprime um relatório completo.

Diferente de um verificador que morre no primeiro erro: aqui TODAS as checagens
rodam e o relatório mostra o que passou e o que falhou. Assim uma rodada de 2h
de build nunca é desperdiçada por causa de uma asserção mal escrita.

Uso:
    python3 verify-monolito-apk.py APK [--aapt2 CAMINHO] [--pacote ...]
                                   [--versao ...] [--codigo ...] [--relatorio ARQ]

Saída: relatório legível; código 1 se alguma checagem obrigatória falhar.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

PACOTE = "smartedtv.full"
VERSAO = "1.0.83"
CODIGO = 2103069

BLOCO_ABERTURA = "ca-app-pub-2066014755407744/4214378379"
BLOCO_PREROLL = "ca-app-pub-2066014755407744/3572039686"
ADS_APP_ID = "ca-app-pub-2066014755407744~5076693043"

# base estável (perfil semeado) dentro do APK
MANIFESTO_BASE = "assets/smarted/profile-manifest.txt"
MANIFESTO_BASE_SHA256 = "1447de816a44ecc11c42c2c315cf20e61c9baa037e914a13293711cf152d1ede"
BRAZUCA = "assets/smarted/profile/addons/plugin.video.BrazucaPlay.Matrix/addon.xml"

ADDONS = (
    "skin.novatv",
    "skin.smartedtv.classic",
    "plugin.video.smarted",
    "service.smarted.bootstrap",
    "resource.uisounds.silencio",
)

PONTE = (
    "ATIVIDADE_PREROLL = 'smartedtv.full.PreRollActivity'",
    "ATIVIDADE_ABERTURA = 'smartedtv.full.AppOpenActivity'",
    "tentar_plano_b=False",
)


class Relatorio:
    def __init__(self) -> None:
        self.linhas: list[str] = []
        self.erros: list[str] = []
        self.avisos: list[str] = []

    def titulo(self, texto: str) -> None:
        self.linhas.append("")
        self.linhas.append(f"== {texto}")

    def ok(self, rotulo: str, detalhe: str = "") -> None:
        self.linhas.append(f"  OK    {rotulo:<34} {detalhe}")

    def falha(self, rotulo: str, detalhe: str = "") -> None:
        self.erros.append(f"{rotulo}: {detalhe}")
        self.linhas.append(f"  FALHA {rotulo:<34} {detalhe}")

    def aviso(self, rotulo: str, detalhe: str = "") -> None:
        self.avisos.append(f"{rotulo}: {detalhe}")
        self.linhas.append(f"  aviso {rotulo:<34} {detalhe}")

    def texto(self, conteudo: str) -> None:
        self.linhas.append("  " + conteudo.replace("\n", "\n  "))

    def exige(self, condicao: bool, rotulo: str, detalhe: str = "") -> bool:
        (self.ok if condicao else self.falha)(rotulo, detalhe)
        return condicao


def dump(aapt2: str, *args: str) -> str:
    proc = subprocess.run([aapt2, *args], capture_output=True, text=True)
    if proc.returncode != 0:
        return f"<<aapt2 falhou: {proc.stderr.strip()[:200]}>>"
    return proc.stdout


def conferir(apk: Path, aapt2: str, rel: Relatorio, esperado: dict) -> None:
    rel.titulo(f"arquivo: {apk}  ({apk.stat().st_size / 1048576.0:.1f} MB)")

    # ---------------------------------------------------------------- badging
    rel.titulo("identidade do pacote (aapt2 badging)")
    badging = dump(aapt2, "dump", "badging", str(apk))
    primeira = badging.splitlines()[0] if badging else "(sem saída)"
    rel.texto(primeira)
    rel.exige(f"package: name='{esperado['pacote']}'" in badging,
              "pacote", esperado["pacote"])
    rel.exige(f"versionName='{esperado['versao']}'" in badging,
              "versionName", esperado["versao"])
    rel.exige(f"versionCode='{esperado['codigo']}'" in badging,
              "versionCode", str(esperado["codigo"]))

    # --------------------------------------------------------------- manifesto
    rel.titulo("manifesto (aapt2 xmltree)")
    arvore = dump(aapt2, "dump", "xmltree", "--file", "AndroidManifest.xml", str(apk))
    rel.exige("AppOpenActivity" in arvore, "activity de abertura", ".AppOpenActivity")
    rel.exige("PreRollActivity" in arvore, "activity de pre-roll", ".PreRollActivity")
    rel.exige(ADS_APP_ID in arvore, "APPLICATION_ID do AdMob", ADS_APP_ID)
    rel.exige("OtaProvider" in arvore, "provedor do APK de atualização", ".OtaProvider")
    rel.exige("REQUEST_INSTALL_PACKAGES" in arvore,
              "permissão de instalar atualização", "REQUEST_INSTALL_PACKAGES")
    rel.exige("AtualizaActivity" in arvore, "tela de procurar atualização", ".AtualizaActivity")
    rel.exige("com.google.android.gms.permission.AD_ID" in arvore,
              "permissão AD_ID", "com.google.android.gms.permission.AD_ID")

    orientacoes = [l.strip() for l in arvore.splitlines() if "screenOrientation" in l]
    # aapt2 imprime o enum: "=6" (sensorLandscape) em algumas versoes, "0x6" em outras
    if any("sensorLandscape" in l or "0x6" in l or l.rstrip().endswith("=6")
           for l in orientacoes):
        rel.ok("telas de anúncio em paisagem", f"{len(orientacoes)} linha(s)")
    else:
        rel.aviso("telas de anúncio em paisagem", "sem sensorLandscape no manifesto")
        for linha in orientacoes[:4]:
            rel.texto(linha)

    # -------------------------------------------------------------------- ZIP
    rel.titulo("conteúdo do APK (ZIP)")
    with zipfile.ZipFile(apk) as z:
        nomes = z.namelist()
        presentes = set(nomes)

        for addon in ADDONS:
            alvo = f"assets/addons/{addon}/addon.xml"
            rel.exige(alvo in presentes, f"addon {addon}", alvo)

        # A skin precisa estar COMPLETA: o build de 1.0.65/1.0.70 levava 222
        # arquivos enquanto a estavel tinha 934 (faltavam as imagens de media/,
        # por isso as abas/categorias apareciam vazias).
        skin = [n for n in nomes if n.startswith("assets/addons/skin.novatv/")]
        midia = [n for n in skin if "/media/" in n]
        rel.exige(len(skin) >= 800, "skin.novatv completa",
                  f"{len(skin)} arquivos (a estavel tinha 934)")
        rel.exige(len(midia) >= 600, "imagens da skin (media/)",
                  f"{len(midia)} imagens")
        rel.exige("assets/addons/skin.novatv/media/DefaultAddon.png" in presentes,
                  "imagem-sentinela da skin", "media/DefaultAddon.png")

        plugin = [n for n in nomes if n.startswith("assets/addons/plugin.video.smarted/")]
        rel.exige(len(plugin) >= 16, "plugin.video.smarted completo",
                  f"{len(plugin)} arquivos")
        rel.exige("assets/addons/plugin.video.smarted/catalogue.py" in presentes,
                  "catálogo do plugin (abas)", "plugin.video.smarted/catalogue.py")

        # --- QR de compartilhamento / ponto de retomada ----------------------
        qr = "assets/addons/script.smartedtv.ajustes/resources/qrcode.png"
        rel.exige(qr in presentes, "QR Code no pacote", qr)
        qr_cakto = "assets/addons/script.smartedtv.ajustes/resources/qrcode-cakto.png"
        rel.exige(qr_cakto in presentes, "QR do checkout (Cakto) no pacote", qr_cakto)
        if qr_cakto in presentes:
            rel.exige(z.read(qr_cakto)[:8] == b"\x89PNG\r\n\x1a\n", "QR do checkout é PNG",
                      f"{len(z.read(qr_cakto))} bytes")
        if qr in presentes:
            dados_qr = z.read(qr)
            rel.exige(dados_qr[:8] == b"\x89PNG\r\n\x1a\n", "QR é PNG", f"{len(dados_qr)} bytes")
        bootstrap = "assets/addons/service.smarted.bootstrap/retomar.py"
        rel.exige(bootstrap in presentes, "ponto de retomada", bootstrap)
        b_skin = "assets/addons/service.smarted.bootstrap/skin_setup.py"
        if b_skin in presentes:
            texto_skin = z.read(b_skin).decode("utf-8", "replace")
            rel.exige("def ensure_shortcuts" in texto_skin,
                      "atalhos VIP/Compartilhar na Home", "ensure_shortcuts")
            rel.exige("plugin://script.smartedtv.ajustes/" in texto_skin,
                      "atalhos apontam para o add-on de ajustes",
                      "plugin://script.smartedtv.ajustes/")
        else:
            rel.falha("skin_setup do bootstrap", f"{b_skin} ausente")
        b_vip = "assets/addons/service.smarted.bootstrap/vip.py"
        if b_vip in presentes:
            texto_vip = z.read(b_vip).decode("utf-8", "replace")
            rel.exige("VALIDAR_URIS" in texto_vip,
                      "ativação por código (rotas)", "VALIDAR_URIS")
        # o menu dos atalhos da Home mora no add-on de ajustes: o
        # plugin.video.smarted do APK é substituído pelo do APK estável
        vipmenu = "assets/addons/script.smartedtv.ajustes/vipmenu.py"
        rel.exige(vipmenu in presentes, "menu VIP do atalho da Home", vipmenu)
        if vipmenu in presentes:
            texto_vipmenu = z.read(vipmenu).decode("utf-8", "replace")
            rel.exige("plugin://script.smartedtv.ajustes/" in texto_vipmenu,
                      "rotas do menu VIP", "plugin://script.smartedtv.ajustes/")
        ajustes_xml = "assets/addons/script.smartedtv.ajustes/addon.xml"
        if ajustes_xml in presentes:
            texto_ajustes = z.read(ajustes_xml).decode("utf-8", "replace")
            rel.exige("xbmc.python.pluginsource" in texto_ajustes,
                      "ajustes como fonte de plugin", "xbmc.python.pluginsource")

        # --- menu de ajustes / VIP -------------------------------------------
        alvo_ajustes = "assets/addons/script.smartedtv.ajustes/addon.xml"
        rel.exige(alvo_ajustes in presentes, "addon de ajustes (VIP)", alvo_ajustes)
        home = "assets/addons/skin.novatv/xml/Home.xml"
        if home in presentes:
            texto_home = z.read(home).decode("utf-8", "replace")
            rel.exige("RunAddon(script.smartedtv.ajustes)" in texto_home,
                      "Home abre o menu SMARTEDTV", "RunAddon(script.smartedtv.ajustes)")
        else:
            rel.falha("Home da skin", f"{home} ausente")

        if "assets/system/addon-manifest.xml" in presentes:
            manifesto = z.read("assets/system/addon-manifest.xml").decode("utf-8", "replace")
            rel.exige("<addon>skin.novatv</addon>" in manifesto,
                      "skin.novatv no addon-manifest", "padrão na primeira execução")
            rel.exige("<addon>script.smartedtv.ajustes</addon>" in manifesto,
                      "ajustes no addon-manifest", "habilitado na primeira execução")
        else:
            rel.falha("addon-manifest.xml", "assets/system/addon-manifest.xml ausente")

        for sonda, rotulo in (
            ("assets/media/splash.jpg", "splash da GUI"),
            ("assets/media/applaunch_screen.png", "splash do Android"),
        ):
            if sonda in presentes:
                rel.ok(rotulo, sonda)
            else:
                rel.falha(rotulo, f"{sonda} ausente")

        # o aapt compila os drawables: o caminho original não aparece no ZIP,
        # só entradas res/**.png
        icones = [n for n in nomes if n.startswith("res/") and n.endswith(".png")]
        if icones:
            rel.ok("ícones do launcher no APK", f"{len(icones)} PNG em res/")
        else:
            rel.aviso("ícones do launcher", "nenhum PNG em res/")

        # biblioteca nativa e motor
        if "lib/arm64-v8a/libkodi.so" in presentes:
            rel.ok("motor nativo", "lib/arm64-v8a/libkodi.so")
        else:
            libs = [n for n in nomes if n.startswith("lib/arm64-v8a/") and n.endswith(".so")]
            rel.falha("motor nativo", f"libkodi.so ausente (libs: {len(libs)})")

        dex = b"".join(z.read(n) for n in nomes
                       if n.startswith("classes") and n.endswith(".dex"))
        pacotes = sorted({n.split("/")[2] for n in nomes
                          if n.startswith("assets/addons/") and n.count("/") > 2})
        rel.texto(f"addons no APK ({len(pacotes)}): " + ", ".join(pacotes[:14]))

        ponte = None
        alvo_ponte = "assets/addons/service.smarted.bootstrap/smart_ads.py"
        if alvo_ponte in presentes:
            ponte = z.read(alvo_ponte).decode("utf-8", "replace")

        # ------------------------------------------------ base estável (perfil)
        rel.titulo("base estável (perfil semeado da linha clássica)")
        if MANIFESTO_BASE in presentes:
            import hashlib
            dados = z.read(MANIFESTO_BASE)
            digest = hashlib.sha256(dados).hexdigest()
            esperado = esperado["manifesto_base"]
            rel.exige(digest == esperado, "manifesto do perfil",
                      f"{digest[:16]}… (esperado {esperado[:16]}…)")
            arquivos = [n for n in nomes if n.startswith("assets/smarted/profile/")
                        and not n.endswith("/")]
            rel.exige(len(arquivos) > 50, "arquivos do perfil", f"{len(arquivos)} entradas")

            # diagnóstico: formato real das linhas do manifesto e dos caminhos
            linhas = [l for l in dados.decode("utf-8", "replace").splitlines() if l.strip()]
            rel.texto(f"manifesto: {len(linhas)} linhas; 3 primeiras:")
            for linha in linhas[:3]:
                rel.texto("   " + linha.replace("\t", " | ")[:110])
            prefixos = sorted({l.split("\t")[2].split("/")[0] for l in linhas
                               if len(l.split("\t")) == 3})
            rel.texto("primeiro componente dos caminhos: " + ", ".join(prefixos[:8]))
            rel.texto("amostra de arquivos no APK:")
            for nome in arquivos[:6]:
                rel.texto("   " + nome)

            # o que faz o layout/menus aparecerem: skin ativa e ajustes da skin
            gui = "assets/smarted/profile/userdata/guisettings.xml"
            if gui in presentes:
                texto = z.read(gui).decode("utf-8", "replace")
                skin = [l.strip() for l in texto.splitlines() if "lookandfeel.skin" in l]
                rel.texto("guisettings do perfil: " + (skin[0][:120] if skin else "(sem lookandfeel.skin)"))
            else:
                rel.falha("guisettings no perfil", "userdata/guisettings.xml ausente")

            # o layout/menus podem estar dentro do backup do wizard
            import io
            for zip_nome in ("My_Builds/BACKUP+SMARTED.zip", "SaveData.zip"):
                chave = "assets/smarted/profile/" + zip_nome
                if chave not in presentes:
                    rel.texto(f"backup {zip_nome}: ausente")
                    continue
                try:
                    with zipfile.ZipFile(io.BytesIO(z.read(chave))) as interno:
                        itens = interno.namelist()
                        alvos = [n for n in itens
                                 if "addon_data/skin.novatv" in n or "skinshortcuts" in n]
                        rel.texto(f"backup {zip_nome}: {len(itens)} entradas, "
                                  f"{len(alvos)} de skin/menus")
                        for nome in alvos[:5]:
                            rel.texto("   " + nome)
                        gui = [n for n in itens if n.endswith("guisettings.xml")]
                        if gui:
                            texto = interno.read(gui[0]).decode("utf-8", "replace")
                            skin = [l.strip() for l in texto.splitlines()
                                    if "lookandfeel.skin" in l]
                            rel.texto("   guisettings do backup: "
                                      + (skin[0][:110] if skin else "(sem skin)"))
                except Exception as erro:
                    rel.texto(f"backup {zip_nome}: ilegível ({erro.__class__.__name__})")

            for rotulo, trecho in (
                ("ajustes da skin.novatv", "userdata/addon_data/skin.novatv/"),
                ("atalhos/menus (skinshortcuts)", "script-skinshortcuts"),
                ("fontes do catálogo (sources.xml)", "userdata/sources.xml"),
                ("favoritos", "userdata/favourites.xml"),
            ):
                quantos = [n for n in arquivos if trecho in n]
                rel.texto(f"{rotulo}: {len(quantos)} arquivo(s)"
                          + (f" — ex.: {quantos[0].split('/profile/')[-1]}" if quantos else ""))
            rel.exige(BRAZUCA in presentes, "Brazuca Play no perfil", BRAZUCA)
        else:
            rel.falha("base estável", f"{MANIFESTO_BASE} ausente no APK")

    # ------------------------------------------------------- TV x celular
    rel.titulo("Android TV e celular no mesmo APK")
    for rotulo, agulha in (
        ("touchscreen opcional", b'android.hardware.touchscreen'),
        ("leanback opcional", b'android.software.leanback'),
        ("launcher de TV", b'LEANBACK_LAUNCHER'),
    ):
        rel.exige(agulha in arvore.encode("utf-8", "replace"), rotulo, agulha.decode())

    # -------------------------------------------------------------------- dex
    rel.titulo("classes no dex (anúncios dentro do app)")
    for rotulo, agulha in (
        ("bloco de abertura", BLOCO_ABERTURA.encode()),
        ("bloco de pre-roll", BLOCO_PREROLL.encode()),
        ("activity AppOpenActivity", b"AppOpenActivity"),
        ("activity PreRollActivity", b"PreRollActivity"),
        ("SDK do AdMob", b"com/google/android/gms/ads"),
        ("classe SmartAds", b"SmartAds"),
        ("perfil da base reconhecido", b"perfilSmarted"),
        ("perfil antigo guardado, nao apagado", b".kodi.antigo-"),
        ("log do seed", b"smarted-seed.log"),
        ("leitor da licenca VIP", b"Licenca"),
        ("checagem de VIP antes do anuncio", b"adsPermitidos"),
        ("abrir link (checkout)", b"AbrirUrlActivity"),
        ("compartilhar aplicativo", b"CompartilharActivity"),
        ("abertura limpa do Kodi", b"iniciarKodi"),
        ("ponte com o Supabase", b"Supabase"),
        ("QR de compartilhamento do app", b"qrcode.png"),
        ("atualização OTA", b"atualizacao.json"),
        ("entrega do APK por content://", b".ota"),
        ("instalador nativo", b"application/vnd.android.package-archive"),
    ):
        rel.exige(agulha in dex, rotulo, agulha.decode()[:44])

    if ADS_APP_ID.encode() in dex:
        rel.ok("APPLICATION_ID no dex", "presente (redundante com o manifesto)")
    else:
        rel.aviso("APPLICATION_ID no dex", "não está no dex (esperado: só no manifesto)")

    # ---------------------------------------------------------------- ponte
    rel.titulo("ponte do serviço de bootstrap")
    if ponte is None:
        rel.falha("smart_ads.py embarcado", "ausente no APK")
    else:
        for agulha in PONTE:
            rel.exige(agulha in ponte, "ponte", agulha)
        # comentários e o antigo ATIVIDADE_LAUNCHER podem citar o pacote antigo
        # (o plano B está desligado); o que importa são as constantes em uso.
        if ("ATIVIDADE_ABERTURA = 'org.smartedtv" in ponte
                or "ATIVIDADE_PREROLL = 'org.smartedtv" in ponte):
            rel.falha("ponte", "aponta para o app auxiliar antigo (org.smartedtv.ads)")
        else:
            rel.ok("ponte", "constantes em uso apontam para dentro do app")

    # ------------------------------------------------------------------ splash
    rel.titulo("splash (barra branca, sem texto)")
    recursos = dump(aapt2, "dump", "resources", str(apk))
    rel.exige("progresswhite" in recursos, "drawable branco", "progresswhite")
    layout = dump(aapt2, "dump", "xmltree", "--file",
                  "res/layout/activity_splash.xml", str(apk))
    if layout.startswith("<<"):
        # o aapt2 pode renomear o caminho do layout; procura pelo id
        layout = ""
    if layout:
        rel.exige("progressBar1" in layout or "progressDrawable" in layout,
                  "layout da splash", "activity_splash.xml legível")
        # O `visibility` do XML usa a enum do aapt (visible=0, invisible=1,
        # gone=2) — não os valores do View (VISIBLE=0, INVISIBLE=4, GONE=8).
        visib = [l.strip() for l in layout.splitlines() if "isib" in l]
        escondido = False
        for linha in visib:
            valor = linha.split("=")[-1].split()[0] if "=" in linha else ""
            if valor.rstrip(")").lower() in ("2", "0x2", "0x02", "0x00000002"):
                escondido = True
        rel.exige(escondido, "texto de status",
                  "escondido (gone)" if escondido else "visível no layout")
    else:
        rel.aviso("layout da splash", "não consegui ler activity_splash.xml")

    # -------------------------------------------------------------- resumo
    rel.titulo("resumo")
    rel.texto(f"obrigatórias com falha: {len(rel.erros)}")
    rel.texto(f"avisos: {len(rel.avisos)}")
    if rel.erros:
        for erro in rel.erros:
            rel.texto(f"- {erro}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("apk")
    ap.add_argument("--aapt2", default="aapt2")
    ap.add_argument("--pacote", default=PACOTE)
    ap.add_argument("--versao", default=VERSAO)
    ap.add_argument("--codigo", type=int, default=CODIGO)
    ap.add_argument("--manifesto-base-sha", default=MANIFESTO_BASE_SHA256)
    ap.add_argument("--relatorio", default="")
    args = ap.parse_args()

    esperado = {"pacote": args.pacote, "versao": args.versao, "codigo": args.codigo,
                "manifesto_base": args.manifesto_base_sha}

    apk = Path(args.apk)
    rel = Relatorio()
    if not apk.is_file():
        rel.falha("APK", f"não existe: {apk}")
    else:
        conferir(apk, args.aapt2, rel, esperado)

    texto = "\n".join(rel.linhas).lstrip("\n")
    print(texto)
    if args.relatorio:
        Path(args.relatorio).write_text(texto + "\n", encoding="utf-8")
    return 1 if rel.erros else 0


if __name__ == "__main__":
    raise SystemExit(main())
