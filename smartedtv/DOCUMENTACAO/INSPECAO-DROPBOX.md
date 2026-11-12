# Inspeção do material do Dropbox

Registro do que foi encontrado, o que foi inspecionado e por que a base escolhida
foi o **Kodi 21.3-Omega**.

## 1. O que existe no Dropbox

Inventário completo (raiz + `/SMARTED-TV-privado`):

| Item | Tamanho | O que é | Uso neste projeto |
|---|---|---|---|
| `kodi-21.3-Omega-arm64-v8a.apk` | 68.167.494 B | **APK oficial do Kodi 21.3** para arm64 | **Base de referência**: confirmou versão, pacote, ABI e assinatura |
| `kodi-21.3-Omega-arm64-v8a (1).apk` | 68.167.494 B | cópia idêntica (mesmo `content_hash`) | confirmado duplicado, ignorado |
| `Kodi.for.Android.21.3.zip` | 68.037.914 B | **fonte Java/manifest decodificada** do mesmo 21.3 | confirmou `@APP_NAME@`, layout da splash, `activity_splash.xml` |
| `KODE-v1.0.13-teste.apk` | 67.335.246 B | build anterior do projeto (linha "KODE") | histórico; **não** é base |
| `KODE-v1.0.14-arm64-teste.apk` | 67.662.841 B | idem | histórico |
| `SMARTED-TV-v1.0.15-arm64-teste.apk` | 67.759.069 B | primeiro build com identidade SMARTED | referência de identidade e de assinatura |
| `SMARTED-TV-v1.0.16-teclado-arm64-teste.apk` | 71.179.287 B | build com patch de teclado nativo | referência do patch de teclado (`patches/`) |
| `/SMARTED-TV-privado/smarted-tv-test.jks` | 2.730 B | **chave de teste** (alias `smarted-tv-test`) | usada para assinar este build |
| `/SMARTED-TV-privado/backup-v1.0.15/` | — | APK 1.0.15 + cópia da chave | confirma a chave da linha 1.0.15 |
| `files.zip` | 164.663.901 B | pacote de arquivos/perfil de uma versão antiga | **inspecionado e NÃO usado** (contém perfil/addons antigos) |
| `backup_part_aa` + `backup_part_ab` | 94 MB + 70 MB | backup dividido (parcial) de perfil | **NÃO usado** (conteúdo antigo/Brazuka) |
| `skin.estilo.personalizado.zip` | 3.652.678 B | skin personalizada anterior | **NÃO usado** (é personalização antiga) |
| `PREVIEW_KODI.html` | 28.900 B | preview HTML da skin Nova TV | **NÃO usado** (é a skin Nova TV) |

Conclusão do inventário: **não existe material de build alternativo** além dos
documentos que já estão versionados no repositório (`.github/workflows/`,
`docs/`, `tools/kodi/`). O Dropbox contém a base binária, a chave e o histórico
de identidade — que é o que este projeto usa.

## 2. Qual versão do Kodi corresponde ao projeto

Três candidatos foram comparados:

| Candidato | Versão | Origem | Veredito |
|---|---|---|---|
| `kodi-21.3-Omega-arm64-v8a.apk` | 21.3 (`versionCode` 2103000) | APK oficial, assinado pelo Team Kodi | **escolhido** — é o binário de referência |
| `Kodi.for.Android.21.3.zip` | 21.3 | decodificação do mesmo APK | mesma versão, usado para conferir recursos |
| builds `KODE-*` / `SMARTED-TV-1.0.x` | 21.3 + reempacotamento | builds anteriores do projeto | reempacotamentos do 21.3, **não** fonte nova |

Todos apontam para a mesma base: **Kodi 21.3-Omega, tag `21.3-Omega`, commit
`a3a448d26b8d560a65655dab2cd122994dc4e146`**.

Confirmações feitas diretamente no APK de referência:

- `package = org.xbmc.kodi`, `versionName = 21.3`, `versionCode = 2103000`
- `minSdkVersion = 21`, `targetSdkVersion = 34`
- ABI: `arm64-v8a` (46 bibliotecas nativas, incluindo `libkodi.so`)
- assinatura: 1 signatário, certificado do Team Kodi
  (`f517b44b5db5e62a6c1ec55ba47526db7de0d61f6ba26a7987520e293499b8d5`)
- SHA-256 do arquivo: `34e7526705a038fa12f70161d0c1cc38f10deb0fee305b46fbd46ff015d05b44`
  (idêntico ao registrado no `README.md` que já estava no repositório)

## 3. Os "documentos de build" mencionados

O material de build do projeto **está no repositório**, não no Dropbox:

| Documento | O que ensina | O que foi aproveitado |
|---|---|---|
| `README.md` | que os builds anteriores eram reempacotamento, com limitações explícitas | evitamos repetir o erro: aqui o Kodi é compilado |
| `.github/workflows/verify-native-keyboard.yml` | **procedimento completo de compilação do Kodi 21.3 para Android** (SDK/NDK/JDK, `tools/depends`, `make apk`) | é a base literal de `smartedtv/tools/build-apk.sh`; prova que o pipeline funciona no runner (1h05m, verde) |
| `docs/teclado-android.md` | o que o patch de teclado altera e o que **não** foi validado | referência de rigor de validação |
| `docs/emulador-diagnostico.md` | como o emulador se comporta (guisettings, paths) | base de `smoke-emulador.sh` |
| `.github/workflows/home-carrossel-emulator.yml` | emulador API 30 + KVM + coleta de logcat/screenshot | base do `smartedtv-emulator-test.yml` |
| `patches/kodi-21.3-native-android-keyboard.patch` | patch aplicável sobre 21.3 | **não aplicado** (teclado é personalização; fora do escopo desta etapa) |
| `ENTREGA_FINAL/DOCUMENTACAO/RELATORIO_BUILD_RELEASE.md` | declara que o projeto antigo não tinha APK próprio | confirma a necessidade deste build |

Nenhum documento do Dropbox ou do repositório indica uma versão diferente de SDK,
NDK ou JDK; todas as referências convergem para android-34, build-tools 33.0.1,
NDK 21.4.7075529 e JDK 17.

## 4. Identidade visual: quais arquivos oficiais foram usados

| Arquivo no repositório | Origem | Uso |
|---|---|---|
| `assets/brand/source/splash.jpg` (1600×1600) | arte oficial da marca | virou `smartedtv/assets/brand/logo-oficial.jpg` |
| recorte do selo circular (672×678) | derivado da arte acima, sem redesenho | `smartedtv/assets/brand/mark.png` |

Nada foi gerado por IA nem redesenhado. `make-brand-assets.py` apenas redimensiona
e posiciona a arte oficial em fundo preto puro, que é o campo da própria arte.

Detalhe importante: a barra branca horizontal **faz parte do lockup oficial**.
Tentar recortá-la produz uma emenda visível (verificado); por isso o selo é usado
completo, e o fundo é preto puro para casar com a arte.

## 5. O que foi deliberadamente ignorado

Conforme a instrução do projeto, **não** foram usados nem restaurados:

- `files.zip` e `backup_part_aa/ab` (perfil antigo com add-ons)
- `skin.estilo.personalizado.zip` (skin personalizada anterior)
- `PREVIEW_KODI.html` (preview da skin Nova TV)
- `kodi/skin.novatv/`, `kodi/skin.smartedtv.bingie/`, `kodi/addons/*` do
  repositório (ponte Brazuka e bootstrap)
- `plugin.video.BrazukaPlay.*` em qualquer forma
