# SMARTED-TV 1.0.63 (linha clássica) — ponte dos anúncios corrigida + instalador

## Como instalar (só um arquivo para começar)

1. Baixe **`SMARTEDTV-Anuncios-1.0.4.apk`** (leve, ~4,9 MB) e instale. Ele é o
   **instalador**: ao abrir o ícone, se o SMARTEDTV ainda não estiver no
   aparelho, baixa o APK principal sozinho e abre a tela de instalação do
   Android (autorize “instalar apps desconhecidos” quando ele pedir).
2. O próprio app instala o `SMARTED-TV-v1.0.63-arm64.apk` desta release.
3. Depois disso, abrir o ícone do app de anúncios passa a **abrir o SMARTEDTV
   direto**, e o Kodi volta a chamá-lo pelos gatilhos de anúncio.

Se preferir instalar na mão: instale primeiro o APK de anúncios, depois o do Kodi.

Base: **1.0.62 clássica**. Só o **service.smarted.bootstrap** muda (1.0.12 → 1.0.13).
Vai junto o **APK de anúncios 1.0.3** (modo de teste + launcher + Toasts).

## O segundo bloqueio (e o que ele causava)

A 1.0.62 corrigiu a posição da classe (o `className` é o 9º parâmetro), mas o disparo
continuava morrendo **antes** de chegar lá. Código real do Kodi Omega
(`CXBMCApp::StartActivity`):

```cpp
CJNIIntent newIntent = intent.empty() ?
    GetPackageManager().getLaunchIntentForPackage(package) :   // intent vazio
    CJNIIntent(intent);

if (!newIntent) return false;          // <- sai AQUI, sem olhar o className
...
newIntent.setPackage(package);
if (!className.empty()) newIntent.setClassName(package, className);
startActivity(newIntent);
```

Com o parâmetro **`intent` vazio**, o Kodi procurava a **activity de launcher** do pacote
`smartedtv.full`; o app de anúncios não tinha launcher → `null` → `return false` **silencioso**.
Nenhuma tela abria e nada aparecia no log do Kodi.

## O que mudou

**Na ponte (`smart_ads.py`):**

```
StartAndroidActivity(smartedtv.full,smartedtv.ads.PREROLL,,,,,,,org.smartedtv.ads.PreRollActivity)
                      └ pacote ──┘ └ intent (não pode ser vazio) ┘        └ className ──┘
```

- `intent` sempre preenchido (`smartedtv.ads.PREROLL` / `smartedtv.ads.APPOPEN`).
- **Plano B** disparado junto: `StartAndroidActivity(smartedtv.full,android.intent.action.MAIN,,smartedtv://ads/preroll,,,,,org.smartedtv.ads.LauncherActivity)` — se o
  componente explícito não abrir, o launcher do app resolve pelo data URI.
- Log `[SmartAds]` de cada tentativa + **aviso na tela do Kodi** ("Abrindo anúncio…").
- Marca da abertura com versão (`smartedtv-ads-v2`): a marca gravada pelas 1.0.60/1.0.61
  (quando nada abria) **não bloqueia** mais o pop-up.

**No app de anúncios (1.0.3):**

- **`LauncherActivity`**: dá launcher ao pacote (plano B) e roteia por
  `smartedtv://ads/preroll` / `smartedtv://ads/appopen`.
- **`intent-filter`** com as actions `smartedtv.ads.PREROLL` / `smartedtv.ads.APPOPEN`.
- **Toasts** na abertura de cada tela e no erro ("SMARTEDTV Ads: …"), além do painel de
  diagnóstico com o **código numérico** do AdMob.
- Continua `sensorLandscape` em todas as telas (conferido por `aapt2` no CI: 3 activities).

## Como testar

1. Instale `SMARTEDTV-Anuncios-1.0.3.apk` e depois `SMARTED-TV-v1.0.63-arm64.apk`.
2. Ao abrir o Kodi: aviso "Abrindo anúncio (abertura)" + Toast do app + **anúncio de teste**.
3. Ao dar play em um canal: o vídeo de teste cobre a tela; o conteúdo segue atrás.
4. Se falhar: painel com o código do AdMob na TV, Toast, e `adb logcat -s SmartAds`
   (o `kodi.log` mostra `[SmartAds] disparando …` e `plano B …`).

Se **nem o Toast** do app aparecer, o problema é o disparo (Kodi → app); se o Toast aparecer
e o anúncio não, é o AdMob (aí o painel mostra o código 0/1/2/3/8).

## Arquivos e conferência (11/2026)

| Arquivo | Pacote | Versão / código | Tamanho | sha256 |
| --- | --- | --- | --- | --- |
| `SMARTED-TV-v1.0.63-arm64.apk` | `org.xbmc.kodi` | 1.0.63 / 2103049 | 242.222.254 B | `82c206e3eac9df9068414bc59908449008424927106e87a867e64f90b5bcee8d` |
| `SMARTEDTV-Anuncios-1.0.4.apk` | `smartedtv.full` | 1.0.4 / 5 | 5.119.928 B | ver `SMARTEDTV-Anuncios.sha256` |

Conferência do APK **publicado** (workflow `verificar-classica.yml`, run verde —
relatório em `docs/comparacao-1.0.63.txt`):

- diff do ZIP vs 1.0.62: **0 entradas novas, 0 removidas**, só
  `service.smarted.bootstrap/smart_ads.py` mudou (7.951 → 11.496 B);
- bootstrap embarcado: **1.0.13**;
- anúncios: **13/13 checagens OK** (intent não vazio, plano B, marca `smartedtv-ads-v2`,
  classes da abertura e do pre-roll, gancho `xbmc.Player`, pacote `smartedtv.full`);
- playback: **9/9 OK** (buffermode 1, 50 MB, readfactor 20x, sem troca de modo de vídeo,
  nav-check em segundo plano);
- skin 1.0.18 sem regressão (9201 `570/194`, 9203 `822/194`, 9202 ausente, painéis escuros);
- APK de anúncios da release: `smartedtv.full` 1.0.3/4, com os dois blocos de teste no dex
  e a tag `SmartAds` (orientação `sensorLandscape` confirmada por `aapt2` nas 3 telas no
  build do app).
