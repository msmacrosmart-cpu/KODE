# Relatório de integridade — SMARTEDTV

O que foi preservado, o que foi removido, o que foi personalizado, limitações e
situação de instalação/atualização.

## 1. Base utilizada

| Item | Valor |
|---|---|
| Projeto upstream | `xbmc/xbmc`, tag **`21.3-Omega`** |
| Commit | `a3a448d26b8d560a65655dab2cd122994dc4e146` |
| Versão exibida | **21.4.0** (identidade SMARTEDTV sobre o Kodi 21.3) |
| `versionCode` Android | **2104000** |
| Application ID | **`org.xbmc.kodi`** (preservado) |
| `ADDON_API` | **21.3.0** (preservado) |
| ABI | **arm64-v8a** |
| `minSdk` / `targetSdk` | 21 / 34 (do upstream) |

## 2. O que foi PRESERVADO do Kodi original

Tudo isto é o código do Kodi 21.3, sem modificação:

- Navegação completa (Home, Configurações, Arquivos, Biblioteca, Complementos).
- Sistema de reprodução: VideoPlayer (ffmpeg), AudioEngine, legendas, faixas,
  aceleração de hardware por MediaCodec.
- **PVR e TV**: módulos `pvr` compilados; sem cliente PVR instalado (usuário
  adiciona depois), mas `pvr.nextpvr`/IPTV Simple instalam normalmente.
- **Gerenciamento de arquivos e fontes de mídia** (Adicionar fonte, SMB/NFS/
  WebDAV/HTTP).
- **Listas de reprodução**: `playlistplayer`, `.m3u`/`.xsp` em
  `userdata/playlists/{music,video,mixed}` — intactos.
- **Sistema de skins**: Estuary é a padrão; o usuário pode instalar qualquer skin
  compatível com `xbmc.gui 5.17.0`. A skin Estuary está **completa e original**,
  exceto a linha de descrição em `addon.xml`.
- **Add-ons nativos**: `repository.xbmc.org` embarcado → o usuário instala o que
  quiser pelo menu Complementos. Todos os `kodi.binary.*` presentes.
- Configurações de áudio, vídeo, legendas, rede, controle parental, perfis.
- Compatibilidade Android: `extractNativeLibs`, permissões do upstream,
  `LEANBACK_LAUNCHER` (Android TV), `XBMCBroadcastReceiver`, MediaSession.
- Diretório de perfil **`.kodi`** e biblioteca **`libkodi.so`** — nomes internos
  inalterados (ver §5).

## 3. O que foi REMOVIDO / não incluído

| Item | Situação | Como foi garantido |
|---|---|---|
| Brazuka Play (`plugin.video.BrazukaPlay.*`) | **ausente** | nunca foi adicionado; `verify-apk.py` procura "brazuka" em **todas** as entradas do ZIP |
| Ponte `plugin.video.smarted` | **ausente** | não incluída; verificador bloqueia |
| `service.smarted.bootstrap` | **ausente** | não incluído; verificador bloqueia |
| `resource.uisounds.silencio` | **ausente** | não incluído; verificador bloqueia |
| Skin Nova TV (`skin.novatv`) | **ausente** | verificador exige que o único `skin.*` seja `skin.estuary` |
| `skin.estilo.personalizado` / `skin.smartedtv.*` | **ausente** | idem |
| Titan Bingie Mod (`skin.titan*`) | **ausente** | idem |
| Perfil pronto (`assets/smarted/profile.zip`) | **ausente** | verificador reprova `assets/smarted/*` |
| Perfil antigo do Dropbox (`files.zip`, `backup_part_*`) | **não usado** | ver `INSPECAO-DROPBOX.md` §5 |
| Atalhos/caminhos fixos do Brazuka | **inexistentes** | nada foi configurado; o app inicia “de fábrica” |
| Teclado Android nativo (`patches/…keyboard.patch`) | **não aplicado** | é personalização; fora do escopo desta etapa |
| Add-ons de terceiros em geral | **ausentes** | só os nativos do Kodi |

Resultado verificável: o APK tem **exatamente um** add-on de skin
(`skin.estuary`) e **nenhum** `plugin.video.*`.

## 4. O que foi PERSONALIZADO

Só identidade visual/textual. Nenhuma lógica.

