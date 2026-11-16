# Tela inicial do SMARTEDTV — o que inspecionei e o que ela precisa ter

Este texto é o resultado da inspeção do APK `SMARTEDTV-atual` (base
`v1.0.83-unificado`) e da tela que já está rodando (release
`v1.0.83-tela-inicial-v4`). A ideia é simples:

> **obrigatório** = sem isso a tela não aparece, não clica ou não volta para a Home;
> **opcional** = só muda o visual;
> **contrato** = o que a sua tela precisa declarar para eu só mapear botões.

---

## 1. O que o app é, por dentro

| item | como está no APK |
|---|---|
| Motor | Kodi **21.3-Omega** (`assets/addons/xbmc.addon` = `21.3.0`), `libkodi.so` intacta |
| Motor de UI | `xbmc.gui` **5.17.0** → XML de skin no formato Omega; `xbmc.python` **3.0.1** (abi 3.0.0 → Python 3) |
| Skins | `skin.novatv` e `skin.smartedtv.classic` (**1.0.18**, resolução **1920×1080 @16:9 `default="true"`**) + `skin.estuary` 4.0.0 |
| Addons próprios | `service.smarted.bootstrap` (licença/VIP/ads), `script.smartedtv.ajustes`, `plugin.video.smarted` |
| Perfil semeado | `assets/smarted/profile/…` = **2731 arquivos**, com SHA-256 conferido pelo dex → **não pode ser tocado** |
| Assinatura | certificado `CN=SMARTED-TV Test …` SHA-256 `855de171…951a` (v1+v2+v3) |
| Resolução real de saída | 1920×1080 (é o que está no `addon.xml` das skins) |

Ou seja: **a tela é uma janela de skin do Kodi**. Não é Activity Android, não é
HTML. Ela fala XML + PNG, roda em Python 3 e só existe depois que o Kodi
inicializou o GUI.

---

## 2. A parte OBRIGATÓRIA (sem isso não funciona)

### 2.1 O gancho de boot: `Startup.xml` de cada skin

O Kodi 21 chama `CApplication::Initialize` → carrega a skin → abre
`CSkinInfo::GetFirstWindow()`. Se a skin tem **`xml/Startup.xml`**, essa janela
é a `WINDOW_STARTUP_ANIM` (12999) em vez da Home (10000). É **o único ponto do
boot em que dá para colocar uma tela antes da Home** sem recompilar o Kodi.

O `Startup.xml` de hoje (nas 3 skins) tem exatamente duas ações:

```xml
<window>
  <onload>AlarmClock(smartedtv_entrada,RunScript(script.smartedtv.welcome),00:00:00,silent)</onload>
  <onload>AlarmClock(smartedtv_entrada_seguro,ReplaceWindow($INFO[System.StartupWindow]),00:00:30,silent)</onload>
  <controls />
</window>
```

- linha 1 = abre a tela no próximo ciclo do alarme;
- linha 2 = **seguro**: se a tela não abrir em 30 s, entra na Home (o app nunca
  fica preso); a tela cancela esse alarme no `onInit`.

Regras que o injetor impõe (e que você não precisa mudar):

- a skin precisa ter `Startup.xml` — hoje **as 3 têm**;
- não pode existir `ReplaceWindow` solto no `Startup.xml` (senão a Home abre
  antes/concorrente à tela; o injetor recusa);
- só o `ReplaceWindow($INFO[System.StartupWindow])` dentro do seguro é aceito.

### 2.2 O addon que desenha a tela

- id: **`script.smartedtv.welcome`** (qualquer id serve, mas este já está no
  `assets/system/addon-manifest.xml` como `<addon optional="true">` — mudar o id
  obriga a mexer no manifest **e** no `Startup.xml` das 3 skins);
- `addon.xml` precisa de `xbmc.python` **3.0.0** e um `xbmc.python.script`
  apontando para `default.py`;
