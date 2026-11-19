#!/usr/bin/env bash
# Reempacota somente overlays + manifesto. O motor já compilado não muda.
set -euo pipefail
cd "$(dirname "$0")/../.."
PROJECT=$PWD
work=${RELEASE_WORK:-$PWD/build/universal}
bt="${ANDROID_HOME:?}/build-tools/35.0.0"
. kodi/addons/service.smarted.bootstrap/smarted_release.py
[[ $VERSION_NAME =~ ^[0-9]+\.[0-9]+\.[0-9]+$ && $VERSION_CODE =~ ^[0-9]+$ ]]
((VERSION_CODE > 2103077 && VERSION_CODE <= 2100000000)) || { echo 'versionCode precisa superar todas as versões até v22' >&2; exit 1; }
# Reutilizar as convenções de assinatura da linha de teste; nunca gerar chave.
. smartedtv/tools/test-signing-env.sh
base="$work/base-v22.apk"
# Duas versoes do MESMO projeto: o celular (linha historica) e a TV. A receita
# abaixo e a mesma para as duas - muda so o marcador que o app le em
# ``variante.py`` e o nome do arquivo publicado. Nada de recompilar o Kodi.
final="$work/SMARTEDTV-universal.apk"
final_tv="$work/SMARTEDTV-tv.apk"

montar() {  # $1 = mobile|tv  $2 = arquivo final
  local variante=$1 saida=$2
  local scratch
  scratch=$(mktemp -d "$work/montagem.XXXXXX")
  python3 tools/kodi/atualizar-apk-v17.py --apk "$base" --saida "$scratch/overlay.apk" \
    --variante "$variante"
# Receita IDENTICA a da v22/v21, que instalou no aparelho: o manifesto muda
# so versao/codigo (o minSdk fica o da base) e o alinhamento e feito pelo
# align-apk.py, o mesmo daquela entrega. Nao elevar nem reduzir minSdk aqui.
  python3 tools/kodi/ajustar-versao-apk.py "$scratch/overlay.apk" "$scratch/raw.apk" \
    --de 1.0.87 --de-codigo 2103073 --para "$VERSION_NAME" --para-codigo "$VERSION_CODE"
  python3 tools/kodi/align-apk.py "$scratch/raw.apk" "$scratch/aligned.apk"
  "$bt/apksigner" sign --ks "$KODI_ANDROID_STORE_FILE" --ks-key-alias "$KODI_ANDROID_KEY_ALIAS" \
    --ks-pass env:KODI_ANDROID_STORE_PASSWORD --key-pass env:KODI_ANDROID_KEY_PASSWORD \
    --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true --v4-signing-enabled false \
    --out "$scratch/signed.apk" "$scratch/aligned.apk"
  "$bt/zipalign" -c -P 16 4 "$scratch/signed.apk"
  "$bt/apksigner" verify "$scratch/signed.apk"
  # A partir de API 26 o verificador normalmente pula o v1: testar também a faixa v1.
  "$bt/apksigner" verify --min-sdk-version 21 --verbose --print-certs "$scratch/signed.apk" > "$work/signature-$variante.txt"
  for scheme in 1 2 3; do grep -E "^Verified using v$scheme scheme .*: true$" "$work/signature-$variante.txt"; done
  grep -Fx 'Number of signers: 1' "$work/signature-$variante.txt"
  grep -F 'certificate SHA-256 digest: 855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a' "$work/signature-$variante.txt"
  "$ANDROID_HOME/cmdline-tools/latest/bin/apkanalyzer" manifest print "$scratch/signed.apk" > "$work/manifest.xml"
  python3 smartedtv/release/verify.py "$base" "$scratch/signed.apk" "$work/manifest.xml" "$VERSION_NAME" "$VERSION_CODE"
  # O marcador tem de estar NO APK assinado e legivel: e o que decide a pasta
  # do Dropbox, o pacote logico e o anuncio de cada versao.
  unzip -p "$scratch/signed.apk" assets/smartedtv-variante.txt | grep -qx "$variante"
  python3 tools/kodi/simular-boot-tela-entrada.py --apk "$scratch/signed.apk"
  mv "$scratch/signed.apk" "$saida"
  rm -rf "$scratch"
  sha256sum "$saida"
}

montar mobile "$final"
# A TV sai do MESMO APK base, com o mesmo certificado e as mesmas ABIs: o que
# muda e o marcador embutido (variante.py) - pasta SMARTEDTV-ON, anuncio de
# video e nada de AdMob.
montar tv "$final_tv"
