# Pontos de Referência (Checkpoints) do APK Universal SMARTEDTV

Este documento mantém o registro de referência das entregas estáveis do APK universal na branch `arena/5c219515-kode`, permitindo restauração imediata caso necessário.

## 1. Referência de Reabertura Provada — `v1.0.148-universal`
- **Commit:** `fdc2b98`
- **Workflow Run:** `https://github.com/msmacrosmart-cpu/KODE/actions/runs/44670994546`
- **Release:** `https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.148-universal`
- **Download direto:** `https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.148-universal/SMARTEDTV-universal.apk`
- **Destaques:** `classes*.dex` e `profile-manifest.txt` 100% idênticos ao `base-v22.apk`, navegação D-pad da `Home.xml` e `MyVideoNav.xml`, Elementum + Cloudflare DoH e reabertura limpa do app validada em aparelho real.

## 2. Checkpoint VIP + VAST 2º Vídeo + TV Ao Vivo — `v1.0.149-universal`
- **Commit:** `fcbc2c0a5c530fdb7133d80049acef1e54e33233`
- **Workflow Run:** `https://github.com/msmacrosmart-cpu/KODE/actions/runs/44680840391`
- **Release:** `https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.149-universal`
- **Download direto:** `https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.149-universal/SMARTEDTV-universal.apk`
- **Tamanho / SHA-256:** `264844534` bytes / `9e7cb53d1a89e168938ca87dcd55524b0fb4c8c795de9c82b4ed211e6b1cf814`
- **Destaques:** validação de código VIP sem travar cookie/caixa, remoção de YouTube e MP3 Streams, 2º vídeo com anúncio sem congelar e anúncios VAST na TV ao vivo.

## 3. Release Consolidada — `v1.0.150-universal` (`versionCode = 2103136`)
- **Base:** soma integral das melhorias aprovadas nas `1.0.148` e `1.0.149` +
  1. **Reabertura restaurada ao estado exato da `1.0.148` (`fdc2b98`)**: `classes*.dex` e `profile-manifest.txt` 100% intocados em relação à `base-v22.apk`, sem escrita concorrente em `Addons*.db` nas reaberturas e com limpeza automática de `.tmp` residuais no boot;
  2. **Bloqueio de repetição de anúncios nas tentativas da TV ao vivo**: selecionado o canal, quedas de stream (`onPlayBackEnded` / `onPlayBackError`), trocas de porta do proxy LAN, reaberturas internas (`ao_vivo._tocar_de_novo` / `ads_vast.restaurar`) e tentativas de opções/rotas do mesmo canal não disparam novo anúncio — anúncios só voltam a ser avaliados após **sair** (`onPlayBackStopped`) ou **escolher outro conteúdo**.
