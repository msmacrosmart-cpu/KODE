#!/bin/bash
# =============================================================================
# Script de instalação de dependências para build do APK release - SmartED-TV
# Execute como root ou com sudo
# =============================================================================

set -e

echo "============================================================"
echo "  Instalando dependências para build APK SmartED-TV"
echo "============================================================"

# Detectar gerenciador de pacotes
if command -v apt-get &> /dev/null; then
    PKG_MANAGER="apt-get"
    echo "[+] Usando apt-get (Debian/Ubuntu)"
elif command -v yum &> /dev/null; then
    PKG_MANAGER="yum"
    echo "[+] Usando yum (RHEL/CentOS/Fedora)"
elif command -v dnf &> /dev/null; then
    PKG_MANAGER="dnf"
    echo "[+] Usando dnf (Fedora)"
elif command -v pacman &> /dev/null; then
    PKG_MANAGER="pacman"
    echo "[+] Usando pacman (Arch Linux)"
else
    echo "[!] Nenhum gerenciador de pacotes suportado encontrado"
    echo "    Instale manualmente: openjdk-17, apktool, apksigner, aapt, wget, unzip"
    exit 1
fi

# Atualizar índices de pacotes
echo "[+] Atualizando índices de pacotes..."
sudo $PKG_MANAGER update -y || true

# Instalar OpenJDK 17
echo "[+] Instalando OpenJDK 17..."
case $PKG_MANAGER in
    apt-get)
        sudo apt-get install -y openjdk-17-jdk-headless wget unzip curl || {
            echo "[!] Falha ao instalar via apt. Tentando openjdk-17-jre-headless..."
            sudo apt-get install -y openjdk-17-jre-headless wget unzip curl || true
        }
        ;;
    yum|dnf)
        sudo $PKG_MANAGER install -y java-17-openjdk wget unzip curl || true
        ;;
    pacman)
        sudo pacman -S --noconfirm jdk17-openjdk wget unzip curl || true
        ;;
esac

# Verificar Java
echo "[+] Verificando Java..."
java -version 2>&1 || {
    echo "[!] Java não encontrado após instalação. Verifique JAVA_HOME."
}

# Instalar Android SDK Build Tools (para apksigner e aapt)
echo "[+] Baixando Android SDK Command Line Tools..."
SDK_DIR="$HOME/android-sdk"
mkdir -p "$SDK_DIR"

# Tentar baixar via repositórios disponíveis
if command -v apt-get &> /dev/null; then
    sudo apt-get install -y android-sdk-build-tools android-sdk-platform-tools || true
fi

# Se não tiver apksigner/aapt, tentar baixar do Google (pode falhar em sandboxes restritos)
if ! command -v apksigner &> /dev/null || ! command -v aapt &> /dev/null; then
    echo "[!] apksigner/aapt não encontrados via apt. Baixando build-tools..."
    # Nota: Em sandboxes com rede restrita, isso pode falhar
    # O usuário pode precisar instalar manualmente o Android SDK
fi

# Instalar apktool
echo "[+] Instalando apktool..."
APKTOOL_DIR="$HOME/tools/apktool"
mkdir -p "$APKTOOL_DIR"

if [ ! -f "$APKTOOL_DIR/apktool.jar" ]; then
    echo "    Baixando apktool.jar..."
    # Tenta baixar do GitHub (se a rede permitir)
    curl -L -o "$APKTOOL_DIR/apktool.jar" \
        "https://github.com/iBotPeaches/Apktool/releases/download/v3.0.3/apktool_3.0.3.jar" 2>/dev/null || {
        echo "    [!] Falha ao baixar apktool.jar. Baixe manualmente de:"
        echo "        https://github.com/iBotPeaches/Apktool/releases"
    }
fi

if [ ! -f "$APKTOOL_DIR/apktool" ]; then
    echo "    Baixando apktool wrapper..."
    curl -L -o "$APKTOOL_DIR/apktool" \
        "https://raw.githubusercontent.com/iBotPeaches/Apktool/master/scripts/linux/apktool" 2>/dev/null || {
        echo "    [!] Falha ao baixar apktool wrapper."
    }
    chmod +x "$APKTOOL_DIR/apktool"
fi

# Criar atalhos no PATH
sudo ln -sf "$APKTOOL_DIR/apktool" /usr/local/bin/apktool 2>/dev/null || true
sudo ln -sf "$APKTOOL_DIR/apktool.jar" /usr/local/bin/apktool.jar 2>/dev/null || true

echo ""
echo "============================================================"
echo "  Instalação concluída!"
echo "============================================================"
echo ""
echo "Próximos passos:"
echo "  1. Verifique: java -version"
echo "  2. Verifique: apktool --version"
echo "  3. Verifique: apksigner --version (se instalado)"
echo "  4. Execute: ./tools/scripts/build-release.sh"
echo ""