- `default.py` deve ser **executável sem o GUI ter Home** (nada de
  `xbmcgui.Window(10000)` para pegar dados da Home, nada de esperar serviço);
- a janela é `xbmcgui.WindowXMLDialog('DialogWelcome.xml', pasta, 'Default', '1080i')`
  → o arquivo tem de estar em
  `resources/skins/Default/1080i/DialogWelcome.xml`.

### 2.3 Registrar o addon no manifest do APK

`assets/system/addon-manifest.xml` → `<addon optional="true">script.smartedtv.welcome</addon>`.

Por quê: no Kodi 21, `CAddonDatabase::SyncInstalled` insere toda linha **nova**
com `enabled=1`. Sem a linha no manifest o addon não é instalado no boot e o
`RunScript(<id>)` do `Startup.xml` falha. E **nunca** usar `<addon>` obrigatório
(sem `optional`): addon obrigatório que falha derruba o Kodi (`LOGFATAL`).

### 2.4 Clicar nos botões: o `default.py` é quem faz

O XML **não** executa ação de app por conta própria de forma confiável para
checkout/código. O que funciona é `onClick(control_id)` no Python. Então cada
botão que você desenhar tem de ter um **id** e uma linha no `default.py`.

O que já está mapeado hoje (e funciona de verdade no APK):

| id | rótulo na tela | ação real |
|---|---|---|
| 310 | campo do código | `vip.validar(codigo)` → rotas `/api/validar`, `/functions/v1/validar-codigo`, `/api/codigos/validar` (grava `vip.json`) |
| 311 | Ativar | dispara a validação do campo 310 |
| 120 | Abrir checkout | `vip.abrir_checkout()` → `https://pay.cakto.com.br/nkvbegd_1323120` |
| 121 | Compartilhar link | `vip.compartilhar()` → `smartedtv.full.CompartilharActivity` |
| 122 | Baixar APK | `vip.abrir_url(vip.APK)` |
| 123 | Atualizar aplicativo | `vip.procurar_atualizacao()` → `smartedtv.full.AtualizaActivity` |
| 312 → 905/906 | Continuar com anúncios | confirmação e depois libera a Home |
| 130/131 | Android TV / Celular | não faz nada (a tela é fixa 16:9) |
| 955 | OK de diálogo | fecha o diálogo de status |

Nada de endpoint novo: tudo vem do `vip.py` que **já está dentro do APK**
(`assets/addons/service.smarted.bootstrap/vip.py`, 21 KB, funções `validar`,
`abrir_checkout`, `abrir_site`, `procurar_atualizacao`, `compartilhar`,
`abrir_url`).

### 2.5 Cores/fontes/texturas: limites técnicos do Kodi

- **fonte**: só se usa fonte declarada no `Font.xml` **da skin ativa**. A tela
  usa estilos próprios `wf11 … wf42` (o número = altura em px de 1080p) e o
  injetor **declara automaticamente** os que faltarem, apontando para
  `NotoSans-Regular.ttf`. Se você usar outro tipo de letra, ele precisa ir
  dentro do addon e ser declarado do mesmo jeito.
- **cor**: `AARRGGBB`. Não existe gradiente em XML — gradiente é **textura**
  (PNG). Fundo, cartão, botão, pílula, placa do QR: tudo é PNG.
- **borda arredondada**: é `border="N"` na textura (o Kodi estica o meio e
  preserva o canto) — por isso as texturas têm raio embutido.
- **foco**: `texturefocus` / `texturenofocus` são obrigatórios no botão; sem
  eles o D-pad "desaparece" (não há realce).
- **posição**: `left/top/width/height` absolutos em px de 1920×1080 (o `%`
  funciona, mas o resto do app não usa).

---

## 3. O contrato que eu preciso que a sua tela cumpra

Se você desenhar (Figma, HTML/CSS, PSD, Canvas, Canva…), para eu **só mapear
botões** o desenho precisa entregar estes 8 itens. Cada item abaixo é o que
trava o mapeamento hoje:

