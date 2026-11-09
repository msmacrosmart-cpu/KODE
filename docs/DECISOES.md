# DECISÕES DO PROJETO (leia antes de mexer)

## O que o SmartED-TV é
App **Android TV / TV Box** nativo, em **Kotlin + Jetpack Compose**.
**Não é** um addon/skin do Kodi. Não existe (nem nunca existiu) `addon.xml`, `skin.xml`
ou Python neste repositório — a primeira versão do repo já era Kotlin.

## Decisão do usuário (definida em 2026-11-09)
- **Rota:** App Android TV (o que já existe) — corrigir a tela preta e evoluir o app.
- **Layout:** feito em XML — porém **XML de layout Android**, não XML de skin Kodi.
  O app carrega os arquivos de `app/src/main/assets/layout/` e converte em UI Compose
  em tempo de execução (motor em `ui/xmlengine/`). Ou seja: dá para desenhar/montar o
  layout em XML sem recompilar o APK.
- **Aparelhos:** TV Box (D-pad) + Android TV + celular/tablet (toque) — todos.

## Regra de ouro
Nada de reescrever tudo de uma vez. Cada mudança precisa:
1. compilar (CI verde),
2. não regredir o que já funciona,
3. ser reversível (commits pequenos).
