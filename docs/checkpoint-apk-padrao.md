# Pontos de Referência (Checkpoints) do APK Universal SMARTEDTV

Este documento mantém o registro de referência das entregas estáveis do APK universal na branch `arena/5c219515-kode`, permitindo restauração imediata caso necessário.

## 1. Checkpoint Oficial do Pacote Compacto (~265 MB) — `v1.0.149-universal`
- **Commit:** `fcbc2c0a5c530fdb7133d80049acef1e54e33233`
- **Workflow Run:** `https://github.com/msmacrosmart-cpu/KODE/actions/runs/44680840391`
- **Release:** `https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.149-universal`
- **Download direto:** `https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.149-universal/SMARTEDTV-universal.apk`
- **Tamanho / SHA-256:** `264844534` bytes (~265 MB, sem YouTube nem MP3 Streams no perfil embarcado) / `9e7cb53d1a89e168938ca87dcd55524b0fb4c8c795de9c82b4ed211e6b1cf814`
- **Destaques:** pacote enxuto sem YouTube/MP3 Streams, validação de código VIP sem travar cookie/caixa, 2º vídeo com anúncio sem congelar e anúncios VAST na TV ao vivo.

## 2. Release Consolidada sobre a Base Compacta (~265 MB) — `v1.0.151-universal` (`versionCode = 2103137`)
- **Base exata:** `v1.0.149-universal` (`fcbc2c0`, ~265 MB sem YouTube e MP3 Streams no APK) +
  1. **Bloqueio de repetição de anúncios nas tentativas da TV ao vivo:** após selecionar o canal, quedas/erros de stream (`onPlayBackEnded` / `onPlayBackError`), trocas de porta do proxy LAN, reaberturas internas (`ao_vivo._tocar_de_novo` / `ads_vast.restaurar`) e tentativas de opções/rotas do mesmo canal não disparam novo anúncio — anúncios só voltam a rodar após **sair** (`onPlayBackStopped`) ou **escolher outro conteúdo**;
  2. **Limpeza de `.tmp` residuais no boot:** protege contra arquivos temporários truncados caso o app seja interrompido por erro de reprodução.
