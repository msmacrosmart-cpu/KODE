# v12 — anúncio em toda troca de conteúdo, VIP real e app que não fecha

## O que mudou

### 1. Um anúncio por conteúdo escolhido

O `service.py` que já vem no APK base chama `smart_ads.iniciar_monitor(log)`. O
problema era o `smart_ads.py` dentro do APK: ele não estava no repositório e a
ponte usava nomes de classe antigos. Agora:

- `kodi/addons/service.smarted.bootstrap/smart_ads.py` é a versão que o injetor
  coloca no APK (byte a byte, conferido no passo 6 do workflow);
- a activity é a que **existe** no APK: `smartedtv.full.PreRollActivity`
  (pacote `smartedtv.full`, classe no 9º parâmetro do
  `StartAndroidActivity`);
- o gancho escuta `onPlayBackStarted` e `onAVStarted` do `xbmc.Player`;
- a chave é `caminho + canal/título`: canal → canal, filme → filme, episódio →
  episódio e repetir o mesmo conteúdo depois de parar pedem anúncio;
- só o par de callbacks do **mesmo** início é deduplicado (janela de 10 s,
  ajustável em `ads_intervalo`);
- VIP ativo (`vip.ativa()`) continua sem anúncio.

O anúncio de abertura (`AppOpenActivity`, uma vez por instalação) continua.

### 2. Ativação VIP pelo backend real

A rota confirmada em produção é:

```
POST https://smartedtv-vip.lovable.app/api/public/validar-codigo
Content-Type: application/json
{"code":"TESTE-..."}
```

Respostas usadas:

- `200 {"status":"success","active":true}` → grava a licença;
- `403 {"status":"error","active":false,"message":"..."}` → mostra a recusa,
  **sem** tentar uma segunda rota;
- `200` sem `active:true` → **não** ativa;
- rede/servidor fora → tenta a segunda rota (`/public/api/cakto`) apenas para
  não deixar o usuário sem mensagem; ela não é API de código e só ativa se
  devolver `active:true`.

A licença é gravada em:

```
<perfil>/.kodi/userdata/addon_data/service.smarted.bootstrap/vip.json
{"ativo":true,"codigo_hash":"...","expira":"AAAA-MM-DD","expira_em":"...","origem":"site",...}
```

Esse é o caminho que o Java `Licenca`/`SmartAds` lê (o antigo
`userdata/vip.json` era ignorado pelo app). A validação roda em thread, com
vigia de 30 s; a interface não trava mais.

### 3. O app não fecha sozinho

- removido o `RestartApp` de último recurso do `_ir_para_home()`: se a Home não
  abrir, o app é mantido aberto e o usuário é avisado;
- removido o grupo 960 (`welcome_teclado`), o overlay falso que cobria o campo
  e impedia o clique de abrir o teclado do Kodi;
- o campo 310 usa o teclado do Kodi; o botão Ativar com campo vazio também abre
  o teclado.

### 4. Colar código

O Kodi 21.3/Android não implementa `getClipboard()` no `WinSystemAndroid` e o
teclado genérico não tem colar. O código usa `getClipboard` se uma versão
futura expuser a API; nesta versão a digitação é pelo teclado do Kodi. Não é
possível prometer colar do Android sem trocar o motor do Kodi.

## Provas executadas

- `python3 tools/kodi/static-check.py` — 214 XML, 61 scripts;
- `python3 tools/kodi/simular-boot-tela-entrada.py` — boot, 311, 120–123,
  diálogos e VOLTAR na Home;
- `python3 tools/kodi/mapear-botoes.py` — todos os botões com ação;
- testes de `tests/test_tela_entrada.py`, `tests/test_vip_botoes_android.py`;
- injeção em `/tmp/SMARTEDTV-v11.apk`: `smart_ads.py` e `vip.py` substituídos
  byte a byte, `service.py` do APK base mantido com
  `smart_ads.iniciar_monitor(log)`.

Não houve execução em aparelho Android real neste ambiente. O APK mantém a
mesma assinatura e é instalado por cima, sem apagar dados.
