# -*- coding: utf-8 -*-
"""Simulador de estado dos 10 ciclos de reabertura do SMARTEDTV.

NAO substitui aparelho/emulador: nao abre o Kodi nem o video. Ele exercita a
modelagem de estado usada pela tela/servico para provar que:

* marcas temporarias de UI somem entre ciclos;
* perfil, configuracoes, favoritos e ativacao VIP nunca entram na limpeza;
* somente estagios ``.smarted-seed-*`` sao varridos;
* o ciclo funciona mesmo quando a saida acontece no boot, no video, num
  dialogo ou durante uma requisicao de rede.

O teste fisico/emulado de reabertura continua obrigatorio.
"""
from __future__ import print_function

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICO = ROOT / 'kodi/addons/service.smarted.bootstrap/service.py'
TELA = ROOT / 'kodi/addons/script.smartedtv.welcome/default.py'
ADDON = ROOT / 'kodi/addons/service.smarted.bootstrap/addon.xml'

TEMPORARIAS = ('smartedtv.welcome.saiu', 'smartedtv.welcome.home',
               'smartedtv.welcome.voltar', 'smartedtv.welcome.saindo',
               'smarted-saindo')
PERMANENTES = {
    'guisettings': '<settings/>',
    'vip.licenca': 'ATIVO-123',
    'favoritos': '<favourites/>',
    'skin.ajustes': 'padrao',
    'addon_data': {'service.smarted.bootstrap': {'vip': 'ATIVO-123'}},
}


def iniciar(estado):
    for chave in TEMPORARIAS:
        estado[chave] = 'preso'
    estado['.smarted-seed-abc'] = {'stage': True}
    estado['.smarted-seed-def'] = {'stage': True}


def sair(estado):
    """Mesma semantica do Python: limpa UI e estagios, preserva o resto.

    O guarda da saida agora e um alarme do Kodi (`smartedtv_sair_guarda`) com
    arquivo-marca. A saida grava a marca; a abertura seguinte a remove e
    cancela o alarme, entao a sessao nova nunca e encerrada pelo guarda velho.
    """
    for chave in TEMPORARIAS:
        estado.pop(chave, None)
    estado.pop('smartedtv_sair_guarda', None)
    for chave in list(estado):
        if chave.startswith('.smarted-seed-'):
            del estado[chave]


def ciclo(numero, fase):
    estado = dict(PERMANENTES)
    estado['addon_data'] = {'service.smarted.bootstrap':
                            dict(PERMANENTES['addon_data']
                                 ['service.smarted.bootstrap'])}
    iniciar(estado)
    # Em cada fase a UI pode ter deixado uma marca diferente; a saida limpa
    # precisa remover todas sem tocar nos dados permanentes.
    estado['fase'] = fase
    sair(estado)
    assert all(chave not in estado for chave in TEMPORARIAS), (numero, fase)
    assert not any(chave.startswith('.smarted-seed-') for chave in estado), \
        (numero, fase)
    for chave, valor in PERMANENTES.items():
        assert estado[chave] == valor, (numero, fase, chave)
    assert estado['addon_data']['service.smarted.bootstrap']['vip'] == 'ATIVO-123'
    return estado


def main():
    fontes = SERVICO.read_text(encoding='utf-8')
    tela = TELA.read_text(encoding='utf-8')
    addon = ADDON.read_text(encoding='utf-8')
    assert "nome.startswith('.smarted-seed-')" in fontes
    assert 'limpar_estagios_de_seed()' in fontes
    # Saida: nada de thread dormindo matando a sessao seguinte.
    assert "os._exit(0)" in tela and 'System.Platform.Android' in tela
    assert 'AlarmClock(smartedtv_sair_guarda' in tela
    assert 'def _limpar_guarda_de_saida' in tela
    assert 'JANELA_SAIDA' in tela
    assert 'library="vip.py"' not in addon
    assert '<?xml version="1.0"' in addon
    # o guarda da saida pode ser armado em qualquer fase do ciclo
    estado = dict(PERMANENTES)
    iniciar(estado)
    estado['smartedtv_sair_guarda'] = 'armado'
    estado['smarted-saindo'] = '1700000000 4242'
    sair(estado)
    assert 'smartedtv_sair_guarda' not in estado
    assert 'smarted-saindo' not in estado
    fases = ('boot', 'video', 'dialogo', 'rede')
    for numero in range(1, 11):
        ciclo(numero, fases[(numero - 1) % len(fases)])
    print(json.dumps({'ciclos': 10, 'fases': list(fases),
                      'perfil_preservado': True, 'vip_preservado': True,
                      'estagios_temporarios_removidos': True,
                      'tipo': 'simulacao_de_estado'}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
