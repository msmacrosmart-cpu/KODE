# -*- coding: utf-8 -*-
"""TV EMINEM - instalador automatico da build.

Mostra a arte em TELA CHEIA durante todo o download/instalacao (escondendo a
interface vazia do Kodi), com a barra de progresso e UMA linha de texto por
cima. Ao terminar, reinicia o app sozinho.
"""
import os
import json
import zipfile
import urllib.request

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ZIP_URL = "https://archive.org/download/tv-eminem-3.0.6-64/TV-EMINEM-3.0.6-64.zip"
CHECK_ID = "plugin.video.flixplay"
FLAG = "tveminem_installed.txt"
ADDON_ID = "service.kodiplay.installer"


def log(msg):
    xbmc.log("[TV EMINEM] %s" % msg, xbmc.LOGINFO)


def home():
    return xbmcvfs.translatePath("special://home/")


def addons_dir():
    return os.path.join(home(), "addons")


def flag_path():
    return os.path.join(xbmcvfs.translatePath("special://profile/"), FLAG)


def ja_instalado():
    """So considera instalado se a marca for da MESMA build. Assim, ao
    instalar um APK novo apontando pra outra build, ela e baixada e
    atualizada por cima automaticamente."""
    try:
        with open(flag_path(), "r", encoding="utf-8") as f:
            marcado = f.read().strip()
    except Exception:
        return False
    if marcado == ZIP_URL:
        return True
    log("build diferente da marcada — vai atualizar")
    return False


def marcar():
    """Guarda QUAL build esta instalada (o endereco dela)."""
    try:
        with open(flag_path(), "w", encoding="utf-8") as f:
            f.write(ZIP_URL)
    except Exception:
        pass


def recurso(nome):
    """Caminho de um arquivo em resources/ do addon (copiado p/ temp)."""
    destino = xbmcvfs.translatePath("special://temp/tve_%s" % nome)
    try:
        if os.path.exists(destino) and os.path.getsize(destino) > 50:
            return destino
        base = xbmcaddon.Addon(ADDON_ID).getAddonInfo("path")
        origem = os.path.join(base, "resources", nome)
        xbmcvfs.copy(origem, destino)
        return destino if os.path.exists(destino) else origem
    except Exception as exc:
        log("recurso %s: %s" % (nome, exc))
        return ""


def splash_local():
    """Copia a arte do addon pra pasta temp (garante que o control ache)."""
    destino = xbmcvfs.translatePath("special://temp/tveminem_splash.jpg")
    try:
        if os.path.exists(destino) and os.path.getsize(destino) > 1000:
            return destino
        base = xbmcaddon.Addon(ADDON_ID).getAddonInfo("path")
        origem = os.path.join(base, "resources", "splash.jpg")
        xbmcvfs.copy(origem, destino)
        if os.path.exists(destino):
            return destino
        return origem
    except Exception as exc:
        log("splash: %s" % exc)
        return ""


class TelaInstalacao(xbmcgui.WindowDialog):
    """Janela sem fundo: arte em tela cheia + texto (1 linha) + barra."""

    def __init__(self):
        super(TelaInstalacao, self).__init__()
        larg, alt = self.getWidth(), self.getHeight()

        img = splash_local()
        if img:
            self.fundo = xbmcgui.ControlImage(0, 0, larg, alt, img,
                                              aspectRatio=0)
            self.addControl(self.fundo)

        # texto: UMA linha, centralizado, logo acima da barra
        y_txt = int(alt * 0.86)
        self.texto = xbmcgui.ControlLabel(
            int(larg * 0.10), y_txt, int(larg * 0.80), 30, "",
            font="font13", textColor="0xFFFFFFFF", alignment=2 | 4)
        self.addControl(self.texto)

        # barra por cima da arte
        self.barra = xbmcgui.ControlProgress(
            int(larg * 0.10), int(alt * 0.91), int(larg * 0.80), 20)
        self.addControl(self.barra)
        self.barra.setPercent(0)

    def atualizar(self, pct, msg):
        try:
            self.barra.setPercent(max(0, min(100, pct)))
            self.texto.setLabel(msg)
        except Exception:
            pass

    def piscar(self, msg, segundos):
        """Mostra a mensagem piscando por N segundos (fase de espera)."""
        fim = segundos * 2
        for i in range(fim):
            try:
                self.texto.setLabel(msg if i % 2 == 0 else "")
            except Exception:
                pass
            xbmc.sleep(500)
        try:
            self.texto.setLabel(msg)
        except Exception:
            pass


