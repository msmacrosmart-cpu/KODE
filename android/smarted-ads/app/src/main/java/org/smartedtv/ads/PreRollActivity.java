package org.smartedtv.ads;

import com.google.android.gms.ads.AdError;
import com.google.android.gms.ads.AdRequest;
import com.google.android.gms.ads.FullScreenContentCallback;
import com.google.android.gms.ads.LoadAdError;
import com.google.android.gms.ads.interstitial.InterstitialAd;
import com.google.android.gms.ads.interstitial.InterstitialAdLoadCallback;

/**
 * GATILHO 2 — video pre-roll antes de canal/filme/serie.
 *
 * O Python do Kodi (xbmc.Player.onPlay) abre esta tela assim que o stream
 * comeca a ser preparado: o anuncio cobre a tela em quanto o player faz o
 * buffer atras. Ao fechar, o Kodi volta em primeiro plano com o video ja
 * pronto. Bloco: ca-app-pub-2066014755407744/3572039686.
 */
public class PreRollActivity extends AdActivity {

    private InterstitialAd anuncio;

    @Override
    protected void carregar() {
        log("carregando video (" + Ads.UNIT_PREROLL + ")");
        InterstitialAd.load(this, Ads.UNIT_PREROLL, new AdRequest.Builder().build(),
                new InterstitialAdLoadCallback() {
                    @Override
                    public void onAdLoaded(InterstitialAd carregado) {
                        anuncio = carregado;
                        anuncio.setFullScreenContentCallback(new FullScreenContentCallback() {
                            @Override
                            public void onAdDismissedFullScreenContent() {
                                log("video encerrado");
                                fechar();
                            }

                            @Override
                            public void onAdFailedToShowFullScreenContent(AdError erro) {
                                log("video nao pode ser exibido: " + erro);
                                fechar();
                            }
                        });
                        try {
                            anuncio.show(PreRollActivity.this);
                        } catch (Throwable erro) {
                            log("falha ao exibir video: " + erro);
                            fechar();
                        }
                    }

                    @Override
                    public void onAdFailedToLoad(LoadAdError erro) {
                        // nunca segurar o usuario: sem anuncio, volta direto ao video
                        log("video sem anuncio: " + erro);
                        fechar();
                    }
                });
    }
}
