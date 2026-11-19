#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Le o kodi.log de um aparelho e diz o que quebrou na Home.

O dono do app relatou, no projetor: notificacoes de addon com erro antes da
Home e, depois de avancar, a Home sem dados. As duas coisas aparecem no log do
Kodi - este script le o log de verdade e separa:

  * addon que o Kodi tentou abrir e nao conseguiu (``Add-on com erro``);
  * addon instalado no perfil sem o codigo (sem ``addon.xml``/``library``);
  * falha ao carregar a Home (skin, navegacao, plugin do menu);
  * excecao Python do servico do app.

Nao inventa nada: so conta o que esta escrito no log. Sem ``--exigir-limpo`` a
saida e um relatorio; com ele, sai != 0 quando encontra defeito (uso no CI).
"""
from __future__ import print_function

import io
import re
import sys

# O Kodi escreve assim quando a tela de um addon vai para o ar e falha.
PADROES_ADDON = (
    re.compile(r"Add-on (?:com erro|com erros)", re.I),
    re.compile(r"Failed to load addon[:\s]+\"?([\w.\-]+)", re.I),
    re.compile(r"ADDON::CAddonMgr.*(?:failed|could not|unable)", re.I),
    re.compile(r"ADDON::CAddon.*not (?:found|installed|enabled)", re.I),
    re.compile(r"Unable to load addon[:\s]+\"?([\w.\-]+)", re.I),
    re.compile(r"Add-on '\''?([\w.\-]+)'\''? (?:is )?(?:disabled|not installed)", re.I),
)

PADROES_HOME = (
    re.compile(r"GUIINFO.*(?:Container|ListItem).*(?:failed|empty|unavailable)", re.I),
    re.compile(r"Error loading (?:skin|window|Home)", re.I),
    re.compile(r"CGUIControlFactory.*failed", re.I),
    re.compile(r"failed to (?:load|parse) .*Home\.xml", re.I),
    re.compile(r"unable to load skin|skin .* not (?:found|available)", re.I),
    re.compile(r"GetDirectory.*(?:failed|error)", re.I),
    re.compile(r"plugin\.video\.[\w.\-]+.*(?:error|failed|exception)", re.I),
)

PADROES_SERVICO = (
    re.compile(r"service\.smarted\.bootstrap.*(?:Traceback|Error|exception)", re.I),
    re.compile(r"ModuleNotFoundError|ImportError", re.I),
    re.compile(r"PythonToCppException", re.I),
)

ID_ADDON = re.compile(r"\b((?:plugin|script|repository|skin|service|resource|metadata)"
                      r"(?:\.[\w\-]+)+)\b")


def ler(caminho):
    with io.open(caminho, 'rb') as arquivo:
        dados = arquivo.read()
    for codificacao in ('utf-8', 'latin-1'):
        try:
            return dados.decode(codificacao)
        except UnicodeDecodeError:
            continue
    return dados.decode('utf-8', 'replace')


def analisar(texto):
    resultado = {'addons': {}, 'home': [], 'servico': [], 'linhas': 0}
    for linha in texto.splitlines():
        resultado['linhas'] += 1
        for padrao in PADROES_ADDON:
            achado = padrao.search(linha)
            if not achado:
                continue
            alvo = achado.group(1) if achado.groups() else None
            if not alvo:
                achados = ID_ADDON.findall(linha)
                alvo = achados[0] if achados else '(nao nomeado no log)'
            resultado['addons'].setdefault(alvo, []).append(linha.strip())
            break
        for padrao in PADROES_HOME:
            if padrao.search(linha):
                resultado['home'].append(linha.strip())
                break
        for padrao in PADROES_SERVICO:
            if padrao.search(linha):
                resultado['servico'].append(linha.strip())
                break
    return resultado


def relatar(resultado, limite=6):
    print('linhas do log: %d' % resultado['linhas'])
    print('addons com erro: %d' % len(resultado['addons']))
    for addon, linhas in sorted(resultado['addons'].items()):
        print('  - %s (%d linha(s))' % (addon, len(linhas)))
        for linha in linhas[:2]:
            print('      %s' % linha[:300])
    print('falhas de Home/skin: %d' % len(resultado['home']))
    for linha in resultado['home'][:limite]:
        print('  ! %s' % linha[:300])
    print('erros do servico do app: %d' % len(resultado['servico']))
    for linha in resultado['servico'][:limite]:
        print('  ! %s' % linha[:300])


def defeitos(resultado):
    """Lista curta do que impede o app de funcionar (para o CI reprovar)."""
    problemas = []
    for addon in sorted(resultado['addons']):
        problemas.append('addon com erro: %s' % addon)
    if resultado['servico']:
        problemas.append('erro no servico do app (%d linha(s))' % len(resultado['servico']))
    return problemas


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    exige_limpo = '--exigir-limpo' in argv[1:]
    caminho = [a for a in argv[1:] if not a.startswith('--')][0]
    resultado = analisar(ler(caminho))
    relatar(resultado)
    problemas = defeitos(resultado)
    if exige_limpo and problemas:
        print('::error::defeitos encontrados no log do aparelho')
        for problema in problemas:
            print('::error::%s' % problema)
        return 1
    if exige_limpo:
        print('::notice::kodi.log sem addon com erro e sem falha do servico')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
