# Entrega v14 — instalação por cima da v12/v13

**APK:** https://github.com/msmacrosmart-cpu/KODE/releases/download/v1.0.84-tela-inicial-v14/SMARTEDTV-atual-com-tela-inicial-v14.apk  
**Tamanho:** 250.491.254 bytes (~239 MiB)  
**SHA-256:** `3e32c3712b62bb799f57c1b017daad001db7d70a99f6df3a3cad8238fd1da421`  
**Release:** https://github.com/msmacrosmart-cpu/KODE/releases/tag/v1.0.84-tela-inicial-v14  
**Versão:** `1.0.84` / `versionCode 2103070`  
**Commit:** `76086f1` — run `44115137260` (todos os passos verdes)

## Por que a v13 não instalava

A v13 continuava com **`versionCode 2103069`**, o mesmo da v12. O Android até
aceita reinstalar o mesmo código em alguns aparelhos, mas MIUI, Samsung,
Android TV e Fire OS costumam mostrar apenas **“Aplicativo não instalado”**
quando o APK tem o mesmo `versionCode` da versão já instalada. Não era vírus,
APK corrompido nem permissão do app.

A v14 sobe para **`2103070` / `1.0.84`**, mantendo:

- o **mesmo certificado** da v12/v13
  (`855de171e5560d517db1a69f6aa55562b72c8b66f9cc29dfd55be0a8aa00951a`);
- o **mesmo `applicationId`** (`smartedtv.full`);
- todos os dados, perfil, addons e VIP do aparelho.

Assim ela é uma **atualização de verdade**: instala por cima da v12/v13 sem
desinstalar nada.

## Como a versão foi trocada sem apktool

`tools/kodi/ajustar-versao-apk.py` (novo, passo **6c** do workflow):

1. lê o `AndroidManifest.xml` binário do APK já injetado;
2. troca a string UTF-16 `1.0.83` por `1.0.84` (mesmo tamanho) e o inteiro
   little-endian `2103069` por `2103070` — os offsets do AXML não mudam;
3. reescreve o ZIP preservando compressão, ordem e todas as entradas;
4. remove assinaturas antigas; o passo 7 alinha e assina com a mesma chave;
5. o workflow confere os bytes novos e roda `apksigner verify --print-certs`.

## Se ainda aparecer “Aplicativo não instalado”

A causa passa a ser uma destas (veja `docs/instalar-apk.md` para o passo a passo):

1. **Fontes desconhecidas** desligadas para o navegador/gerenciador/Downloader;
2. **Play Protect** bloqueando — “Mais detalhes” → “Instalar mesmo assim”;
3. **Assinatura diferente** de uma versão muito antiga (ex.: APK do Dropbox):
   desinstale a antiga (perde dados/VIP) e instale a v14;
4. **Pouco espaço**: libere pelo menos ~700 MB;
5. **Download incompleto**: confira o SHA-256 acima.

## O que continua igual à v13

- variante `DialogWelcomeTV.xml` com área segura (TV/box/projetor/stick);
- detecção por `plataforma.txt`, resolução 16:9 ≥1280×720 ou nome do aparelho;
- campo 310 como `defaultcontrol`, teclado real do Kodi, D-pad e VOLTAR;
- anúncios: um por troca de conteúdo, nenhum para VIP, app-open por instalação;
- VIP: só ativa com `POST /api/public/validar-codigo` e `active:true`.

## Provas do build

- `static-check`: 215 XML, 63 scripts;
- `TVBoxStickTest`: 3 testes;
- passo 6: injeção byte a byte, perfil intacto, somente arquivos esperados;
- passo 6c: manifesto com 1.0.84/2103070 (bytes conferidos);
- passo 7: assinatura com o certificado `855de171...`;
- não houve execução em aparelho real neste ambiente.
