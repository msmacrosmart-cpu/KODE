# SMARTEDTV 1.0.89 (v19) — entrega para instalar no projetor

O APK v18 foi verificado de volta no CI: ZIP íntegro, `zipalign` OK, assinatura
v1/v2/v3, pacote `smartedtv.full`, minSdk 21, targetSdk 34, ABIs `arm64-v8a` e
`armeabi-v7a`. Mesmo assim o Android 11 do projetor recusou a instalação em duas
tentativas. Como o pacote é válido, a v19 ataca as três causas restantes de
rejeição **no aparelho**, sem apagar dados:

1. **`versionCode` novo:** 1.0.89 / **2103075**, para o Android não tratar a
   instalação como repetição/downgrade de uma tentativa anterior incompleta.
2. **APK só com a ABI certa:** além do universal, há `arm64` e `arm32`, menores
   e sem a biblioteca da outra arquitetura. Isso elimina rejeição de extração
   de 45 `.so` de duas ABIs em projetor de pouca memória.
3. **Assinatura sem o bloco v3:** a variante `v2` usa v1+v2, para firmware
   Android 11 que rejeita o bloco v3.

Todos usam **o mesmo pacote, a mesma chave** (`855de171...`) e o mesmo
`versionCode`; instalar uma variante por cima da outra é permitido.

## Downloads

Tag: https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.89-instalacao-v19

| Arquivo | Bytes | SHA-256 | Quando usar |
|---|---:|---|---|
| [universal](https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.89-instalacao-v19/SMARTEDTV-atual-v19-instalacao-universal.apk) | 285.488.378 | `47268c72807de765effc1ebe0512148a01d31b1b8837c05a6dad6a80d90cf13d` | não sabe a ABI; inclui arm64+arm32 |
| [arm64](https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.89-instalacao-v19/SMARTEDTV-atual-v19-instalacao-arm64.apk) | 250.377.505 | `f0693dcd4ec176f23c8adb5668c33dcb2b25bd6523941a8e8d79bab98443d170` | AIDA64 mostra `arm64-v8a` |
| [arm32](https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.89-instalacao-v19/SMARTEDTV-atual-v19-instalacao-arm32.apk) | 248.472.952 | `04e838112bf1d7a6aec169d29abd2a39b3ab7335cbe047e4672918efe424f118` | AIDA64 mostra só `armeabi-v7a` |
| [v2](https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.89-instalacao-v19/SMARTEDTV-atual-v19-instalacao-v2.apk) | 285.488.378 | `ed9d8e481ed1b7918e3058e851cbe6f099929cd9502ec4c03951893b3d322d11` | as anteriores falham por assinatura/firmware |

`hashes-v19.txt` também está na release.

## Ordem de teste no projetor

1. Baixe **arm64** (mais provável em Android 11) e instale do armazenamento
   interno. Se a ABI for 32-bit, use **arm32**.
2. Se falhar, tente **universal**.
3. Se ainda falhar, tente **v2** (assinatura v1+v2).
4. Se todas falharem, o problema não é o APK: veja a ABI no AIDA64
   (`x86`/`x86_64` não roda ARM) ou o código do `adb install`.

Nada aqui apaga perfil, VIP ou configurações; é a primeira instalação, então
também não há dados para perder.

## Build

Workflow `build-v17-responsivo.yml`, execução **44192225260**, versão 1.0.89 /
2103075. Testes estáticos, auditorias, testes unitários, boot simulado,
variantes, alinhamento e assinatura passaram. Não houve teste em aparelho
físico.
