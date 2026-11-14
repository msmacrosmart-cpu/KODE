package org.smartedtv.ads;

import android.content.Context;
import android.content.Intent;
import android.util.Log;

import com.google.android.gms.ads.MobileAds;
import com.google.android.gms.ads.RequestConfiguration;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Constantes, modo de teste e inicializacao unica do AdMob.
 *
 * Todos os logs usam a tag "SmartAds" (no logcat: adb logcat -s SmartAds), em
 * cada etapa: inicializacao, qual bloco esta sendo usado, loaded/failed com o
 * codigo numerico do erro e o fechamento da tela.
 */
public final class Ads {

    /** Tag unica de diagnostico (aparece no logcat e nos relatorios). */
    public static final String TAG = "SmartAds";

    /** APPLICATION_ID do AdMob (o mesmo do AndroidManifest.xml). */
    public static final String APP_ID = "ca-app-pub-2066014755407744~5076693043";

    /** Blocos REAIS do projeto. */
    public static final String UNIT_APP_OPEN = "ca-app-pub-2066014755407744/4214378379";
    public static final String UNIT_PREROLL = "ca-app-pub-2066014755407744/3572039686";

    /**
     * Blocos de TESTE oficiais do Google: sempre tem inventario, o que isola
     * "a ponte funciona?" de "a conta tem anuncio?".
     * App Open: ca-app-pub-3940256099942544/9257395921
     * Interstitial (video): ca-app-pub-3940256099942544/1033173712
     */
    public static final String UNIT_APP_OPEN_TESTE = "ca-app-pub-3940256099942544/9257395921";
    public static final String UNIT_PREROLL_TESTE = "ca-app-pub-3940256099942544/1033173712";

    /** Ligado por build (-PadsTeste=true) e desligavel em tempo de execucao. */
    private static boolean teste = BuildConfig.ADS_TESTE;

    private static boolean inicializado;

    private Ads() {
    }

    public static boolean testeAtivo() {
        return teste;
    }

    public static String unidadeAppOpen() {
        return teste ? UNIT_APP_OPEN_TESTE : UNIT_APP_OPEN;
    }

    public static String unidadePreRoll() {
        return teste ? UNIT_PREROLL_TESTE : UNIT_PREROLL;
    }

    /**
     * Permite trocar o modo de teste sem recompilar, pelo data URI do intent:
     * StartAndroidActivity(pkg,,,,,"", "", "", "", classe) com data
     * smartedtv://ads?teste=0 ou =1. Sem data, vale o padrao do build.
     */
    public static void aplicarIntent(Intent intent) {
        if (intent == null) {
            return;
        }
        String data = intent.getDataString();
        if (data == null || !data.contains("teste=")) {
            return;
        }
        boolean antes = teste;
        teste = data.endsWith("teste=0") ? false : true;
        Log.i(TAG, "modo de teste alterado pelo intent (" + data + "): " + antes + " -> " + teste);
    }

    public static synchronized void init(Context context) {
        if (inicializado) {
            return;
        }
        inicializado = true;
        try {
            List<String> dispositivos = new ArrayList<>();
            if (BuildConfig.ADS_TESTE_HASH != null && !BuildConfig.ADS_TESTE_HASH.trim().isEmpty()) {
                dispositivos.add(BuildConfig.ADS_TESTE_HASH.trim());
            }
            MobileAds.setRequestConfiguration(
                    new RequestConfiguration.Builder()
                            .setTestDeviceIds(dispositivos.isEmpty()
                                    ? Arrays.<String>asList() : dispositivos)
                            .build());
            Log.i(TAG, "config: teste=" + teste
                    + " unidades=" + (teste ? "TESTE do Google" : "REAIS do projeto")
                    + " appId=" + APP_ID
                    + " dispositivosDeTeste=" + dispositivos);
            MobileAds.initialize(context, status ->
                    Log.i(TAG, "AdMob inicializado: " + status.getAdapterStatusMap().keySet()));
        } catch (Throwable erro) {
            Log.e(TAG, "AdMob nao inicializou: " + erro, erro);
        }
    }
}
