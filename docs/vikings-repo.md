# Vikings Repo no SMARTEDTV — como o repositório entra no APK

## O que o build faz

1. **`tools/kodi/fetch-vikings-repo.py`** baixa o zip do add-on de repositório,
   confere que ele tem **um** `addon.xml` na raiz cujo `id` combina com a pasta
   (`repository.*`) e o extrai para a pasta de add-ons extras do build.
2. **`tools/kodi/build-release-apk.py`** recolhe essa pasta em
   `assets/addons/<id>/` e registra a linha
   `<addon optional="true"><id></addon>` em `assets/system/addon-manifest.xml`.
   Resultado: no primeiro boot o Kodi instala o repositório no perfil e ele já
   aparece em *Add-ons → Instalar a partir do repositório*.
3. O zip original também vai para `service.smarted.bootstrap/payload/`, então
   `repository.py` consegue **refazer o registro sem rede** se o perfil perder o
   add-on (limpeza, atualização por cima, perfil recriado).
4. O zip do add-on de vídeo publicado pelo repositório
   (`plugin.video.BrazucaPlay.Matrix-<versão>.zip`) vai no mesmo payload:
   `repair.py` copia esse pacote para `addons/packages/` e o reparo do perfil
   instala a partir dele quando o perfil semeado não trouxe o add-on.

## Qual endereço é usado

| Endereço | Situação em 2026-11 |
|---|---|
| `https://vkodi.net/repo/repository.vikings.zip` | **fora do ar** (timeout na CI; usuários relatam queda desde dez/2025) |
| `https://github.com/vikingsbuild/vikings.repo/raw/master/vkkodi.repo/vkkodi.repo-3.00.zip` | **funciona** — repositório oficial do time Vikings no GitHub |
| `https://vikingskoditeam/vikingskoditeam.github.io` (árvore `matrix`) | fonte de conteúdo que o `vkkodi.repo` aponta (Kodi ≥ 18.9.1) |

O script tenta o GitHub primeiro e mantém `vkodi.net` como alternativa caso o
domínio volte. O id do add-on embarcado é `vkkodi.repo` (nome exibido:
“Vikings Repositorio Oficial … compatível com Kodi Matrix”), não
`repository.vikings`, porque é esse o zip que o time publica hoje com a árvore
`matrix` — a mesma que lista `plugin.video.BrazucaPlay.Matrix` 2.1.4.

## No primeiro boot (`service.smarted.bootstrap`)

```
vikings: repos=vkkodi.repo plugin=ok falhas=nenhuma
```

`repository.ensure_repository()`:

* procura o repositório em `special://home/addons` e em `special://xbmc/addons`;
* se não existir, extrai do payload (qualquer `repository*.zip` / `*.repo*.zip`);
* roda `UpdateLocalAddons()` e habilita com `Addons.SetAddonEnabled`;
* se `plugin.video.BrazucaPlay.Matrix` não estiver instalado, executa
  `UpdateAddonRepos()` + `InstallAddon(plugin.video.BrazucaPlay.Matrix)`.

Nada é inventado: sem zip, o log registra “repositorio ausente” e o build segue
(com `::warning::` no run).

## Testes

```
python3 -m unittest tests.test_vikings_repo -v
```

Cobrem: validação do zip (id/pasta/raiz), extração no formato que o build
recolhe, `vkkodi.repo` como repositório válido, extração do payload, habilitação
por JSON-RPC, `InstallAddon` só quando o plugin falta e a importação do pacote
de vídeo do payload para `addons/packages/`.