1. **Base 1920×1080, horizontal (16:9).** Sem versão retrato: a tela é fixa
   (o app roda deitado; já foi decidido assim).
2. **Textos finais em português**, não “lorem ipsum” — eu transcrevo 1:1 e o
   layout é dimensionado pelo texto real.
3. **Cada elemento interativo com nome e id sugerido**, por exemplo:
   `Ativar (310)`, `Checkout (120)`, `Compartilhar (121)`, `Baixar APK (122)`,
   `Atualizar (123)`, `Plano 10min (140)`, `Plano 1mês (141)`,
   `Continuar com anúncios (312)`. Ids livres de 1 a 9999, **sem repetir** e
   **sem usar** os reservados: 1 (fundo), 6 (barra), 10 (logo), 13 (seg),
   20-22 (cartões), 24, 30-36, 40-55, 60-63, 70, 310, 311, 312, 900, 905, 906,
   950-955.
4. **Para cada botão: o que ele deve fazer**, escolhendo de uma lista fechada
   (é o que existe no app):
   `checkout` · `compartilhar` · `baixar_apk` · `atualizar` · `ativar_codigo` ·
   `continuar_com_anuncios` · `fechar_dialogo` · `nada/só visual`.
   Qualquer outra coisa (login de terceiro, abrir Netflix, chat, etc.) **não
   existe** no app e eu não invento endpoint.
5. **Textos dinâmicos marcados**: onde muda em tempo real (status do VIP, código
   digitado, mensagem de erro) use um marcador visível, ex. `{codigo}`,
   `{status_vip}`, `{mensagem}`. Isso vira uma *property* da janela e o Python
   preenche.
6. **Estados de cada botão**: normal e **foco** (o D-pad precisa de um realce
   visível e diferente do hover). Se no seu desenho o foco for só uma borda de
   2 px, me diga a cor.
7. **Texturas/ícones como arquivos separados** (PNG com transparência) ou
   vetor que eu consiga exportar. Gradiente, vidro (blur), sombra e brilho
   **não existem em XML**: viram PNG. Se o desenho tiver blur pesado, ele entra
   como textura estática.
8. **QR Codes como PNG original** (nada de reconstruir QR a partir de link). Os
   dois de hoje estão guardados byte a byte: `qr_checkout.png` (396×396) e
   `qr_apk.png` (588×588).

### 3.1 Formato de entrega que aceito

Qualquer um destes (do mais fácil para o mais trabalhoso):

| entrega | o que eu faço |
|---|---|
| **HTML/CSS** (como o `smartedtv-src`) | Meço o CSS (rem/vw/vh/clamp), calculo o box model em 1920×1080 e gero XML + texturas com o gerador que já existe (`tools/kodi/gerar-tela-entrada.py`) |
| **Figma/Adobe XD** (link ou JSON de export) | Leio posições/tamanhos/cores absolutos e gero direto |
| **PNG 1920×1080 (mockup chapado)** | Eu recrio as caixas sobre o seu desenho; você confere na prova visual antes de eu injetar |
| **só uma lista de botões** | Eu mantenho o layout atual e troco apenas os rótulos/ações |

Em todos os casos eu preciso do **item 4** (ação de cada botão) e do **item 6**
(estado de foco). Sem esses dois, a tela aparece mas não navega.

### 3.2 Como você confere o mapeamento (sem ler XML)

Existe uma ferramenta que cruza o desenho com o código e diz, botão por botão,
qual ação ele executa:

```bash
python3 tools/kodi/mapear-botoes.py          # tabela legível
python3 tools/kodi/mapear-botoes.py --json   # para script/planilha
```

Saída de hoje (a tela que está publicada):

