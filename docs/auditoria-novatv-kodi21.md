# Auditoria NovaTV / Kodi 21.3

## Entradas e escopo

O ZIP `NovaTV_Kodi21_Skin_Base.zip` fornecido tem 15 arquivos: somente Home de exemplo, inicialização, includes vazios, fontes/cores e imagens. Ele declara 44 mockups HTML que **não estão no ZIP** e descreve a si próprio como base, não produto completo. A Home do ZIP tem botões sem ações e placeholders; não foi sobreposta à skin existente, pois isso removeria integrações e mudaria o visual anterior. O projeto contém uma skin 1920×1080 com 93 XMLs de janela e um complemento que encaminha aos menus do Brazuca. O usuário pediu preservar o estilo anterior e forneceu uma prévia com sete cards, que foram recortados; os arquivos originais separados não foram localizados.

A tabela abaixo distingue **rota presente** de comportamento comprovado. Uma rota presente só indica uma ação XML ou um contrato de controle no projeto; não constitui teste de todas as funções da janela. O modo básico mantém TV, filmes, séries, categorias e ajustes; recursos adicionais seguem o desbloqueio já existente. As opções PVR não são ativadas nem simuladas: dependem de PVR e das condições existentes.

| Elemento / área | Tela de destino | Função real | Método/ação | Status |
|---|---|---|---|---|
| Aurora / Blade | Home | Destaque e navegação atuais | Home.xml, listas de widgets | Layouts distintos dos HTMLs ausentes não convertidos |
| Top 10 | Home | Rankings por popularidade | Fonte real necessária | Não implementado; não há métrica confiável |
| Esportes | TV Brazuca | Navegar pelas opções disponíveis | rota TV → menu original | Depende das opções da fonte; sem eventos fabricados |
| Guia | Guia PVR | Programação | ActivateWindow(TVGuide) / janela PVR | Condicional ao PVR; não configurado |
| Canais | TV | Menus e busca | plugin.video.smarted rota tv | Presente; fonte externa necessária |
| Série | Séries | Categorias e pesquisa | rota series, add-on Brazuca | Presente; fontes PRO não incluídas na busca |
| Player | VideoOSD | Comandos de reprodução | PlayerControl, seek, diálogos nativos | Controles ampliados; validar no aparelho |
| Config / Ajustes | Settings | Categorias de configuração | ActivateWindow(Settings) | Rota presente; todas opções exigem validação |
| Música / Tocando | Music / MusicVisualisation | Biblioteca e música atual | ActivateWindow(Music), Kodi | Exige biblioteca/add-ons configurados |
| VídeoMus | Videos | Vídeos musicais | videodb://musicvideos/ | Exige biblioteca |
| Rádio | RadioChannels | Rádio PVR | ActivateWindow(RadioChannels) | Condicional a PVR |
| Jogos | Games | Jogos | ActivateWindow(Games) | Condicional a suporte/serviço |
| Complementos | AddonBrowser | Gerenciar add-ons | ActivateWindow(AddonBrowser) | Rota presente |
| Imagens | Pictures | Biblioteca de imagens | ActivateWindow(Pictures) | Rota presente; depende de fontes |
| Vídeos / Filmes | Videos | Biblioteca ou menu real Brazuca | ActivateWindow(Videos), rota movies | Rota presente; paginação contínua pendente |
| Favoritos | Favourites / canais | Favoritos do Kodi e Brazuca | ActivateWindow(Favourites), rota channel-favorites | Widget de canais depende do arquivo nativo do Brazuca |
| Clima | Weather | Previsão | ActivateWindow(Weather) | Depende de serviço instalado e configurado |
| Arquivos | FileManager | Navegador de fontes | ActivateWindow(FileManager) | Rota presente |
| Energia | ShutdownMenu | Opções de energia | ActivateWindow(ShutdownMenu) | Depende de plataforma/permissões |
| Busca | Busca de canais / séries | Consultas nas fontes disponíveis | rotas search-channels, search-series; script.globalsearch | Busca global depende do complemento; fontes PRO pendentes |
| Gravações / Timers | MyPVRRecordings / MyPVRTimers | Gravações/agendamentos | janelas PVR nativas | PVR necessário, não ativado nem simulado |
| Perfis | Profiles | Perfis do Kodi | ActivateWindow(Profiles) | Rota presente; validar no aparelho |
| Contexto | DialogContextMenu | Ações do item | janela contextual nativa | Menus originais do Brazuca não atravessam JSON-RPC |
| AudioLeg | DialogSettings | Áudio e legendas | ActivateWindow(osdaudiosettings / osdsubtitlesettings) | Rota presente; validar trilhas e downloads |
| Sobre | SettingsSystemInfo | Informações do sistema | SystemInfo | Janela existe; conferir navegação |
| CPlayer | SettingsCategory | Player | PlayerSettings | Rota presente |
| CMidia | SettingsCategory | Mídia | MediaSettings | Rota presente |
| CTV | SettingsCategory | TV / PVR | PVRSettings | Depende de PVR; não exposto no modo básico |
| CServ | SettingsCategory | Serviços | ServiceSettings | Rota presente |
| CInt | SettingsCategory | Interface | InterfaceSettings | Rota presente |
| CSis | SettingsCategory | Sistema | SystemSettings | Rota presente |
| CPerf | Profiles | Perfis | Profiles | Rota presente |
| Hero — assistir | Vídeo / diretório | Abrir o título selecionado | PlayMedia ou ActivateWindow para pasta | Usa o destino do Brazuca; reprodução remota não comprovada |
| Hero — detalhes | Visualizador de texto | Sinopse real, quando fornecida | hero_details.py lê Container(9100).ListItem.Plot | Estado explícito se não houver sinopse; validar no aparelho |
| Categorias | Navegação por cards | TV, filmes, séries, doramas, animes, novelas, desenhos | rota root e menus reais Brazuca | Cards da prévia recebida, visualização sujeita a validação |
| Marcadores | VideoOSDBookmarks | Marcadores do Kodi | controles nativos 2/3/4/11 | XML implementado; validar em conteúdo compatível |

