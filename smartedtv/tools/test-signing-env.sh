# Configuração LEGADA da chave pública de TESTE; não usar para produção.
# Compartilhada pelos dois builds. PROJECT deve apontar para a raiz do checkout.
DEFAULT_KEYSTORE="$PROJECT/dropbox/smarted-tv-test.jks"
export KODI_ANDROID_STORE_FILE="${KODI_ANDROID_STORE_FILE:-$DEFAULT_KEYSTORE}"
export KODI_ANDROID_STORE_PASSWORD="${KODI_ANDROID_STORE_PASSWORD:-android}"
export KODI_ANDROID_KEY_ALIAS="${KODI_ANDROID_KEY_ALIAS:-smarted-tv-test}"
export KODI_ANDROID_KEY_PASSWORD="${KODI_ANDROID_KEY_PASSWORD:-android}"
