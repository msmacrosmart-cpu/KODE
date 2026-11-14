package org.smartedtv.ads;

import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.os.Build;
import android.util.Log;

/**
 * Situacao do app PRINCIPAL (SMARTED-TV / Kodi) neste aparelho.
 *
 * O pacote do Kodi e org.xbmc.kodi — declarado em <queries> no manifesto, senao
 * o Android 11+ esconde o pacote e a resposta seria sempre "nao instalado".
 */
public final class Kodi {

    /** Pacote do app principal (o mesmo do <queries> no manifesto). */
    public static final String PACOTE = "org.xbmc.kodi";

    private Kodi() {
    }

    private static PackageInfo info(Context contexto) {
        try {
            return contexto.getPackageManager().getPackageInfo(PACOTE, 0);
        } catch (PackageManager.NameNotFoundException naoAchou) {
            return null;
        } catch (Throwable erro) {
            Log.w(Ads.TAG, "Kodi: falha ao consultar o pacote: " + erro);
            return null;
        }
    }

    public static boolean instalado(Context contexto) {
        return info(contexto) != null;
    }

    /** versionCode instalado, ou -1 quando o Kodi nao esta no aparelho. */
    public static long codigoInstalado(Context contexto) {
        PackageInfo pacote = info(contexto);
        if (pacote == null) {
            return -1L;
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            return pacote.getLongVersionCode();
        }
        return pacote.versionCode;
    }

    /** "1.0.63 (2103049)" ou null quando nao esta instalado. */
    public static String versaoInstalada(Context contexto) {
        PackageInfo pacote = info(contexto);
        if (pacote == null) {
            return null;
        }
        return pacote.versionName + " (" + codigoInstalado(contexto) + ")";
    }

    /** Instalado, mas mais velho que o APK que este app distribui. */
    public static boolean desatualizado(Context contexto) {
        long codigo = codigoInstalado(contexto);
        return codigo > 0 && Instalador.CODIGO_MINIMO > 0 && codigo < Instalador.CODIGO_MINIMO;
    }

    /**
     * Abre o SMARTEDTV. Usa o intent de launcher (e o de Leanback, se houver):
     * e exatamente o mesmo caminho que o proprio Kodi usa no CXBMCApp.
     */
    public static boolean abrir(Context contexto) {
        PackageManager pm = contexto.getPackageManager();
        Intent intent = pm.getLaunchIntentForPackage(PACOTE);
        if (intent == null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            intent = pm.getLeanbackLaunchIntentForPackage(PACOTE);
        }
        if (intent == null) {
            Log.w(Ads.TAG, "Kodi: pacote instalado, mas sem intent de launcher");
            return false;
        }
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            contexto.startActivity(intent);
            Log.i(Ads.TAG, "Kodi: abrindo " + PACOTE);
            return true;
        } catch (Throwable erro) {
            Log.e(Ads.TAG, "Kodi: falha ao abrir: " + erro, erro);
            return false;
        }
    }
}
