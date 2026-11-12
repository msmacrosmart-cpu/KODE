# Testes executados

Este documento lista **o que foi realmente executado**, com evidência, e o que
**não** foi — sem tratar "gerou o APK" como prova de funcionamento.

## 0. Legenda

- ✅ executado e aprovado
- ❌ executado e reprovado (com a correção aplicada)
- ⚠️ executado com ressalva
- ⬜ não executado (motivo explícito)

## 1. Inspeção do material de origem

| # | Teste | Resultado | Evidência |
|---|---|---|---|
| 1.1 | Inventário completo do Dropbox (raiz + `/SMARTED-TV-privado`) | ✅ | 14 entradas listadas, ver `INSPECAO-DROPBOX.md` §1 |
| 1.2 | Confirmar que `kodi-21.3-Omega-arm64-v8a (1).apk` é duplicata | ✅ | mesmo `content_hash` `043666a7…` |
| 1.3 | Ler `package`, `versionName`, `versionCode`, `minSdk`, `targetSdk` do APK de referência | ✅ | `org.xbmc.kodi`, `21.3`, `2103000`, `21`, `34` |
| 1.4 | Confirmar ABI única e presença de `libkodi.so` | ✅ | `arm64-v8a`, 46 `.so`, incluindo `libkodi.so` |
| 1.5 | Conferir SHA-256 do APK de referência | ✅ | `34e7526705a038fa12f70161d0c1cc38f10deb0fee305b46fbd46ff015d05b44` — igual ao registrado no `README.md` do projeto |
| 1.6 | Inspecionar `Kodi.for.Android.21.3.zip` (fonte decodificada) para achar onde o nome é usado | ✅ | `res/values/strings.xml`, `activity_splash.xml`, `Splash.java` |
| 1.7 | Identificar no código-fonte 21.3 todos os usos de `APP_NAME`/`GetAppName()` | ✅ | 33 ocorrências mapeadas; ver `RELATORIO-INTEGRIDADE.md` §5 |
| 1.8 | Verificar quais arquivos mudam se `APP_NAME` for renomeado | ✅ (descoberta crítica) | `libkodi.so` e o perfil `.kodi` — motivo da decisão cirúrgica |
| 1.9 | Comparar as três fontes de versão (APK, zip, builds antigos) | ✅ | todas 21.3 (`21.3-Omega`) |

## 2. Identidade visual (geração de recursos)

| # | Teste | Resultado | Evidência |
|---|---|---|---|
| 2.1 | Gerar todos os recursos a partir da arte oficial | ✅ | `make-brand-assets.py` → 19 arquivos, nenhum desenhado à mão |
| 2.2 | Conferir dimensões exigidas pelo Kodi/Android | ✅ | splash 1920×1080, banner 320×180, launcher 36/48/72/96/144/192, `vendor_logo` 465×128, `vendor_icon` 128×128 |
| 2.3 | Primeira tentativa: recortar o selo sem a barra do lockup | ❌ | gerou emenda visível no círculo — **descartada** |
| 2.4 | Segunda tentativa: espelhar a banda da barra | ❌ | deformou o "S" — **descartada** |
| 2.5 | Solução final: arte oficial completa, fundo preto puro | ✅ | inspeção visual do `splash.jpg` e dos ícones aprovada |
| 2.6 | Determinismo (mesma entrada → mesmos bytes) | ✅ | duas execuções seguidas produzem arquivos idênticos |

## 3. Aplicação da identidade no código-fonte

| # | Teste | Resultado | Evidência |
|---|---|---|---|
| 3.1 | `patch-source.py` sobre a árvore 21.3 limpa | ✅ | 19 alterações aplicadas, nenhum erro de âncora |
| 3.2 | Guarda: aborta se `APP_NAME`/`APP_PACKAGE` mudarem | ✅ | verificação explícita no script |
| 3.3 | Guarda: aborta se `ADDON_API` mudar | ✅ | verificação explícita |
| 3.4 | Idempotência (rodar duas vezes não corrompe) | ✅ | segunda execução detecta a marca já aplicada |
| 3.5 | Diff completo contra o upstream | ✅ | 25 arquivos, todos esperados (ver saída do `diff -rq`) |
| 3.6 | Compilar a mudança de C++ isoladamente (`GetDisplayName`) | ✅ | `g++ -std=c++17 -Wall -Wextra` sem warnings; imprime `SMARTEDTV 21.4.0 …` |
| 3.7 | Chaves de `version.txt` validadas contra o arquivo real | ✅ | primeira versão usava nomes `APP_VERSION_*`; corrigida para `VERSION_*` |
| 3.8 | `Splash.java.in` / `strings.xml.in` resultantes | ✅ | revisão do diff: sem `@APP_NAME@` remanescente nos textos |

## 4. Ambiente de compilação