def _tamanho_remoto():
    """Quantos bytes o servidor diz que o arquivo tem (0 se nao informar)."""
    try:
        req = urllib.request.Request(
            ZIP_URL, headers={"User-Agent": "Mozilla/5.0 (TVEminem)"})
        req.get_method = lambda: "HEAD"
        with urllib.request.urlopen(req, timeout=60) as r:
            return int(r.headers.get("Content-Length") or 0)
    except Exception:
        return 0


def baixar(tela, destino, tentativas=4):
    """Baixa com RETOMADA: se a conexao cair no meio, continua de onde parou
    em vez de estragar o arquivo. Em internet lenta, so demora mais."""
    esperado = _tamanho_remoto()
    baixado = 0
    if os.path.exists(destino):
        try:
            os.remove(destino)
        except Exception:
            pass

    for tentativa in range(1, tentativas + 1):
        try:
            cab = {"User-Agent": "Mozilla/5.0 (TVEminem)"}
            if baixado:
                cab["Range"] = "bytes=%d-" % baixado   # retoma
            req = urllib.request.Request(ZIP_URL, headers=cab)
            with urllib.request.urlopen(req, timeout=120) as r:
                if not esperado:
                    esperado = int(r.headers.get("Content-Length") or 0) + baixado
                modo = "ab" if baixado else "wb"
                with open(destino, modo) as f:
                    while True:
                        pedaco = r.read(64 * 1024)
                        if not pedaco:
                            break
                        f.write(pedaco)
                        baixado += len(pedaco)
                        mb = baixado / (1024.0 * 1024.0)
                        if esperado:
                            pct = int(baixado * 100 / esperado)
                            extra = "" if tentativa == 1 else "  (retomando)"
                            tela.atualizar(
                                int(pct * 0.7),
                                "Baixando...  %.1f MB de %.1f MB  (%d%%)%s"
                                % (mb, esperado / (1024.0 * 1024.0), pct, extra))
                        else:
                            tela.atualizar(35, "Baixando...  %.1f MB" % mb)
        except Exception as exc:
            log("download interrompido (tentativa %d): %s" % (tentativa, exc))
            baixado = os.path.getsize(destino) if os.path.exists(destino) else 0

        # terminou inteiro?
        if esperado and baixado >= esperado:
            return True
        if not esperado and baixado > 0 and zipfile.is_zipfile(destino):
            return True

        if tentativa < tentativas:
            tela.atualizar(
                int((baixado * 100.0 / esperado) * 0.7) if esperado else 5,
                "Conexao instavel. Retomando o download... (%d/%d)"
                % (tentativa + 1, tentativas))
            for _ in range(6):
                xbmc.sleep(500)

    log("download incompleto: %d de %d bytes" % (baixado, esperado))
    return False


def extrair(tela, zip_path):
    with zipfile.ZipFile(zip_path) as z:
        nomes = z.namelist()
        topo = set(n.split("/")[0] for n in nomes if "/" in n)
        destino = home() if "addons" in topo else addons_dir()
        log("extraindo %d arquivos em %s" % (len(nomes), destino))
        total = len(nomes) or 1
        for i, nome in enumerate(nomes, 1):
            z.extract(nome, destino)
            if i % 15 == 0 or i == total:
                tela.atualizar(
                    min(99, 70 + int(i * 30.0 / total)),
                    "Instalando...  %d de %d arquivos" % (i, total))
        return destino


def habilita_novos(antes):
    try:
        agora = set(os.listdir(addons_dir()))
    except Exception:
        return 0
    n = 0
    for name in sorted(agora - antes):
        if not os.path.isfile(os.path.join(addons_dir(), name, "addon.xml")):
            continue
        try:
            xbmc.executeJSONRPC(json.dumps({
                "jsonrpc": "2.0", "id": 1,
                "method": "Addons.SetAddonEnabled",
                "params": {"addonid": name, "enabled": True}}))
            n += 1
        except Exception:
            pass
    return n


