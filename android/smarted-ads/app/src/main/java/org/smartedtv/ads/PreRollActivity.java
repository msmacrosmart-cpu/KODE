package org.smartedtv.ads;

import com.google.android.gms.ads.AdError;
import com.google.android.gms.ads.AdRequest;
import com.google.android.gms.ads.FullScreenContentCallback;
import com.google.android.gms.ads.LoadAdError;
import com.google.android.gms.ads.ResponseInfo;
import com.google.android.gms.ads.interstitial.InterstitialAd;
import com.google.android.gms.ads.interstitial.InterstitialAdLoadCallback;

/**
 * GATILHO 2 — video pre-roll antes de canal/filme/serie.
 *
 * Bloco real: ca-app-pub-2066014755407744/3572039686.
 * Em modo de teste usa o bloco de teste do Google (sempre preenche).
 */
public class PreRollActivity extends AdActivity {

    private InterstitialAd anuncio;

    @Override
    protected void carregar() {
        String unidade = Ads.unidadePreRoll();
        log("carregando VIDEO unidade=" + unidade + " (teste=" + Ads.testeAtivo() + ")");
        InterstitialAd.load(this, unidade, new AdRequest.Builder().build(),
                new InterstitialAdLoadCallback() {
                    @Override
                    public void onAdLoaded(InterstitialAd carregado) {
                        anuncio = carregado;
                        ResponseInfo info = carregado.getResponseInfo();
                        log("onAdLoaded VIDEO | responseId=" + (info == null ? "?" : info.getResponseId())
                                + " adapters=" + (info == null ? "?" : info.getAdapterResponses().size()));
                        anuncio.setFullScreenContentCallback(new FullScreenContentCallback() {
                            @Override
                            public void onAdShowedFullScreenContent() {
                                log("onAdShowedFullScreenContent VIDEO (anuncio na tela)");
                            }

                            @Override
                            public void onAdImpression() {
                                log("onAdImpression VIDEO (impressao contabilizada)");
                            }

                            @Override
                            public void onAdClicked() {
                                log("onAdClicked VIDEO");
                            }

                            @Override
                            public void onAdDismissedFullScreenContent() {
                                log("onAdDismissedFullScreenContent VIDEO");
                                fechar("video encerrado");
                            }

                            @Override
                            public void onAdFailedToShowFullScreenContent(AdError erro) {
                                mostrarDiagnostico("Falha ao EXIBIR o video",
                                        AppOpenActivity.descrever(erro));
                            }
                        });
                        try {
                            anuncio.show(PreRollActivity.this);
                        } catch (Throwable erro) {
                            mostrarDiagnostico("Excecao ao exibir o video", erro.toString());
                        }
                    }

                    @Override
                    public void onAdFailedToLoad(LoadAdError erro) {
                        mostrarDiagnostico("Falha ao CARREGAR o video",
                                AppOpenActivity.descrever(erro));
                    }
                });
    }
}
