# Checkpoint Oficial — APK Padrão (~264 MB)

Ponto de referência oficial do **APK Universal** mantendo 100% do funcionamento aprovado em celular e projetor (`v1.0.154-universal`) e adicionando compatibilidade completa para **TV Stick** e **TV Box** (remoção de `uses-feature` obrigatória `screen.landscape` contra erro *"App não instalado"*, detecção real via `build.prop`/permissões Android sem `subprocess`, reserva dupla GitHub `SMARTEDTV-universal.apk` + `SMARTEDTV.apk` e teclas `<nav_back>`/`<gamepad>` para controles Bluetooth e 2.4GHz):

- **Versão / Tag Padrão Atual:** `v1.0.155-universal` (`VERSION_NAME="1.0.155"`, `VERSION_CODE=2103141`)
- **Commit Git do APK:** `80bc6f72fe700732cc4007630f65ebbaa5c1fe8b`
- **GitHub Actions Run:** `https://github.com/msmacrosmart-cpu/KODE/actions/runs/44798224758`
- **Release Oficial (Latest):** `https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.155-universal`
- **Download Direto do APK:** `https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.155-universal/SMARTEDTV-universal.apk`
- **Tamanho Exato:** `264.848.723` bytes (~264 MB)
- **SHA-256:** `7f7d7eda5716d279a056ecb3e3045420470548dd5c7cd5f5d6febbc9855fb5e0`

## Como restaurar este checkpoint
```bash
git checkout 80bc6f72fe700732cc4007630f65ebbaa5c1fe8b
```

---

### Histórico de checkpoints anteriores
- `v1.0.154-universal` (`VERSION_CODE=2103140`, commit `99db8974698248044df859f17e39cb6ba8ea87a6`, `264.844.625` bytes, SHA-256 `ba24d7fbcc4722348880c87644c27c5ea0afc4bfb798d6fcb66a51cc642ff5fa`)
- `v1.0.149-universal` (`VERSION_CODE=2103135`, commit `fcbc2c0a5c530fdb7133d80049acef1e54e33233`, `264.844.534` bytes, SHA-256 `9e7cb53d1a89e168938ca87dcd55524b0fb4c8c795de9c82b4ed211e6b1cf814`)
