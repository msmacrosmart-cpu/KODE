# Critérios de aceitação SMARTED-TV — em andamento

A entrega 1.0.18 **não satisfez** todos estes critérios. Abrir menus, verificar arquivos no APK ou testar um substituto sintético não comprova reprodução, nem equivalência visual completa. O usuário relatou falha na reprodução; ainda é necessário o log do aparelho para diagnosticar a causa. Não afirmar que houve reprodução bem-sucedida no aparelho sem evidência.

## Reprodução e preservação

- [ ] Diagnosticar o erro relatado com `kodi.log` do aparelho e uma reprodução real. Os logs podem conter URLs e credenciais; não publicar dados pessoais.
- [ ] Confirmar player oficial do Kodi, opções de áudio, legendas, pausa e retomada com vídeo local e com um vídeo resolvido pelo Brazuca. O backup inspecionado configura o player nativo no complemento; isso, por si só, não prova que os vídeos remotos funcionem.
- [ ] Preservar dados e preferências de uma instalação existente. O APK 1.0.18 inclui os arquivos do backup, mas só os restaura quando o perfil não existe; não faz migração ou mesclagem.

## Aparência e navegação

- [ ] Usar a skin do ZIP fornecido como referência visual exata: preservar aparência e geometria já existentes, acrescentar telas ausentes e corrigir contratos Kodi quando necessário sem redesenhar a interface.
- [ ] Reunir TV, filmes e séries no modo básico; liberar opções extras pela sequência solicitada; manter opções de usuário conforme o backup. Testar toque e controle.
- [ ] Disponibilizar complementos de programas/YouTube e áudio/música quando apropriado, mantendo o layout.
- [ ] Listar todas as opções originais de TV, busca de canais incluindo Pluto e favoritos de canais na Home. A busca em duas fontes tem testes de unidade, não comprova a disponibilidade das fontes ou reprodução.
- [ ] Organizar séries, novelas, animes, doramas e desenhos na mesma aba; busca unificada também precisa refletir fontes privadas habilitadas no perfil e suas regras de acesso.
- [ ] Tela de filmes com busca exclusiva, lançamentos, gêneros e alfabética em uma grade; filmes e séries com rolagem infinita.

## Home e atualizações

- [ ] Hero de filmes e séries do Brazuca com o design original. A alteração em desenvolvimento conecta o hero e a primeira grade à pasta nativa de lançamentos de filmes; falta validar aparência, navegação, séries e reprodução.
- [ ] Seções, nesta ordem: continuar assistindo; 10 filmes mais recentes; 10 séries mais recentes; canais favoritos; 10 filmes mais vistos/votados; 10 séries mais vistas/votadas. Dados de popularidade e recência devem vir de fonte real, não inventada.
- [ ] Favoritos de canais, filmes e séries; progresso e confirmação de retomada. Não sobrescrever favoritos do usuário.
- [ ] Atualizar conteúdo do Brazuca no primeiro início após meia-noite, uma vez por dia, respeitando falhas de rede e perfil.

## Entrega

- [ ] Validar com o backup real em ambiente protegido, sem comprometer dados existentes; assinar com a mesma chave e versionCode crescente.
- [ ] Testar instalação/atualização ARM64 e reprodução no aparelho. A versão universal é uma etapa posterior.
