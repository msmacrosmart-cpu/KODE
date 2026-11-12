# SMARTED-TV 1.0.50 — correção dos erros do log + menu Brazuca Play

**APK direto:** https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.50-smarted-arm64/SMARTED-TV-v1.0.50-arm64.apk
**Tamanho:** 375.954.147 bytes · **versionName** 1.0.50 · **versionCode** 2103036 · `org.xbmc.kodi` ARM64
**Build:** run `43179307673` — 11 passos verdes, assinado com a chave da linha 1.0.15+ (instala por cima).

## O que o log do Kodi mostrou

```
ModuleNotFoundError: No module named 'arrow'        -> script.skin.helper.service / backgrounds
ModuleNotFoundError: No module named 'unidecode'    -> script.skinshortcuts (menu da skin!)
ModuleNotFoundError: No module named 'simplejson'   -> script.bingie.helper
```

Traduzindo: os serviços da skin morriam no boot e o **gerador de menu do
skinshortcuts nem rodava** — por isso a Home aparecia sem a barra de categorias
e com as entradas genéricas do Kodi (Filmes/Séries/PVR).

## O que foi corrigido nesta versão

- **`tools/kodi/vendor-python-modules.py`** (novo): baixa as wheels cp311/aarch64 e
  monta addons `script.module.*` com `addon.xml` + `lib/`, embutidos no APK:
  `arrow`, `dateutil`, `unidecode`, `simpleeval`, `requests`, `urllib3`, `idna`,
  `certifi`, `charset_normalizer`, `beautifulsoup4`, `soupsieve`,
  `musicbrainzngs`, `simplejson`, `pil`.
- **Verificação automática de imports** (a etapa nova do build): varre o código de
  todos os addons embarcados, ignora imports protegidos por `try/except
  ImportError` e **falha o build** se algum import de terceiro não tiver módulo.
  É isso que impede o erro de voltar sem ninguém ver.
- **Barra superior** (herdada da skin base Bingie, exibida como SMARTEDTV): as 7
  categorias — TV ao vivo, Filmes, Séries, Novelas, Animes, Doramas, Desenhos —
  fixas no topo, cada uma abrindo a pasta real do `plugin.video.BrazucaPlay.Matrix`
  (`mode=21/27/25/22/31/28`). Sem botão de Add-ons; ficam Busca, Ajustes e Sair.
  Os carrosséis/HERO usam as rotas do SMARTED (lançamentos de filmes e séries,
  favoritos por categoria).
- **Menu estático**: o `script.skinshortcuts` não regrava por cima, e no primeiro
  boot o bootstrap limpa os dados antigos do menu e recarrega a interface uma vez.
- Som silenciado (`resource.uisounds.silencio`) e migalha: a skin antiga fica
  instalada como **SMARTEDTV Classica** (Ajustes > Aparência > Skin) para voltar.
- Ajuste de build: `versionName` só pode ter o mesmo tamanho do anterior (o
  metadado é binário) — bug que derrubou a tentativa 1.1.0 na assinatura.

## Como testar

1. Baixe o APK no link e instale por cima (mesma assinatura, atualiza).
2. Abra o app e espere o primeiro boot (ele limpa o menu antigo e recarrega a skin).
3. O topo deve mostrar as 7 categorias + Busca/Ajustes/Sair; as fileiras devem
   vir do Brazuca Play.
4. Se algo travar: Ajustes > Aparência > Skin > *SMARTEDTV Classica* volta a
   interface anterior sem reinstalar nada; e me mande o `kodi.log` — agora o log
   já é lido no processo de build, não é mais chute.

## Pendências conhecidas

- Widgets/spotlight do Bingie são configuráveis na skin; o conteúdo é do Brazuca,
  mas o layout de cada fileira ainda herda o padrão do autor.
- `PIL` vai embutido (20 MB) porque o TMDb Helper importa sem proteção; dá para
  cortar se você não usar as funções de imagem.
