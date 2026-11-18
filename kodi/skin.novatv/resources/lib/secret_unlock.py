#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Secret Unlock — Brazuka Play Skin
# 8 cliques no logo (top-left) + 2 ciclos completos de entrar/sair no Settings
# Libera configurações avançadas quando ambas condições são satisfeitas
#
# Implementação: usa Skin.SetSetting/Skin.GetSetting (built-in do Kodi)
#
# Variáveis:
#   secret_click_count  — número de cliques no logo (0-8)
#   secret_settings_cycle — número de ciclos completos Settings (0-2)
#   secret_unlocked     — 1 quando desbloqueado, 0 quando bloqueado

import xbmc
import xbmcgui

def increment_click():
    """Incrementa a contagem de cliques no logo."""
    try:
        current = int(xbmc.getSetting("secret_click_count"))
    except (ValueError, TypeError):
        current = 0

    if current >= 7:
        # Reset após 8 cliques
        xbmc.setSetting("secret_click_count", "0")
        # Incrementa o ciclo de Settings
        try:
            cycle = int(xbmc.getSetting("secret_settings_cycle"))
        except (ValueError, TypeError):
            cycle = 0
        xbmc.setSetting("secret_settings_cycle", str(cycle + 1))

        # Verificar se unlock foi atingido
        if cycle + 1 >= 2:
            xbmc.setSetting("secret_unlocked", "1")
            xbmcgui.Dialog().notification(
                "Brazuka Play",
                "Configurações avançadas liberadas!",
                xbmcgui.NOTIFICATION_SUCCESS,
                5000
            )
        else:
            xbmcgui.Dialog().notification(
                "Brazuka Play",
                f"Ciclo {cycle + 1}/2 no Settings necessário",
                xbmcgui.NOTIFICATION_INFO,
                3000
            )
    else:
        xbmc.setSetting("secret_click_count", str(current + 1))

        # Notificar progresso (opcional, discreto)
        if current + 1 == 8:
            xbmcgui.Dialog().notification(
                "Brazuka Play",
                "8 cliques! Abra Settings 2 vezes para liberar",
                xbmcgui.NOTIFICATION_INFO,
                3000
            )

def check_unlocked():
    """Verifica se o unlock foi atingido."""
    try:
        clicks = int(xbmc.getSetting("secret_click_count"))
    except (ValueError, TypeError):
        clicks = 0

    try:
        cycle = int(xbmc.getSetting("secret_settings_cycle"))
    except (ValueError, TypeError):
        cycle = 0

    if clicks >= 8 and cycle >= 2:
        xbmc.setSetting("secret_unlocked", "1")
        return True
    return False

def reset_unlock():
    """Reverté o unlock (usado para teste/debug)."""
    xbmc.setSetting("secret_click_count", "0")
    xbmc.setSetting("secret_settings_cycle", "0")
    xbmc.setSetting("secret_unlocked", "0")

if __name__ == "__main__":
    increment_click()