class TelaFinal(xbmcgui.WindowDialog):
    """Aviso final sobre a arte: instalacao concluida + botao OK que fecha."""

    def __init__(self):
        super(TelaFinal, self).__init__()
        larg, alt = self.getWidth(), self.getHeight()

        img = splash_local()
        if img:
            self.addControl(xbmcgui.ControlImage(0, 0, larg, alt, img,
                                                 aspectRatio=0))

        # painel PRETO TRANSLUCIDO por tras do texto
        try:
            painel = recurso("panel_black.png")
            if painel:
                self.addControl(xbmcgui.ControlImage(
                    int(larg * 0.06), int(alt * 0.30),
                    int(larg * 0.88), int(alt * 0.42), painel,
                    aspectRatio=0))
        except Exception as exc:
            log("painel: %s" % exc)

        titulo = xbmcgui.ControlLabel(
            int(larg * 0.08), int(alt * 0.35), int(larg * 0.84), 60,
            "[B]INSTALACAO CONCLUIDA[/B]",
            font="font30", textColor="0xFFFFD700", alignment=2 | 4)
        self.addControl(titulo)

        l1 = xbmcgui.ControlLabel(
            int(larg * 0.08), int(alt * 0.46), int(larg * 0.84), 40,
            "A TV EMINEM foi instalada e atualizada com sucesso!",
            font="font14", textColor="0xFFFFFFFF", alignment=2 | 4)
        self.addControl(l1)

        l2 = xbmcgui.ControlLabel(
            int(larg * 0.08), int(alt * 0.53), int(larg * 0.84), 40,
            "O aplicativo sera fechado agora. Abra a TV EMINEM novamente "
            "para comecar a usar.",
            font="font13", textColor="0xFFEEEEEE", alignment=2 | 4)
        self.addControl(l2)

        self.botao = xbmcgui.ControlButton(
            int(larg * 0.40), int(alt * 0.62), int(larg * 0.20), 55,
            "OK", font="font14",
            textColor="0xFFFFFFFF", focusedColor="0xFFFFD700",
            alignment=2 | 4)
        self.addControl(self.botao)
        self.setFocus(self.botao)

    def onControl(self, control):
        if control == self.botao:
            self.close()

    def onAction(self, action):
        # OK/Enter/Select ou Voltar fecham a tela
        if action.getId() in (7, 100, 9, 10, 92, 13):
            self.close()


class TelaPergunta(xbmcgui.WindowDialog):
    """Pergunta em portugues, com a mesma aparencia da tela final."""

    def __init__(self, titulo, linha1, linha2, botao="SIM"):
        super(TelaPergunta, self).__init__()
        larg, alt = self.getWidth(), self.getHeight()
        self.resposta = False

        img = splash_local()
        if img:
            self.addControl(xbmcgui.ControlImage(0, 0, larg, alt, img,
                                                 aspectRatio=0))
        try:
            painel = recurso("panel_black.png")
            if painel:
                self.addControl(xbmcgui.ControlImage(
                    int(larg * 0.06), int(alt * 0.30),
                    int(larg * 0.88), int(alt * 0.42), painel, aspectRatio=0))
        except Exception:
            pass

        self.addControl(xbmcgui.ControlLabel(
            int(larg * 0.08), int(alt * 0.35), int(larg * 0.84), 60,
            "[B]%s[/B]" % titulo, font="font30",
            textColor="0xFFFFD700", alignment=2 | 4))
        self.addControl(xbmcgui.ControlLabel(
            int(larg * 0.08), int(alt * 0.46), int(larg * 0.84), 40,
            linha1, font="font14", textColor="0xFFFFFFFF", alignment=2 | 4))
        self.addControl(xbmcgui.ControlLabel(
            int(larg * 0.08), int(alt * 0.53), int(larg * 0.84), 40,
            linha2, font="font13", textColor="0xFFEEEEEE", alignment=2 | 4))

        self.botao = xbmcgui.ControlButton(
            int(larg * 0.40), int(alt * 0.62), int(larg * 0.20), 55,
            botao, font="font14", textColor="0xFFFFFFFF",
            focusedColor="0xFFFFD700", alignment=2 | 4)
        self.addControl(self.botao)
        self.setFocus(self.botao)

    def onControl(self, control):
        if control == self.botao:
            self.resposta = True
            self.close()

    def onAction(self, action):
        if action.getId() in (7, 100, 9, 10, 92, 13):
            self.resposta = True
            self.close()


def pedir_permissao():
    """Nossa tela (em portugues) no lugar do aviso em ingles do Kodi."""
    try:
        tela = TelaPergunta(
            "PERMISSAO NECESSARIA",
            "A TV EMINEM precisa liberar a instalacao de complementos.",
            "Toque em SIM para continuar a instalacao.",
            "SIM")
        tela.doModal()
        del tela
    except Exception as exc:
        log("tela de permissao falhou: %s" % exc)


def _versao_ok(addon_id):
    """True se o complemento instalado e reconhecido pelo Kodi (versao
    compativel). Se o Kodi nao o reconhece, a copia esta quebrada."""
    try:
        r = json.loads(xbmc.executeJSONRPC(json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "Addons.GetAddonDetails",
            "params": {"addonid": addon_id, "properties": ["version"]}})))
        return "result" in r and r["result"].get("addon") is not None
    except Exception:
        return False


