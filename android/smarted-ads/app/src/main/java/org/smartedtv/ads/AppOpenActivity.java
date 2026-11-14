package org.smartedtv.ads;

import com.google.android.gms.ads.AdError;
import com.google.android.gms.ads.AdRequest;
import com.google.android.gms.ads.FullScreenContentCallback;
import com.google.android.gms.ads.LoadAdError;
import com.google.android.gms.ads.ResponseInfo;
import com.google.android.gms.ads.appopen.AppOpenAd;

/**
 * GATILHO 1 — anuncio de abertura (App Open).
 *
 * Bloco real: ca-app-pub-2066014755407744/4214378379.
 * Em modo de teste usa o bloco de teste do Google (sempre preenche).
 */
public class AppOpenActivity extends AdActivity {

    private AppOpenAd anuncio;

    @Override
    protected void carregar() {
        String unidade = Ads.unidadeAppOpen();
        log("carregando ABERTURA unidade=" + unidade + " (teste=" + Ads.testeAtivo() + ")");
        AppOpenAd.load(this, unidade, new AdRequest.Builder().build(),
                new AppOpenAd.AppOpenAdLoadCallback() {
                    @Override
                    public void onAdLoaded(AppOpenAd carregado) {
                        anuncio = carregado;
                        ResponseInfo info = carregado.getResponseInfo();
                        log("onAdLoaded ABERTURA | responseId=" + (info == null ? "?" : info.getResponseId())
                                + " adapters=" + (info == null ? "?" : info.getAdapterResponses().size()));
                        anuncio.setFullScreenContentCallback(new FullScreenContentCallback() {
                            @Override
                            public void onAdShowedFullScreenContent() {
                                log("onAdShowedFullScreenContent ABERTURA (anuncio na tela)");
                            }

                            @Override
                            public void onAdImpression() {
                                log("onAdImpression ABERTURA (impressao contabilizada)");
                            }

                            @Override
                            public void onAdClicked() {
                                log("onAdClicked ABERTURA");
                            }

                            @Override
                            public void onAdDismissedFullScreenContent() {
                                log("onAdDismissedFullScreenContent ABERTURA");
                                fechar("abertura fechada pelo usuario");
                            }

                            @Override
                            public void onAdFailedToShowFullScreenContent(AdError erro) {
                                mostrarDiagnostico("Falha ao EXIBIR a abertura",
                                        descrever(erro));
                            }
                        });
                        try {
                            anuncio.show(AppOpenActivity.this);
                        } catch (Throwable erro) {
                            mostrarDiagnostico("Excecao ao exibir a abertura", erro.toString());
                        }
                    }

                    @Override
                    public void onAdFailedToLoad(LoadAdError erro) {
                        mostrarDiagnostico("Falha ao CARREGAR a abertura", descrever(erro));
                    }
                });
    }

    /** Codigo numerico do AdMob + dominio + mensagem (vai para o logcat e a tela). */
    static String descrever(AdError erro) {
        if (erro == null) {
            return "erro nulo";
        }
        return "codigo=" + erro.getCode()
                + " dominio=" + erro.getDomain()
                + "\nmensagem=" + erro.getMessage()
                + (erro.getCause() == null ? "" : "\ncausa=" + erro.getCause());
    }

    static String descrever(LoadAdError erro) {
        if (erro == null) {
            return "erro nulo";
        }
        return "codigo=" + erro.getCode()
                + " dominio=" + erro.getDomain()
                + "\nmensagem=" + erro.getMessage()
                + "\nresponseId=" + (erro.getResponseInfo() == null ? "?"
                        : erro.getResponseInfo().getResponseId())
                + (erro.getCause() == null ? "" : "\ncausa=" + erro.getCause());
    }
}
