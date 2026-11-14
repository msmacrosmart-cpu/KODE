package org.smartedtv.ads;

import android.content.Context;
import android.util.Log;

import com.google.android.gms.ads.MobileAds;
import com.google.android.gms.ads.RequestConfiguration;

import java.util.Collections;

/**
 * Constantes e inicializacao unica do AdMob.
 *
 * O app so existe para mostrar anuncio em cima do Kodi (ver PreRollActivity e
 * AppOpenActivity); quem abre as telas e o Python do Kodi, pela ponte nativa
 * StartAndroidActivity().
 */
public final class Ads {

    private static final String TAG = "SmartAd";

    /** Bloco de abertura (App Open / pop-up inicial). */
    public static final String UNIT_APP_OPEN = "ca-app-pub-2066014755407744/4214378379";

    /** Bloco em video, exibido antes de canal/filme/serie. */
    public static final String UNIT_PREROLL = "ca-app-pub-2066014755407744/3572039686";

    /** APPLICATION_ID do AdMob (o mesmo do AndroidManifest.xml). */
    public static final String APP_ID = "ca-app-pub-2066014755407744~5076693043";

    private static boolean inicializado;

    private Ads() {
    }

    public static synchronized void init(Context context) {
        if (inicializado) {
            return;
        }
        inicializado = true;
        try {
            // sem rastreamento de crianca: anuncios normais, como pedido
            MobileAds.setRequestConfiguration(
                    new RequestConfiguration.Builder()
                            .setTagForChildDirectedTreatment(
                                    RequestConfiguration.TAG_FOR_CHILD_DIRECTED_TREATMENT_UNSPECIFIED)
                            .setTestDeviceIds(Collections.<String>emptyList())
                            .build());
            MobileAds.initialize(context, initializationStatus ->
                    Log.i(TAG, "AdMob pronto"));
        } catch (Throwable erro) {
            Log.w(TAG, "AdMob nao inicializou: " + erro);
        }
    }
}