def motivo_falha():
    """Ultima linha de erro do log do Kodi (pra mostrar o motivo real)."""
    try:
        caminho = xbmcvfs.translatePath("special://logpath/kodi.log")
        with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
            linhas = f.readlines()[-400:]
        chaves = ("dependency", "Unable to load", "requires", "not met",
                  "Failed to install", "unresolved")
        achados = [l.strip() for l in linhas
                   if any(k.lower() in l.lower() for k in chaves)]
        return achados[-1][-160:] if achados else ""
    except Exception:
        return ""


def instalar_inputstreams(tela):
    """Instala os complementos de video que a build precisa. Eles vem do
    repositorio oficial, entao atualizamos os repositorios antes."""
    tela.atualizar(100, "Atualizando os repositorios...")
    try:
        xbmc.executebuiltin("UpdateAddonRepos")
    except Exception:
        pass
    for _ in range(40):          # ate ~20s
        xbmc.sleep(500)

    problemas = []
    for addon_id, nome in (("inputstream.adaptive", "InputStream Adaptive"),
                           ("inputstream.ffmpegdirect", "FFmpeg Direct"),
                           ("inputstream.rtmp", "RTMP")):
        pasta = os.path.join(addons_dir(), addon_id)

        # A build costuma trazer esses complementos numa versao feita pra
        # outro Kodi — o que faz a instalacao falhar. Removemos a copia da
        # build e instalamos a versao certa do repositorio oficial.
        if os.path.isdir(pasta) and not _versao_ok(addon_id):
            log("removendo copia incompativel de %s" % addon_id)
            try:
                import shutil
                shutil.rmtree(pasta, ignore_errors=True)
                xbmc.executebuiltin("UpdateLocalAddons")
                xbmc.sleep(2000)
            except Exception as exc:
                log("nao removeu %s: %s" % (addon_id, exc))

        if not os.path.isdir(pasta):
            tela.atualizar(100, "Instalando %s..." % nome)
            log("instalando %s do repositorio oficial" % addon_id)
            try:
                xbmc.executebuiltin("InstallAddon(%s)" % addon_id)
                _confirma_dialogo(5)
                for _ in range(40):       # ate ~20s
                    if os.path.isdir(pasta):
                        break
                    xbmc.sleep(500)
            except Exception as exc:
                log("falhou instalar %s: %s" % (addon_id, exc))

        if os.path.isdir(pasta):
            try:
                xbmc.executeJSONRPC(json.dumps({
                    "jsonrpc": "2.0", "id": 1,
                    "method": "Addons.SetAddonEnabled",
                    "params": {"addonid": addon_id, "enabled": True}}))
            except Exception:
                pass
        else:
            problemas.append(nome)
            log("NAO INSTALOU: %s" % addon_id)
    return problemas


def finalizar(tela):
    """Mostra o aviso final SOBRE a arte e encerra o app. A tela de fundo
    so e fechada no fim, pra nunca aparecer a interface do Kodi."""
    try:
        final = TelaFinal()
        final.doModal()
        del final
    except Exception as exc:
        log("tela final falhou (%s), usando dialogo padrao" % exc)
        xbmcgui.Dialog().ok(
            "TV EMINEM",
            "Instalacao concluida com sucesso!\n\n"
            "O aplicativo sera fechado agora.\n"
            "Abra a TV EMINEM novamente para comecar a usar.")
    log("encerrando o app a pedido do usuario")
    try:
        xbmc.executebuiltin("Quit")
    except Exception:
        pass
    xbmc.sleep(3000)
    try:
        tela.close()
    except Exception:
        pass


def _set(setting, valor):
    try:
        xbmc.executeJSONRPC(json.dumps({
            "jsonrpc": "2.0", "id": 1,
            "method": "Settings.SetSettingValue",
            "params": {"setting": setting, "value": valor}}))
    except Exception as exc:
        log("setting %s: %s" % (setting, exc))


def _confirma_dialogo(segundos=3):
    """Aceita UMA vez um 'sim/nao' que apareca logo apos uma acao nossa.
    Nunca fica clicando em loop (isso podia acertar um 'deseja sair?' e
    fechar o aplicativo)."""
    fim = int(segundos * 1000 / 300)
    for _ in range(fim):
        if xbmc.getCondVisibility("Window.IsVisible(yesnodialog)"):
            xbmc.executebuiltin("SendClick(11)")
            xbmc.sleep(700)
            return True
        xbmc.sleep(300)
    return False


