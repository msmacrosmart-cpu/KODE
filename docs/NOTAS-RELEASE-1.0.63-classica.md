# SMARTED-TV 1.0.63 (linha clássica) — a ponte dos anúncios, agora com a Intent certa

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