## Compatibilidade e pendências

- Skin declara xbmc.gui 5.17 e resolução 1920×1080; não substitui o motor do Kodi. O app contém a ponte e o backup privado; o ZIP isolado da skin não inclui o Brazuca nem o complemento de navegação. Instale a ponte separadamente para as rotas SMARTED, e habilite Brazuca 2.1.4 e dependências compatíveis. Um perfil existente não é restaurado nem sobrescrito pelo pacote.
- Os HTMLs de referência não foram fornecidos, portanto não é possível comprovar fidelidade às 36 telas solicitadas; telas existentes marcadas como `sync` em `kodi/skin.novatv/docs/JANELAS.md` também ainda exigem verificação dos contratos.
- A faixa vertical que dividia o hero foi removida. O degradê horizontal permanece para legibilidade. O item de detalhes mostra a sinopse recebida; não inventa metadados ausentes. O banner depende da disponibilidade dos lançamentos reais da fonte.
- Falta comprovar todos os controles, inclusive áudio, legendas, marcadores e aceleração, em dispositivo real; não se declara equivalência integral ao OSD Estuary nem funcionamento de streams externos. Não há mockup, PVR ou dados fictícios no APK.
- Também permanecem pendentes: histórico/retomada unificados, top 10 real, rolagem infinita, hero misto, atualização diária explícita, favoritos contextuais em todos resultados, resultados PRO e validação de todas as telas e de toque/controle.

## Testes

Executados localmente: parsing dos XMLs; referências estáticas de includes e texturas; IDs numéricos duplicados por arquivo; ações e condições estruturais do banner/OSD; navegação de rotas com stubs isolados; integridade de backups, scripts de construção e outros testes unitários. Esses testes **não validam** ações em execução, renderização 1080p, desempenho, serviços ou instalação. Quatro testes locais dependentes de ferramentas Java foram ignorados nesta execução. Os resultados do emulador são registrados separadamente quando disponíveis.
