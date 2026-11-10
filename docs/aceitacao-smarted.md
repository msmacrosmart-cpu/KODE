# Critérios de aceitação SMARTED-TV — em andamento

A entrega 1.0.18 **não satisfez** todos estes critérios. Abrir menus, verificar arquivos no APK ou testar um substituto sintético não comprova reprodução, nem equivalência visual completa. O usuário relatou falha na reprodução; ainda é necessário o log do aparelho para diagnosticar a causa. Não afirmar que houve reprodução bem-sucedida no aparelho sem evidência.

## Reprodução e preservação

- [ ] Diagnosticar o erro relatado com `kodi.log` do aparelho e uma reprodução real. Os logs podem conter URLs e credenciais; não publicar dados pessoais.
- [ ] Confirmar player oficial do Kodi, opções de áudio, legendas, pausa e retomada com vídeo local e com um vídeo resolvido pelo Brazuca. O backup inspecionado configura o player nativo no complemento. [42853960538](https://github.com/msmacrosmart-cpu/KODE/actions/runs/42853960538) abriu e avançou um vídeo local gerado em emulador descartável; isso não prova que os vídeos remotos funcionem.
- [ ] Preservar dados e preferências de uma instalação existente. O APK 1.0.18 inclui os arquivos do backup, mas só os restaura quando o perfil não existe; não faz migração ou mesclagem.

## Aparência e navegação

- [ ] Usar a skin do ZIP fornecido como referência visual exata: preservar aparência e geometria já existentes, acrescentar telas ausentes e corrigir contratos Kodi quando necessário sem redesenhar a interface.
- [ ] Reunir TV, filmes e séries no modo básico; liberar opções extras pela sequência solicitada; manter opções de usuário conforme o backup. Testar toque e controle.
- [ ] Disponibilizar complementos de programas/YouTube e áudio/música quando apropriado, mantendo o layout.
- [ ] Listar todas as opções originais de TV, busca de canais incluindo Pluto e favoritos de canais na Home. A busca em duas fontes tem testes de unidade, não comprova a disponibilidade das fontes ou reprodução. O widget usa a lista nativa do Brazuca sem alterar favoritos; [42855782454](https://github.com/msmacrosmart-cpu/KODE/actions/runs/42855782454) retornou um canal sintético num perfil descartável, não os favoritos do usuário.
- [ ] Organizar séries, novelas, animes, doramas e desenhos na mesma aba; busca unificada também precisa refletir fontes privadas habilitadas no perfil e suas regras de acesso.
- [ ] Tela de filmes com busca exclusiva, lançamentos, gêneros e alfabética. A visão atual abre a primeira página e mantém o menu nativo para as demais; faltam grade contínua e rolagem infinita de filmes e séries.

## Home e atualizações

- [ ] Hero de filmes e séries do Brazuca com o design original. A alteração em desenvolvimento conecta o hero e a primeira grade à pasta nativa de lançamentos de filmes: [42852349386](https://github.com/msmacrosmart-cpu/KODE/actions/runs/42852349386) confirmou consulta com cópia pública do Brazuca em emulador. Falta validar aparência no aparelho, navegação, séries e reprodução.
- [ ] Seções, nesta ordem: continuar assistindo; 10 filmes mais recentes; 10 séries mais recentes; canais favoritos; 10 filmes mais vistos/votados; 10 séries mais vistas/votadas. A seção de séries consulta índices públicos e ordena por data de estreia, não de inclusão; não cobre PRO. Dados de popularidade e recência devem vir de fonte real, não inventada.
- [ ] Favoritos de canais, filmes e séries; progresso e confirmação de retomada. Não sobrescrever favoritos do usuário.
- [ ] Atualizar conteúdo do Brazuca no primeiro início após meia-noite, uma vez por dia, respeitando falhas de rede e perfil.

## Entrega

- [ ] Validar com o backup real em ambiente protegido, sem comprometer dados existentes; assinar com a mesma chave e versionCode crescente.
- [ ] Testar instalação/atualização ARM64 e reprodução no aparelho. A versão universal é uma etapa posterior.
