# Integração NovaTV e backup — em andamento

Esta alteração **ainda não gera um APK de integração** e não substitui a versão 1.0.16 aprovada. A Home, configurações e sequência de desbloqueio passaram em emulador isolado; complementos e reprodução ainda não foram validados.

## Referências examinadas

- Backup reconstruído do Dropbox: `files.zip`, SHA-256 `e38ee0e23356948a008a895fbefd8b659f62504b72d50712ac91c7305a774cde`. O original contém dados pessoais e continua fora do repositório.
- Skin fornecida separadamente, SHA-256 do ZIP `86b9808741bdc00f498dd7d83192518251a455b034eb667e90442e4182df1acb`: importada em `kodi/skin.novatv`. O arquivo `docs/JANELAS.md` da skin lista telas que precisam de sincronização com o Kodi.
- Referência de comportamento do Kodi 21.3: tag `21.3-Omega`, commit `a3a448d26b8d560a65655dab2cd122994dc4e146`. Em `xbmc/settings/dialogs/GUIDialogSettingsBase.cpp` estão os IDs e tipos dos modelos de controles dinâmicos.

## O que foi alterado

A skin original foi mantida como referência visual, incluindo paleta, fontes e recursos. Foi criada a tela `Settings.xml`, ausente na skin original, com ações de configuração equivalentes às da Estuary. `SettingsCategory.xml`, `DialogAddonSettings.xml` e `DialogSettings.xml` foram ajustados aos IDs e tipos de controle esperados pelo Kodi 21. As listas de categorias e configurações agora são destinadas a receber os controles criados pelo próprio Kodi; foi acrescentado o botão de nível de configuração na janela principal. `DialogSelect.xml` teve os IDs de lista detalhada e botão adicional corrigidos e `DialogKeyboard.xml` passou a usar IDs de teclas dinâmicas e ações do teclado Kodi 21; o teclado Android continua sendo o padrão. A compatibilidade funcional, navegação por controle e toque dependem de teste real.

As três imagens enviadas estão preservadas em `assets/brand/source`. `tools/kodi/apply-user-brand.py` aplica a arte a uma árvore APK decodificada: splash horizontal, ícones Android quadrado e redondo e barra de progresso branca. No build experimental local, os dois DEX, o motor e a configuração do teclado permaneceram idênticos ao 1.0.16; o recurso ainda precisa de teste no aparelho. Como duas imagens recebidas são idênticas, o ícone redondo é derivado da arte correspondente por recorte com transparência.

O segundo teste do emulador iniciou o Kodi e exibiu `NOVA TV`, mas não chegou à Home; a skin fornecida não tinha a ação de saída da janela Startup. Foi acrescentado `ReplaceWindow($INFO[System.StartupWindow])`, como na Estuary do Kodi 21. Um teste posterior confirmou que `Home.xml` carregou. A tentativa de abrir configurações por um keymap enviado via adb falhou por contexto SELinux incorreto; o teste foi ajustado para instalar esse atalho somente no APK isolado, antes de testar de novo. Isso não comprova o funcionamento completo da Home nem do player.

`kodi/addons/plugin.video.smarted` contém uma primeira ponte de navegação para os menus reais de TV, filmes, séries, novelas, animes, doramas e desenhos do Brazuca Play 2.1.4. Os destinos foram verificados estaticamente no complemento fornecido e as URLs são testadas, mas a ponte ainda não foi incluída no APK nem validada contra o serviço ao vivo. Ela ainda não implementa busca unificada, histórico ou widgets.

`tools/kodi/stage-profile.py` prepara uma cópia integral **offline** do backup verificado em diretório novo, privado, sem sobrescrever perfil existente. O comando valida o hash e caminhos antes da extração. Não é instalador e não restaura dados automaticamente dentro do aplicativo. Nunca executar sobre um perfil em uso. O backup contém credenciais e dados de conta; não publicar arquivos gerados nem incorporar a chave de assinatura.

```sh
python3 -m unittest discover -s tests -v
python3 tools/kodi/stage-profile.py dropbox/files-reconstructed.zip dropbox/perfil-preparado
```

O teste com o backup fornecido comparou os hashes dos 2.731 arquivos extraídos aos dados do ZIP; o diretório temporário de teste foi removido. O backup original não foi alterado.

## Restauração Android em desenvolvimento

`tools/android/src/org/smartedtv/bootstrap/ProfileSeed.java` é um núcleo de restauração para perfil inexistente: verifica SHA-256, caminhos e CRC, extrai para staging e seleciona NovaTV. A comparação local com o backup real conferiu os 2.731 arquivos e só alterou a preferência de skin. O backup original não foi alterado. `ProfileBootstrap.java` é um protótipo assíncrono antes do início do Kodi; **não foi incluído em APK de entrega**. O workflow `test-profile-seed-emulator.yml` cria exclusivamente um perfil sintético e usa assinatura descartável. A execução [42826033797](https://github.com/msmacrosmart-cpu/KODE/actions/runs/42826033797) passou a instalação inicial, abertura da Home e preservação do perfil no reinício. Ciclo de vida Android durante a cópia, interrupção, espaço insuficiente e atualização de instalação real ainda precisam ser verificados; não é uma migração de perfis já existentes. Nenhum dado pessoal ou chave de produção é incluído no teste.

O smoke anterior de skin ([42824443156](https://github.com/msmacrosmart-cpu/KODE/actions/runs/42824443156)) confirmou a sequência de desbloqueio em perfil descartável. Não comprova player ou Brazuka.

## Pendências para um APK testável

- Definir e implementar migração no primeiro início/atualização com proteção aos dados já existentes, recuperação em caso de falha e comportamento correto dos bancos de dados do Kodi; a ferramenta offline não resolve a inicialização do aplicativo.
- Concluir as janelas e diálogos da skin, inclusive controles necessários para navegação, player, add-ons, PVR, jogos e perfis, e validar em execução. Nem todas as janelas fornecidas foram verificadas funcionalmente.
- Integrar o Brazuka Play real e suas dependências. O código inspecionado tem buscas separadas por categoria e realiza atualizações remotas; não foi validado em execução ou sua disponibilidade. A Home fornecida usa `videodb://` e `pvr://`, não as fontes do Brazuka. Busca unificada, favoritos por categoria, retomada, paginação, métricas e atualização diária não estão implementados.
- Confirmar no emulador e em aparelho real o modo restrito e o desbloqueio: foram adicionados à skin os menus de TV/filmes/séries condicionados aos complementos instalados, o logo com oito cliques e a contagem de duas saídas de Ajustes para a Home. A sequência passou no emulador com teclado de teste; toque e controle físico ainda precisam de validação.
- Empacotar, assinar com a chave da instalação existente, aumentar o versionCode, validar instalação/atualização e teclado; só então publicar no Dropbox e no release privado. Um ZIP ou um teste estrutural não é evidência de que a interface ou a reprodução funcionem.