| # | Teste | Resultado | Evidência |
|---|---|---|---|
| 4.1 | Sintaxe de todos os shell scripts (`bash -n`) | ✅ | `setup-build-env.sh`, `build-apk.sh`, `smoke-emulador.sh` |
| 4.2 | Compilação de todos os scripts Python (`ast.parse`) | ✅ | 3 scripts |
| 4.3 | YAML dos dois workflows | ✅ | `yaml.safe_load` OK, jobs reconhecidos |
| 4.4 | Provisionamento de SDK/NDK/JDK na CI | ✅ | run 43204690500, passos 1–3 verdes |
| 4.5 | Geração das artes na CI | ❌ → ✅ | run 43204217299 falhou (Pillow ausente); corrigido no run 43204690500 |
| 4.6 | Download do pt-BR oficial `repo-resources@omega` na CI | ✅ | passo 5 verde |
| 4.7 | Clone + patch do Kodi 21.3 na CI, com verificação de commit | ✅ | passo 6 verde; `git rev-parse HEAD` = `a3a448d2…` |
| 4.8 | Compilação das dependências (`tools/depends`) | ver §7 | ~40 min de compilação cruzada |
| 4.9 | Compilação do Kodi (`make`) | ver §7 | |
| 4.10 | Empacotamento e assinatura (`make apk`) | ver §7 | |
| 4.11 | Provisionamento local (sandbox) | ⬜ | sem acesso a `dl.google.com`/`mirrors.kodi.tv` neste ambiente; executado na CI |

## 5. Verificação do APK

`smartedtv/tools/verify-apk.py` executa 26 checagens automáticas. Validação do
próprio verificador (prova de que ele **reprova** o que deve reprovar):

| # | Teste | Resultado | Evidência |
|---|---|---|---|
| 5.1 | Rodar o verificador no **APK oficial sem marca** | ✅ (reprovou corretamente) | 23/26 OK; falhas exatamente em `nome exibido = SMARTEDTV`, `versão 21.4.x` e `versionCode 2104000` |
| 5.2 | Rodar no APK compilado com a marca | ver §7 | esperado 26/26 |

Cobertura do verificador:

1. ZIP íntegro (`testzip`).
2. `applicationId` = `org.xbmc.kodi`.
3. nome exibido = `SMARTEDTV`.
4. versão visível = `21.4.x`.
5. `versionCode` = `2104000` (garante atualização sobre 1.0.15/1.0.16).
6. ABI única `arm64-v8a`.
7. `libkodi.so` presente (prova de motor Kodi real e não renomeado).
8. ≥20 bibliotecas nativas.
9. 9 assets obrigatórios (splash, marcas, banner, ícone, skin, manifest, `libkodi.so`, `classes.dex`).
10. splash nativa presente.
11. ícones de launcher em várias densidades.
12. nenhum add-on proibido (`brazuka`, `smarted`, `novatv`, `titan`, …).
13. **somente** `skin.estuary` como skin.
14. `repository.xbmc.org` mantido.
15. nenhum arquivo com "brazuka" no nome.
16. nenhum perfil pré-configurado (`assets/smarted/*`).
17. bloco de assinatura v1 presente.
18. `MANIFEST.MF` presente.

## 6. Instalação e execução

| # | Teste | Resultado | Evidência |
|---|---|---|---|
| 6.1 | `adb install` no emulador | ver §7 | workflow `smartedtv-emulator-test.yml` |
| 6.2 | App abre e permanece vivo | ver §7 | |
| 6.3 | Splash SMARTEDTV aparece | ver §7 | `tela-splash.png` |
| 6.4 | Home da Estuary carrega (`Loading skin file: Home.xml`) | ver §7 | `tela-home.png`, logcat |
| 6.5 | Nome SMARTEDTV no pacote | ver §7 | `launcher.txt` |
| 6.6 | Configurações abrem | ver §7 | `tela-configuracoes.png` |
| 6.7 | Nenhum add-on proibido no perfil | ver §7 | `addons-instalados.txt` |
| 6.8 | Reprodução de vídeo real / aceleração de hardware | ⬜ | exige aparelho com GPU real; o emulador usa `swiftshader` e um APK **x86_64**, não o arm64 entregue |
| 6.9 | Instalação/atualização no aparelho do cliente | ⬜ | depende do usuário; ver `RELATORIO-INTEGRIDADE.md` §6 |

## 7. Resultado do build e dos testes de execução

Preenchido ao final da execução — ver `RESULTADO-BUILD.md`, que é gerado com os
números reais (run, duração, SHA-256, saída do verificador e do emulador). Se a
compilação não tiver concluído, esse arquivo dirá explicitamente **o que não foi
executado e por quê**, em vez de supor sucesso.

## 8. O que este conjunto de testes NÃO prova

- Que o vídeo reproduz com aceleração de hardware no aparelho do usuário.
- Que a atualização sobre uma instalação existente funciona — isso depende da
  assinatura, e só a chave de teste está disponível (ver
  `RELATORIO-INTEGRIDADE.md` §6).
- Que não há nenhuma string "Kodi" em nenhum canto do APK — há, de propósito,
  nas licenças e em identificadores internos (ver §8 do relatório de integridade).
- Que a interface ficou "bonita" em 4K/HDR — nenhuma validação visual em TV real.
