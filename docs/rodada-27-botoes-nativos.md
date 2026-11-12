# Rodada 27 — botões nativos da Bingie (1.0.54)

## O que mudou

**1. Barra = menu nativo da skin (`skinshortcuts-mainmenu`)**, com os oito botões na
ordem pedida:

| # | Botão | Ação gerada | Destino |
|---|-------|-------------|---------|
| 1 | Home | `ActivateWindow(home,return)` | Home da skin |
| 2 | TV | `ActivateWindow(Videos,plugin://plugin.video.BrazucaPlay.Matrix/?mode=21&url=%23menu_canais&…,return)` | pasta real de canais |
| 3 | Filmes | `mode=27` `#filmes_menu` | pasta real de filmes |
| 4 | Séries | `mode=27` `#series_menu` | pasta real de séries |
| 5 | Doramas | `mode=31` `#doramas_menu` | pasta real de doramas |
| 6 | Novelas | `mode=25` `#novelas_menu` | pasta real de novelas |
| 7 | Animes | `mode=22` `#animes_menu` | pasta real de animes |
| 8 | Desenhos | `mode=28` `#desenhos_menu` | pasta real de desenhos |

Mais Busca, Ajustes e Sair. Os itens continuam sendo `<item>` do include
`skinshortcuts-mainmenu`, consumido pelo `<control type="list" id="900">` da skin —
ou seja, o mesmo sistema de menu/foco/controle remoto da Bingie, não botões soltos.

**2. Formato da ação.** Antes: `ActivateWindow(Videos, "plugin://…", return)` (com aspas).
Agora: sem aspas, que é o padrão dos atalhos nativos da skin
(`omega/skin.titan.bingie.mod/xml/shortcuts/*.DATA.xml` usam
`ActivateWindow(Videos,videodb://movies/titles/,return)`).

**3. Validação no aparelho (novo).** O `service.smarted.bootstrap` 1.0.7 roda uma vez
por instalação e percorre os sete destinos de conteúdo com `Files.GetDirectory`, usando
exatamente a mesma URL do clique, gravando:

```
userdata/addon_data/service.smarted.bootstrap/smarted-nav-check.log
```

com linhas `PASS Filmes 20 itens` ou `FALHA Filmes: <motivo>`. Isso separa as duas
causas possíveis:

- **PASS** mas a tela genérica de arquivos aparece no clique → o caminho está certo e o
  problema é a execução da ação (comando).
- **FALHA / 0 itens** → o caminho não devolve diretório e o problema está na rota do addon.

O mesmo resumo vai para o `kodi.log` com o prefixo `nav-check:`.

**4. Widgets da Home:** Lançamentos no HERO, Filmes recentes, Séries recentes, e
carrossel + Favoritos por categoria (Filmes, Séries, Doramas, Novelas, Animes, Desenhos).
A TV ao vivo **não** tem carrossel de canais na Home, só abre a pasta real.

## Backup

- tag `backup-1.0.53` → commit `5e3f1d4` (implementação anterior, íntegra).
- APK 1.0.53 continua publicado na release `v1.0.53-smarted-arm64`.
- Commit da rodada 27: `8c89029`.

## Verificação executada no build

- teste estático: 211 XML válidos, 47 scripts compilados (0,1 s);
- 226 testes unitários OK;
- workflow 1.0.54 (código 2103040), 13/13 etapas verdes, APK 375.937.764 B;
- asserções novas no build: ordem exata dos oito rótulos, ausência de ação com aspas,
  presença de `Files.GetDirectory` + `nav-check` no bootstrap embarcado.

## Pendência honesta

O clique em si só pode ser comprovado no aparelho. Para fechar o diagnóstico do
"tela genérica de arquivos" e dos erros de log, preciso de uma das duas coisas:

1. `smarted-nav-check.log` + trecho do `kodi.log` com `nav-check:` (gerados no primeiro
   boot desta versão), ou
2. o zip do perfil que funciona no Kodi do Dropbox: `userdata/favourites.xml`,
   `userdata/addon_data/skin.titan.bingie.mod/` e
   `userdata/addon_data/script.skinshortcuts/` — com ele copio a string de ação
   exata que a skin em uso executa.
