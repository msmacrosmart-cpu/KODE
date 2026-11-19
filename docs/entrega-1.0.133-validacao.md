# SMARTEDTV 1.0.133 — navegação, addons, inicialização e VIP

APK: `SMARTEDTV-universal.apk` • SHA-256
`96ec6540230ffbaa72bbb5ff80137235aa9c92af36ad892ac914ed7377eaeef1` •
287 316 198 bytes • 1.0.133 / código 2103119.

Regra seguida em cada item: **antes de alterar, histórico do Git**; o que
estava certo foi preservado (nada redesenhado, nada removido).

---

## 1. Navegação D-pad (TV, TV Box, projetor)

### Causa encontrada

A Home tem três layouts (`blade`, `top10`, `sports`). O grafo foi fechado com
as setas **e** a geometria (como o `CGUIControl::Navigate` do Kodi faz) e
apareceram quatro becos:

| controle | antes | efeito no controle remoto |
| --- | --- | --- |
| `9320` (Assistir / Trailer / Informações do Hero) | subia para `9121` (barra superior) | depois de descer para os botões, "cima" pulava para o topo da tela; **o Hero ficava inalcançável** de volta |
| `9203` (última fileira) | descia para `9201` | descer "voltava para cima" em vez de seguir para os botões |
| `9340` / `9350` (barras do layout `sports`) | `<onup>` para si mesmo | "cima" não fazia nada (o Kodi recusa focar o controle que já tem foco) |
| `9100` (coluna do `blade`) | `<onup>9100</onup>` e depois `9117` | "cima" ficava preso na coluna |

### Correção (só setas; **layout, cards e dimensões intactos**)

- `9320` → `onup: 9300` (Hero) e `9300` passou a alcançar os botões;
- `9203` → `ondown: 9320`;
- `9340`/`9350` → sobem para as categorias do layout (`9010` / `9020`) e
  `9020` sobe para a barra superior (`9083`);
- `9100` → `onup: 9121`;
- `9000` (categorias) e `9121` escolhem a descida do layout ativo
  (`blade` → Hero `9300` / botões `9320`; `top10` → `9010`; `sports` → `9020`)
  e a última descida é sempre o Hero, nessa ordem (condicionais antes da
  incondicional — é a regra de `CGUIAction::GetNavigation`);
- as duas skins do APK (`skin.novatv` e `skin.estilo.personalizado`) ficaram
  **byte a byte iguais** (há teste para isso).

### Resultado dos testes

| teste | resultado |
| --- | --- |
| `tests/test_dpad_tres_layouts.py` (novo, 14) — grafo por setas + geometria nos 3 layouts, proíbe seta vertical para si mesmo, exige fileira→Hero, Hero→topo, botões→Hero | **OK** |
| `test_navegacao_aurora` (9), `test_home_navegacao`, `test_foco_dpad_aparelho`, `test_filtro_e_dpad`, `test_skin_novatv_espelha_classica` | **58 testes OK** |
| `tools/kodi/check-foco-skin.py` no Home das duas skins | sem `SEM SAIDA` |

---

## 2. Inicialização e estabilidade

Nenhuma regressão introduzida; as correções anteriores foram **mantidas**:
`WAIT_SECONDS=8` (o boot não espera o banco de addons), `REPARO_EM_SEGUNDO_PLANO`,
`_liberar_home_agora()` (Home na tela antes do reparo terminar), vigia
`garantir_interface_inicial`, `Startup.xml` com espera desenhada e alarme de
segurança da Home, `limpar_estado_interface()` a cada boot.

Prova no CI desta versão (emulador API 30, APK **publicado**):

```
v22 instalada e atualizada com adb install -r; versionCode=2103119; ABI arm64-v8a
reabertura 1: app vivo e com imagem na tela
reabertura 2: app vivo e com imagem na tela
reabertura 3: app vivo e com imagem na tela
instalação limpa (armeabi-v7a) + LAUNCHER + LEANBACK_LAUNCHER: success
```

---

## 3. Addons (prioridade)

### Causa já encontrada e corrigida (log real do projetor)

```
File ".../smart_ads.py", line 66, in <module>  import ads_regra
FileNotFoundError: .../service.smarted.bootstrap/ads_regra.py
```

`ads_regra.py`, `ads_vast.py`, `repair.py`, `favourites.py` e `skin_setup.py`
não estavam na lista de módulos do injetor do APK. Como o `import` está no
topo, o `service.py` morria antes de fazer qualquer coisa: **nenhum** trabalho
do serviço (reparo, favoritos, skin, menu, anúncio) rodava.