| Elemento | Antes | Depois | Onde |
|---|---|---|---|
| Nome do app (launcher, Android TV, Recentes, Ajustes do Android) | Kodi | **SMARTEDTV** | `tools/android/packaging/xbmc/strings.xml.in` (`app_name`, `search_hint`) |
| Splash nativa — texto | "Starting Kodi..." | "Starting SMARTEDTV..." | `Splash.java.in` |
| Diálogo de permissões de arquivos | "Kodi requires access…" | "SMARTEDTV requires access…" | `Splash.java.in` |
| Tags de log (logcat) | Kodi | SMARTEDTV | `Splash.java.in`, `Main.java.in` |
| Tela inicial / "Sobre" | "Kodi media center", "About Kodi" | "SMARTEDTV media center", "About SMARTEDTV" | `strings.po` (en_gb + pt_br) |
| Informações do sistema | `Kodi 21.3.0 …` | **`SMARTEDTV 21.4.0 …`** | `GUIWindowSystemInfo.cpp` via `CSysInfo::GetDisplayName()` |
| Nome padrão do aparelho (zeroconf/UPnP) | Kodi | SMARTEDTV | `system/settings/settings.xml` |
| Descrição da skin em Complementos | "Kodi's default skin" | "SMARTEDTV default skin" | `skin.estuary/addon.xml` |
| Splash da GUI | splash laranja do Kodi | arte oficial SMARTEDTV | `media/splash.jpg` |
| Splash nativa (Android) | arte do Kodi | arte oficial SMARTEDTV | `media/applaunch_screen.png` |
| Ícones do launcher (6 densidades) | ícone Kodi | selo oficial SMARTEDTV | `tools/android/packaging/media/drawable-*/ic_launcher.png` |
| Banner Android TV | banner Kodi | arte oficial | `media/banner.png`, `drawable-xhdpi/banner.png` |
| Marca na Home/Login da Estuary | `vendor_logo.png` do Kodi | arte oficial | `media/vendor_logo.png` |
| Ícone de evento/notificação | `vendor_icon.png` do Kodi | arte oficial | `media/vendor_icon.png` |
| Ícones internos (`icon16…256`) | ícones Kodi | arte oficial | `media/icon*` |
| Empresa/desenvolvedor (metadados) | XBMC Foundation / Team Kodi | SMARTEDTV | `version.txt` |

**Nenhum arquivo de arte foi inventado**: todos derivam de
`assets/brand/source/splash.jpg` (material da marca já existente no repositório,
vindo do Dropbox). Ver `INSPECAO-DROPBOX.md` §4.

## 5. Por que `APP_NAME` NÃO foi renomeado (decisão técnica)

Esta é a decisão mais importante do projeto e ela **contraria o caminho óbvio**.

Trocar `APP_NAME Kodi` → `SMARTEDTV` no `version.txt` parece a forma "limpa" de
renomear o app, mas o Kodi usa essa variável para muito mais que texto:

| Uso de `APP_NAME` | Consequência de renomear |
|---|---|
| nome de `libkodi.so` | vira `libsmartedtv.so` — precisa combinar com `android.app.lib_name` e com o `System.loadLibrary()` do `Main.java`; qualquer descompasso = app não abre |
| **diretório de perfil** (`.kodi`) | vira `.smartedtv`; **todo** o perfil existente do usuário fica órfão (add-ons, fontes, playlists, biblioteca) |
| `assets/addons/kodi.binary.*` | os add-ons binários do motor continuam com id `kodi.*`; a resolução pode falhar |
| `KODI_HOME`, `KODI_BIN_HOME`, `KODI_DATA`, `PYTHONHOME` | caminhos de inicialização do motor nativo |
| `APP_NAME_LC` em `cmake/scripts/android/*` | caminhos de instalação e empacotamento |

A instrução do projeto é explícita: *"Não altere indiscriminadamente
identificadores internos, nomes de pacotes, namespaces, caminhos, bibliotecas ou
referências utilizadas pelo funcionamento do Kodi"* e *"Preserve o identificador
do aplicativo"*.

Por isso o patch mantém `APP_NAME`, `APP_NAME_LC` e `APP_PACKAGE` **intactos** e
troca apenas os **textos de exibição**, no ponto exato onde são consumidos. O
resultado é o requerido — o usuário vê SMARTEDTV em todo lugar — sem renomear
`libkodi.so`, sem criar um `.smartedtv` paralelo e sem quebrar a atualização.

Isso é verificado: `patch-source.py` aborta se `APP_NAME` ou `APP_PACKAGE`
estiverem diferentes de `Kodi`/`org.xbmc.kodi`, e `verify-apk.py` reprova o APK se
`libkodi.so` não estiver presente.

## 6. Instalação e atualização — o que é verdade

| Cenário | Funciona? | Por quê |
|---|---|---|
| Instalar do zero em aparelho arm64, Android 5+ | **Sim** | ABI e minSdk do upstream |
| Atualizar uma instalação feita com **esta** chave de teste (`smarted-tv-test`, builds 1.0.15/1.0.16 e posteriores) | **Sim**, preservando dados | mesmo `applicationId` (`org.xbmc.kodi`) + mesma assinatura + `versionCode` maior (2104000 > 2103001/2103002) |
| Atualizar uma instalação do **Kodi oficial** (Play Store ou kodi.tv) mantendo os dados | **Não** | assinatura oficial (`f517b44b…`) ≠ chave de teste deste projeto. O Android recusa a atualização com `INSTALL_FAILED_UPDATE_INCOMPATIBLE`. Seria necessário desinstalar (perdendo dados) |
| Atualizar builds do projeto assinados com **outra** chave (ex.: 1.0.13/1.0.14, KODE) | **Não** | chaves anteriores diferentes; ver `README.md` §Compatibilidade |
| Convivir com o Kodi oficial no mesmo aparelho | **Não** | mesmo `applicationId` |