| id | rótulo | ação |
|---|---|---|
| 120 | Abrir checkout | `_abrir_checkout` → `vip.abrir_checkout()` |
| 121 | Compartilhar link | `_compartilhar` → `vip.compartilhar()` |
| 122 | Baixar APK (Android) | `_baixar_apk` → `vip.abrir_url(vip.APK)` |
| 123 | ATUALIZAR APLICATIVO | `_atualizar` → `vip.procurar_atualizacao()` |
| 130 / 131 | Android TV / Celular | só log (a tela é fixa 16:9) |
| 140 / 141 | 10 min / 1 mês | `_selecionar_plano` |
| 310 | campo do código | (edit — lido por 311) |
| 311 | Ativar | `_ativar_codigo` → `vip.validar()` |
| 312 | Continuar com anúncios | abre o diálogo de confirmação |
| 905 / 906 | Voltar / Continuar | fecha ou libera a Home |
| 955 | OK do diálogo | fecha o diálogo |

Se depois do seu desenho algum botão novo aparecer, a ferramenta lista
`SEM ACAO  <-- falta mapear` e o build/teste falha de propósito — é o alarme de
que falta uma linha no contrato.

---

## 4. O que o build faz com o que você entregar

O caminho já está pronto e automatizado (não muda com o seu desenho):

```
seu desenho ──► gerador (XML 1920×1080 + texturas PNG)
            └─► addon script.smartedtv.welcome (31 arquivos)
                     │
APK base ──► injetor ─┤ + Startup.xml das 3 skins (tela antes da Home)
                     │ + Font.xml das 3 skins (estilos wfNN)
                     │ + addon-manifest.xml (optional="true")
                     ▼
              zipalign + apksigner (mesma chave 855de171…)
                     ▼
        APK assinado + prova visual + release
```

Conferências que rodam sozinhas em cada build (e que o seu desenho não pode
quebrar):

- as 3 skins mantêm `Startup.xml` com 2 `onload` e **um único** `ReplaceWindow`
  (o do seguro);
- o addon entra como `optional="true"`, nunca obrigatório;
- os 2731 arquivos do perfil semeado ficam **byte a byte** iguais;
- `service.smarted.bootstrap/service.py` não muda uma linha;
- toda `<texture>` do seu XML existe em `media/` e é PNG válido;
- toda `<font>` do seu XML está declarada em cada `Font.xml`;
- simulação do boot: a tela abre, os botões chamam as funções certas e a Home só
  aparece **depois** que a tela sai de cena;
- teste com stub prova que, se a tela falhar, a Home ainda abre (app não trava).

---

## 5. Checklist final (copie e preencha)

```
[ ] base 1920x1080 horizontal
[ ] textos finais em PT-BR
[ ] lista de botões com: nome visível | id | ação (da lista fechada)
[ ] estado de foco de cada botão (cor/forma)
[ ] textos dinâmicos marcados ({codigo}, {status_vip}, {mensagem})
[ ] ícones/texturas em PNG separado (ou CSS/vetor exportável)
[ ] QR Codes em PNG original (checkout e APK)
[ ] o que NÃO deve existir (ex.: seletor "Celular" decorativo)
```

Com isso em mãos eu: gero o XML + texturas → troco no addon → rodo os testes →
injeto no APK base → assino com a chave do app → publico a release com a prova
visual. **Você não precisa saber XML nem Python — só cumprir o contrato acima.**

---

## 6. Limite honesto desta inspeção

Não existe Kodi, emulador Android nem aparelho neste ambiente. O que está
verificado é: o conteúdo do APK (skins, fontes, manifest, perfil, assinatura), a
semântica do Kodi 21.3 (lida no código-fonte: `Startup.xml`, `onload`,
`RunScript`, `AlarmClock`, `SyncInstalled`, `GetFirstWindow`), o APK gerado e uma
simulação com stubs do ciclo de vida da janela. A prova visual é um render feito
a partir do próprio XML — **não** é captura de tela de TV. O primeiro teste em
aparelho real continua sendo necessário para afinar tamanho de fonte na
distância de sofá.