def por_em_portugues():
    """Aplica o portugues do Brasil SE o idioma ja estiver disponivel (vindo
    na build). Nao baixa nada aqui: baixar abria um dialogo em ingles."""
    alvo = "resource.language.pt_br"
    try:
        if not os.path.isdir(os.path.join(addons_dir(), alvo)):
            log("idioma pt_br nao esta presente - mantendo o atual")
            return
        _set("locale.language", alvo)
        xbmc.sleep(1500)
        _set("locale.country", "Brazil")
        _set("locale.timezonecountry", "Brazil")
        log("idioma: portugues (Brasil)")
    except Exception as exc:
        log("idioma falhou: %s" % exc)


def preparar_sistema():
    """Deixa o app pronto de fabrica: fontes desconhecidas ligadas,
    atualizacao automatica de QUALQUER repositorio e idioma portugues."""
    _set("addons.unknownsources", True)   # instalar de fontes desconhecidas
    _confirma_dialogo(3)                  # aceita o aviso de seguranca (1x)
    _set("addons.updatemode", 1)          # 1 = QUALQUER repositorio
    _set("general.addonupdates", 0)       # 0 = atualizar automaticamente
    log("sistema preparado (fontes desconhecidas + qualquer repositorio)")


def ativar_skin(antes):
    """Ativa automaticamente a skin que veio na build (se veio alguma)."""
    try:
        agora = set(os.listdir(addons_dir()))
    except Exception:
        return False
    novas = [n for n in sorted(agora - antes) if n.startswith("skin.")]
    if not novas:
        log("nenhuma skin nova na build")
        return False
    skin = novas[0]
    log("ativando skin: %s" % skin)
    try:
        xbmc.executeJSONRPC(json.dumps({
            "jsonrpc": "2.0", "id": 1,
            "method": "Settings.SetSettingValue",
            "params": {"setting": "lookandfeel.skin", "value": skin}}))
        xbmc.sleep(2500)
        # o Kodi pergunta "manter esta mudanca?" -> confirma sozinho
        for _ in range(10):
            if xbmc.getCondVisibility("Window.IsVisible(yesnodialog)"):
                xbmc.executebuiltin("SendClick(11)")
                break
            xbmc.sleep(500)
        xbmc.sleep(1500)
        return True
    except Exception as exc:
        log("falhou ativar skin: %s" % exc)
        return False


def instalar(tela):
    tmp = xbmcvfs.translatePath("special://temp/tveminem_build.zip")

    try:
        tela.atualizar(1, "Preparando o aplicativo...")
        preparar_sistema()
        completo = baixar(tela, tmp)

        tam = os.path.getsize(tmp) if os.path.exists(tmp) else 0
        log("baixado: %d bytes (completo=%s)" % (tam, completo))
        if not completo or tam < 1000 or not zipfile.is_zipfile(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass
            try:
                aviso = TelaPergunta(
                    "DOWNLOAD INCOMPLETO",
                    "Sua internet caiu durante o download da build.",
                    "Conecte-se a uma rede estavel e abra o aplicativo "
                    "novamente para tentar de novo.",
                    "OK")
                aviso.doModal()
                del aviso
            except Exception:
                pass
            try:
                tela.close()
            except Exception:
                pass
            return

        if not os.path.isdir(addons_dir()):
            os.makedirs(addons_dir())
        antes = set(os.listdir(addons_dir()))

        extrair(tela, tmp)
        try:
            os.remove(tmp)
        except Exception:
            pass

        tela.atualizar(99, "Ativando os complementos...")
        xbmc.executebuiltin("UpdateLocalAddons")
        xbmc.sleep(4000)
        habilita_novos(antes)
        tela.atualizar(100, "Aplicando o idioma e o visual...")
        por_em_portugues()
        ativar_skin(antes)
        marcar()
        log("instalacao concluida")

        finalizar(tela)
    except Exception as exc:
        log("ERRO: %s" % exc)
        try:
            tela.atualizar(0, "Falha na instalacao: %s" % exc)
            xbmc.sleep(8000)
            tela.close()
        except Exception:
            pass


def run():
    if ja_instalado():
        log("build ja instalada - nada a fazer")
        return
    # sobe a tela IMEDIATAMENTE, cobrindo a interface do Kodi
    tela = TelaInstalacao()
    tela.show()
    tela.atualizar(0, "")
    tela.piscar("AGUARDANDO...", 2)
    instalar(tela)


run()
