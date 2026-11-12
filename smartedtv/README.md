# SMARTEDTV — Kodi 21.3-Omega compilado do código-fonte, com a marca aplicada

**O que é:** o Kodi 21.3-Omega **compilado do código-fonte** para Android
arm64-v8a, com a identidade visual SMARTEDTV (nome, splash, ícones, banner,
marca na Home) e **sem** add-ons de conteúdo, **sem** skin Nova TV e **sem**
perfil pré-configurado.

**O que não é:** não é reempacotamento de APK oficial, não é skin, não é uma
"versão turbinada" com conteúdo.

| | |
|---|---|
| Base | `xbmc/xbmc` tag `21.3-Omega`, commit `a3a448d2…` |
| Application ID | `org.xbmc.kodi` (**preservado**) |
| Versão exibida | `21.4.0` (Kodi 21.3 com identidade SMARTEDTV) |
| `versionCode` | `2104000` |
| ABI | `arm64-v8a` (Android 5+) |
| Add-ons extras | nenhum (só os nativos do Kodi) |
| Skin | só `skin.estuary` (original) |

## Compilar

```bash
./smartedtv/tools/setup-build-env.sh   # uma vez: JDK 17 + SDK 34 + NDK 21.4.7075529
./smartedtv/tools/build-apk.sh         # compila, assina e verifica
# saída: smartedtv/build/out/SMARTEDTV-21.4-arm64-v8a.apk
```

Recompilar sem refazer as dependências (~40 min → minutos):

```bash
SKIP_DEPENDS=1 ./smartedtv/tools/build-apk.sh
```

Na CI: `.github/workflows/smartedtv-build-source.yml` (~65 min, ubuntu-22.04).
Teste no emulador: `.github/workflows/smartedtv-emulator-test.yml`.

## Documentação

| Arquivo | Conteúdo |
|---|---|
| [`DOCUMENTACAO/AMBIENTE.md`](DOCUMENTACAO/AMBIENTE.md) | ferramentas, versões, dependências, configurações, comando, onde sai o APK |
| [`DOCUMENTACAO/INSPECAO-DROPBOX.md`](DOCUMENTACAO/INSPECAO-DROPBOX.md) | o que existe no Dropbox, qual versão foi escolhida e por quê |
| [`DOCUMENTACAO/RELATORIO-INTEGRIDADE.md`](DOCUMENTACAO/RELATORIO-INTEGRIDADE.md) | preservado × removido × personalizado, limitações, atualização |
| [`DOCUMENTACAO/TESTES.md`](DOCUMENTACAO/TESTES.md) | o que foi realmente testado e o que não foi |
| [`DOCUMENTACAO/RESULTADO-BUILD.md`](DOCUMENTACAO/RESULTADO-BUILD.md) | resultado do build real (run, hash, verificações) |
| [`DOCUMENTACAO/ENTREGA.md`](DOCUMENTACAO/ENTREGA.md) | índice da entrega A/B/C/D |

## Estrutura

```
smartedtv/
├── assets/brand/        artes oficiais (logo 1600×1600 + selo recortado)
├── out/                 recursos gerados (splash, ícones, banner) — versionados
├── tools/               setup, geração de arte, patch, build, verificação, smoke test
├── build/               (gerado) fonte patchado, dependências, APK
└── DOCUMENTACAO/
```

## Decisões que importam

1. **`APP_NAME` não é renomeado.** O Kodi deriva dele o nome de `libkodi.so` e do
   diretório de perfil `.kodi`. Renomear quebraria o carregamento da biblioteca
   nativa e tornaria o perfil do usuário órfão. A marca é aplicada nos **textos de
   exibição**. Detalhes em `RELATORIO-INTEGRIDADE.md` §5.
2. **`applicationId` não muda**, para preservar permissões, assinatura e a
   possibilidade de atualizar instalações de teste.
3. **Nenhuma arte foi inventada**: splash, ícones e banner derivam do arquivo
   oficial da marca que já estava no repositório.
4. **Sem conteúdo**: nada de Brazuka, nada de Nova TV, nada de perfil pronto.

## Estado da entrega

Ver `DOCUMENTACAO/ENTREGA.md` e `DOCUMENTACAO/RESULTADO-BUILD.md` para o
resultado final, incluindo o que não pôde ser validado e por quê.