### O que foi acrescentado nesta rodada (prova, não suposição)

| ferramenta/teste | o que prova | resultado |
| --- | --- | --- |
| `tools/kodi/simular-servico.py` (roda no CI antes da auditoria) | **importa** o `service.py` de verdade, na ordem do Kodi, com `xbmc` falso; reprova com o erro exato acima quando falta `ads_regra.py` | OK no CI (`servico importado: 6 modulos do boot carregados`) |
| `tests/test_servico_importa_no_aparelho.py` (3) | o serviço importa completo; uma cópia **sem `ads_regra.py`** falha com `FileNotFoundError`; toda chamada de anúncio no `main()` está em `try/except` (verificado por AST, não por texto) | OK |
| `tests/test_reparo_addons_perfil.py` (6) | o reparo real instala o addon e as dependências a partir dos zips, **não apaga** o que o usuário tem, e quando falta pacote **diz o nome do addon** (nunca falha silenciosa) | OK |
| `tests/test_addon_completo_no_apk.py` + `tests/test_conferir_modulos_apk.py` | a pasta do addon == lista do injetor; o conferidor reprova APK incompleto | OK |
| CI: "todos os modulos do addon estao no APK instalado" | confere o addon **dentro do APK já instalado no AVD** | OK |

Nada foi escondido: o texto técnico continua no log interno
(`perfil incompleto: …`, `tentativa n/6 incompleta: …`) e o reparo repete 6
vezes antes de desistir. O que saiu da tela foi só o aviso técnico que
interrompia o uso na TV (usuário não tem como abrir log ali).

---

## 4. VIP e anúncios

### Causa encontrada (reproduzida com o módulo rodando)

`_gravar_licenca` escrevia `expira_em` (ISO **com hora**) também dentro de
`expira`, que é lido como **data**; e `ativa()` decidia apenas pelo dia. Efeito
real: licença vencida às 18:38 continuava liberada até 23:59 — o cliente ganhava
horas de graça e o anúncio **não voltava** na hora certa.

### Correção

- `ativa()` compara o **instante exato** (`expira_em`) quando existe; `expira`
  guarda a data pura (compatível com quem lê o `vip.json`) e licenças antigas
  (só data) continuam funcionando;
- nada mais do fluxo mudou: recusa definitiva não consulta a segunda rota,
  HTTP 200 sozinho nunca é sucesso, e o `vip.json` continua no caminho que o
  Java lê.

### Testes (`tests/test_vip_prazo_contratado.py`, 8 — OK)

| cenário | resultado |
| --- | --- |
| ativação com prazo de 30 dias do servidor | ativo, data pura + instante exato |
| app reaberto (processo novo) | licença continua válida |
| mesmo código de novo | "VIP já está ativo neste aparelho" |
| plano de 3 dias | vale até o fim do 3º dia |
| **licença vencida há 1 hora** | `ativa()` = False (era True) |
| licença que vence em 2 minutos | ainda ativa |
| licença antiga (só data) | continua valendo |
| código recusado | nada é gravado |

E a virada do anúncio: com VIP ativo `mostrar_preroll` devolve False; com a
licença **vencida** o anúncio volta a ser pedido (2 testes).

---

## 5. Testes desta rodada (execução real)

```
632 testes • failures=11, errors=13 (todos PRÉ-EXISTENTES, skins antigas)
comparação com a base (git stash): 0 falhas novas, 0 regressões
novos: test_dpad_tres_layouts (14), test_vip_prazo_contratado (8),
       test_servico_importa_no_aparelho (3), test_reparo_addons_perfil (6)
static-check: 229 XML válidos, 80 scripts compilados
```

As 24 falhas antigas (`test_sem_fundo_fixo_de_1920`, teclado, textos de skin
antiga etc.) descrevem uma skin anterior e **não** tocam navegação, addons,
VIP ou anúncio. Continuam visíveis — nada foi silenciado.

## 6. O que ainda depende de aparelho

| item | como fechar |
| --- | --- |
| D-pad no controle físico | subir das fileiras → Hero → barra superior e descer de volta; nos três layouts (Ajustes → layout da Home) |
| Addons carregando numa TV real | no `kodi.log`: `RESULTADO: ok`, `favoritos: N atalhos`, `servico importado` |
| Anúncio de TV com a tag do projeto | Ajustes → Testar anúncio (caminho já provado no CI: VAST → criativo → player) |

O AVD do CI é celular (API 30, sem leanback) e não tem `python3` no shell: por
isso a reprodução de anúncio de TV **não** é declarada ali.
