package org.smartedtv.ads;

import com.google.android.gms.ads.AdError;
import com.google.android.gms.ads.AdRequest;
import com.google.android.gms.ads.FullScreenContentCallback;
import com.google.android.gms.ads.LoadAdError;
import com.google.android.gms.ads.appopen.AppOpenAd;

/**
 * GATILHO 1 — anuncio de abertura.
 *
 * Aberto pelo Kodi uma unica vez, logo depois de a interface principal ficar
 * pronta (o Python grava a marca em userdata para nao repetir). Bloco:
 * ca-app-pub-2066014755407744/4214378379.
 */
public class AppOpenActivity extends AdActivity {

    private AppOpenAd anuncio;

    @Override
    protected void carregar() {
        log("carregando abertura (" + Ads.UNIT_APP_OPEN + ")");
        AppOpenAd.load(this, Ads.UNIT_APP_OPEN, new AdRequest.Builder().build(),
                new AppOpenAd.AppOpenAdLoadCallback() {
                    @Override
                    public void onAdLoaded(AppOpenAd carregado) {
                        anuncio = carregado;
                        anuncio.setFullScreenContentCallback(new FullScreenContentCallback() {
                            @Override
                            public void onAdDismissedFullScreenContent() {
                                log("abertura fechada");
                                fechar();
                            }

                            @Override
                            public void onAdFailedToShowFullScreenContent(AdError erro) {
                                log("abertura nao pode ser exibida: " + erro);
                                fechar();
                            }
                        });
                        try {
                            anuncio.show(AppOpenActivity.this);
                        } catch (Throwable erro) {
                            log("falha ao exibir abertura: " + erro);
                            fechar();
                        }
                    }

                    @Override
                    public void onAdFailedToLoad(LoadAdError erro) {
                        // sem inventario / sem rede: nao atrapalha a abertura do app
                        log("abertura sem anuncio: " + erro);
                        fechar();
                    }
                });
    }
}
