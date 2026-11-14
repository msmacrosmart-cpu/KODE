# App de anúncios 1.0.4 — agora também o instalador do SMARTEDTV

Um único APK leve (~5 MB) faz o papel de **porta de entrada** e de **anúncios**.
O usuário instala primeiro o `SMARTEDTV-Anuncios`, abre o ícone e o app baixa e
instala o SMARTEDTV (Kodi). Depois disso a TV volta a chamar o app pelos
`StartAndroidActivity` da ponte, exatamente como na 1.0.3.

## As duas decisões do `LauncherActivity`

| Intent que chega | Para onde vai |
|---|---|
| data `smartedtv://ads/preroll` ou `…/appopen` (ponte) | `PreRollActivity` / `AppOpenActivity` — **inalterado** |
| ícone do app (sem data) | Kodi instalado e atualizado → abre o SMARTEDTV; senão → `BoasVindasActivity` |

O ícone do app **nunca** abre anúncio; a ponte **nunca** cai no instalador.
São caminhos separados de propósito, para não mexer no que já funciona.

## O que a tela de boas-vindas faz

1. **Kodi presente e atualizado** → “SMARTEDTV instalado”, botão *Abrir SMARTEDTV*.
2. **Kodi ausente** → baixa sozinho (começa ~1,5 s depois de abrir) com barra de
   progresso em MB e %, e ao terminar **abre a tela de instalação do Android**.
3. **Kodi velho** (versionCode menor que o `codigo=` do `apk-url.txt`) → oferece
   atualizar, mesmo fluxo do item 2.
4. **Falhou** → mostra o motivo (sem espaço, HTTP, link etc.) e *Tentar de novo*.

Detalhes técnicos que evitam as falhas clássicas:

- `DownloadManager` do sistema (não carrega 242 MB na memória; sobrevive ao app
  ir para segundo plano; segue o redirecionamento GitHub → CDN);
- destino em `getExternalFilesDir(DIRECTORY_DOWNLOADS)` — pasta do app, **sem
  permissão de armazenamento** em nenhuma versão;
- instalação por **content:// via FileProvider** (desde o Android 7 `file://`
  estoura `FileUriExposedException`);
- Android 8+: `canRequestPackageInstalls()` + atalho para
  *Configurações → instalar apps desconhecidos* deste app;
- o pacote `org.xbmc.kodi` está em `<queries>` — sem isso o Android 11+ esconde
  o app e a resposta seria sempre “não instalado”.

## Como trocar o APK que ele distribui

Editar **uma** linha em `android/smarted-ads/apk-url.txt`:

```
url=https://github.com/msmacrosmart-cpu/KODE/releases/download/<tag>/<arquivo>.apk
codigo=<versionCode>
```

O build falha (de propósito) se o link não for `https://….apk`, se a release ou o
anexo não existirem, ou se o `codigo` for inválido. Também dá para sobrescrever
sem editar o arquivo: `-PapkUrl=… -PapkCodigo=…`.

## Checklist de teste na TV

1. Desinstalar o SMARTEDTV (se estiver instalado) e instalar só o
   `SMARTEDTV-Anuncios-1.0.4.apk`.
2. Abrir o ícone → “Bem-vindo ao SMARTEDTV” e a barra de progresso andando.
3. Ao chegar em 100% → tela do Android “Deseja instalar?”. Se aparecer o aviso
   de segurança, autorizar para este app e voltar (o app reabre a instalação
   sozinho ao voltar).
4. Instalar, abrir o SMARTEDTV e conferir que o anúncio de abertura aparece.
5. Abrir o ícone do app de anúncios de novo → deve **abrir o SMARTEDTV direto**.
6. `adb logcat -s SmartAds` mostra `Instalador:`, `BoasVindas:` e `LauncherActivity:`.
