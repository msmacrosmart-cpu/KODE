# SMARTEDTV — Janela de boas-vindas para Kodi Omega 21

## Conteúdo
- `default.py`: ponto de entrada e controlador `WindowXMLDialog`.
- `resources/skins/Default/1080i/DialogWelcome.xml`: interface nativa do Kodi.
- `resources/skins/Default/media/`: fundo, botões, painel do diálogo e QR ilustrativos extraídos do SVG do `preview.html`.

## Instalação
1. Copie a pasta `script.smartedtv.welcome` para `addons/` do Kodi, ou compacte a pasta e instale pelo menu de addons.
2. Abra o addon **SMARTEDTV - Welcome Screen** para exibir a janela.

## Limites desta versão
Esta entrega implementa a janela visual independente. Não conecta nem simula:
- validação real do código VIP;
- compartilhamento nativo do aplicativo;
- abertura funcional do checkout externo;
- transição para o modo gratuito com anúncios do SMARTEDTV.

Essas ações dependem das funções reais do addon principal, que não foram fornecidas. Os QR Codes foram reproduzidos como os desenhos SVG presentes no HTML; não foram recriados como QR dinâmicos.

## Verificações realizadas
- XML analisado quanto à boa formação.
- Python compilado sintaticamente.
- ZIP reaberto e conteúdo conferido.
- Não foi possível executar dentro do Kodi nesta sessão.