> A chave de produção do Kodi **não está disponível** neste repositório nem no
> Dropbox (só a chave de teste `smarted-tv-test.jks`). Portanto **não** é possível
> prometer atualização sobre o Kodi oficial. Para isso seria preciso (a) obter a
> chave oficial — impossível, é privada do Team Kodi — ou (b) trocar o
> `applicationId` e aceitar instalação paralela, com perfil novo. Nenhuma das duas
> foi feita porque ambas contrariam a instrução de preservar o identificador.

## 7. Limitações encontradas

1. **Assinatura**: só a chave de teste está disponível (§6).
2. **Sandbox de desenvolvimento sem rede para SDK/NDK**: a compilação roda na CI
   do GitHub (ubuntu-22.04). Ver `AMBIENTE.md` §7.
3. **Sem aparelho físico**: instalação/execução validadas no emulador (API 30,
   x86_64). Um APK x86_64 **não** é o mesmo binário do arm64 entregue; o teste
   prova instalação, inicialização, splash e Home, **não** aceleração de vídeo
   real nem reprodução em hardware do usuário.
4. **Sem KVM no sandbox local**: o teste de emulador roda na CI.
5. **Traduções**: `en_gb` e `pt_br` têm os textos de marca trocados. Outros ~80
   idiomas embarcados mantêm "Kodi" em textos internos de add-ons (ex.: descrição
   do Version Check). Isso **não** aparece na navegação principal, mas é uma
   identificação residual conhecida — ver §8.
6. **`service.xbmc.versioncheck`**: add-on opcional do Kodi que consulta
   `kodi.tv` para avisar de novas versões. Está embarcado (é do upstream) e pode
   exibir texto mencionando "Kodi" **se** o usuário habilitar o check de versão.
   Não foi removido porque é recurso nativo; pode ser desabilitado em
   Complementos → Meus complementos → Serviços.
7. **Reprodução/VOD**: nada é pré-configurado. O app entrega a base limpa; a
   configuração de fontes/playlists é feita pelo usuário.

## 8. Identificações residuais de "Kodi" (honestidade técnica)

Este projeto **não afirma** que a palavra "Kodi" desapareceu de todos os bytes do
APK. Ela permanece, deliberadamente, onde é identificador interno ou licença, e
residualmente em pontos que não valem o risco de alteração:

| Onde | Aparece? | Decisão |
|---|---|---|
| Nome do app, splash, Home, Sobre, info do sistema | **Não** | trocado |
| Caminho do motor (`libkodi.so`), diretório `.kodi`, ids `kodi.binary.*`, `repository.xbmc.org` | **Sim** | **mantido de propósito** (§5) — renomear quebra o app/dados |
| Avisos de licença GPL e créditos do código-fonte | **Sim** | **mantido** — obrigação legal, o Kodi é GPL |
| Descrições de add-ons nativos em idiomas que não en/pt | **Sim** | não traduzidas; só metadados em Complementos |
| `kodi.tv` em textos de ajuda/doação de add-ons nativos | **Sim** | conteúdo do upstream; não é a identidade do app |
| Log interno (`kodi.log`, tags de log interna do motor) | **Sim** | nome de arquivo de log do motor; alterar muda caminhos de diagnóstico |
| Eventual aviso do `versioncheck` (se habilitado) | **Sim** | add-on nativo opcional (§7.6) |

O critério aplicado: **o que o usuário vê como nome do aplicativo** virou
SMARTEDTV; **o que é identificador, caminho ou obrigação legal** ficou como está.

## 9. Situação final

| Pergunta | Resposta |
|---|---|
| É o Kodi real, compilado do código-fonte? | **Sim** — `make apk` sobre `21.3-Omega` |
| Preserva navegação/configurações/reprodução? | **Sim** — nada de lógica foi alterado |
| Tem identidade SMARTEDTV? | **Sim** — nome, splash, ícones, banner, Home |
| Tem Brazuka Play / add-ons de conteúdo? | **Não** |
| Tem skin Nova TV / Titan / outras? | **Não** — só `skin.estuary` |
| Vem com perfil pré-configurado? | **Não** |
| Dá para adicionar playlists/fontes/widgets depois? | **Sim** — é o Kodi nativo |
| Pronto para instalar? | **Sim** (arm64, Android 5+) |
| Atualiza o Kodi oficial sem perder dados? | **Não** — assinatura diferente (§6) |

Ver `TESTES.md` para o que foi efetivamente executado e `ENTREGA.md` para o
resumo dos arquivos.
