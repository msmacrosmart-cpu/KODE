# Teclado Android no SMARTED-TV: investigação

**Estado: não implementado; não há APK ou release novo para esta função.**

O SMARTED-TV 1.0.15 é um reempacotamento do Kodi 21.3, cujo código nativo já está compilado. Na fonte oficial `21.3-Omega`, `xbmc/guilib/GUIKeyboardFactory.cpp` seleciona o teclado do Kodi no Android; a seleção de teclado nativo existente é específica de plataformas Darwin. `system/settings/android.xml` não contém uma opção para habilitar o teclado Android. Portanto adicionar uma preferência XML ao APK atual, sem alterar o código, não ativaria o teclado nativo.

O Kodi incorporou uma implementação posterior em [xbmc/xbmc#28580](https://github.com/xbmc/xbmc/pull/28580), mesclada em `31338108558afc9feb0b400094d957f1e571ff46` em 2026-10-01. Ela inclui uma implementação C++, ponte JNI, diálogo Java e integração na seleção e configurações do teclado. O patch foi avaliado contra a tag `21.3-Omega`; ele **não se aplica diretamente**, pois várias APIs e arquivos do sistema de configurações mudaram. Requer uma adaptação real e compilação do Kodi com SDK/NDK, não apenas Apktool.

## Trabalho necessário

1. Adaptar a implementação Android da alteração oficial para a versão 21.3, mantendo outras plataformas e migrações de configuração intactas.
2. Configurar e compilar o Kodi e suas dependências Android para ARM64, incluindo C++ e Java. O ambiente atual somente reempacota o APK; não contém o toolchain completo e não consegue baixar Android SDK/NDK dos servidores necessários.
3. Reaplicar a identidade SMARTED-TV e assinar com a mesma chave de teste já usada na 1.0.15, aumentando o `versionCode`. Preservar as configurações do usuário durante a atualização.
4. Testar em Android real: teclado nativo por padrão, alternância com teclado do Kodi nas configurações, entrada/edição de links e caracteres Unicode, colar, cancelamento, campos ocultos/senhas, comandos com controle remoto, acessibilidade, e atualização sobre a 1.0.15 sem perda de dados.
5. Somente após validação, gerar e publicar um release. Não inserir credenciais nem a chave de assinatura no repositório.

Uma possível opção temporária, sem alterar o APK, é controlar o Kodi com um aplicativo remoto e enviar texto pela rede local; isso não é equivalente a usar o teclado nativo no próprio dispositivo.

## Preparação iniciada

Uma adaptação inicial da implementação oficial, limitada ao Android, foi preparada em `patches/kodi-21.3-native-android-keyboard.patch`. O patch foi conferido para aplicação limpa sobre a tag oficial e o XML da opção tem `false` como padrão para “usar teclado virtual do Kodi” (portanto solicita o teclado Android). **A adaptação ainda não foi compilada nem validada em aparelho.** A operação de compilar um candidato intermediário foi configurada em `.github/workflows/verify-native-keyboard.yml`; ela não publica release e não usa a chave do usuário. O resultado intermediário, caso exista, não deve ser instalado por cima do SMARTED-TV.

Uma cópia do APK 1.0.15 e da chave de teste foi colocada em `/SMARTED-TV-privado/backup-v1.0.15` no Dropbox. Esse backup não contém o perfil, fontes de mídia, add-ons instalados ou outras configurações que existam apenas no dispositivo.
