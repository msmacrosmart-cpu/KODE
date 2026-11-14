package org.smartedtv.ads;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;
import android.widget.TextView;

/**
 * Base das telas de anuncio.
 *
 * Regras:
 *  - SEMPRE horizontal (TV Box / projetor nao tem vertical);
 *  - tela cheia, sem barra de status/navegacao, tela nao apaga;
 *  - nunca prende o usuario: se o anuncio nao carregar, a tela se fecha sozinha
 *    em {@link #LIMITE_SEM_ANUNCIO} ms;
 *  - em modo de TESTE, qualquer falha aparece ESCRITA na tela (codigo numerico
 *    do AdMob), para diagnosticar sem precisar de adb/logcat.
 */
public abstract class AdActivity extends Activity {

    /** Depois disso a tela de anuncio se fecha e devolve o usuario ao Kodi. */
    protected static final long LIMITE_SEM_ANUNCIO = 20000L;

    /** Quanto tempo o painel de erro fica na tela (modo de teste). */
    private static final long LIMITE_PAINEL_ERRO = 9000L;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean fechando;
    private FrameLayout fundo;
    private TextView painel;

    private final Runnable fecharPorTempo = () -> {
        Log.w(Ads.TAG, nome() + ": tempo esgotado (" + LIMITE_SEM_ANUNCIO
                + " ms) sem anuncio, fechando");
        fechar("timeout");
    };

    @Override
    protected void onCreate(Bundle estado) {
        super.onCreate(estado);
        Ads.aplicarIntent(getIntent());
        Ads.init(getApplicationContext());

        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        entrarEmTelaCheia();

        fundo = new FrameLayout(this);
        fundo.setBackgroundColor(Color.BLACK);
        setContentView(fundo);

        log("aberta | pacote=" + getPackageName()
                + " versao=" + BuildConfig.VERSION_NAME + "(" + BuildConfig.VERSION_CODE + ")"
                + " teste=" + Ads.testeAtivo()
                + " android=" + Build.VERSION.RELEASE
                + " intent=" + descreverIntent(getIntent()));

        handler.postDelayed(fecharPorTempo, LIMITE_SEM_ANUNCIO);
        carregar();
    }

    private String descreverIntent(Intent intent) {
        if (intent == null) {
            return "(sem intent)";
        }
        return "{action=" + intent.getAction()
                + " data=" + intent.getDataString()
                + " de=" + intent.getPackage() + "}";
    }

    @SuppressWarnings("deprecation")
    private void entrarEmTelaCheia() {
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                        | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_FULLSCREEN
                        | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
    }

    /** Carrega o anuncio desta tela e, dando certo, exibe. */
    protected abstract void carregar();

    /** Fecha a tela e devolve o foco ao Kodi (idempotente). */
    protected synchronized void fechar(String motivo) {
        if (fechando) {
            return;
        }
        fechando = true;
        handler.removeCallbacks(fecharPorTempo);
        log("fechando (" + motivo + ")");
        try {
            if (!isFinishing()) {
                finish();
            }
        } catch (Throwable erro) {
            Log.w(Ads.TAG, nome() + ": erro ao fechar: " + erro);
        }
        overridePendingTransition(0, 0);
    }

    /**
     * Mostra o motivo da falha na propria tela (modo de teste) e fecha depois
     * de alguns segundos. Com isso o codigo do erro do AdMob aparece na TV.
     */
    protected void mostrarDiagnostico(String titulo, String detalhe) {
        Log.w(Ads.TAG, nome() + ": " + titulo + " | " + detalhe);
        if (!Ads.testeAtivo() || fundo == null) {
            fechar(titulo);
            return;
        }
        painel = new TextView(this);
        painel.setText("SMARTEDTV Ads — diagnostico\n\n" + titulo + "\n\n" + detalhe
                + "\n\n(pacote " + getPackageName() + " " + BuildConfig.VERSION_NAME + ")");
        painel.setTextColor(Color.WHITE);
        painel.setTextSize(16f);
        painel.setGravity(Gravity.CENTER);
        painel.setBackgroundColor(Color.rgb(20, 20, 20));
        painel.setPadding(48, 48, 48, 48);
        fundo.addView(painel, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        handler.removeCallbacks(fecharPorTempo);
        handler.postDelayed(() -> fechar("diagnostico exibido"), LIMITE_PAINEL_ERRO);
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacks(fecharPorTempo);
        super.onDestroy();
    }

    protected String nome() {
        return getClass().getSimpleName();
    }

    protected void log(String mensagem) {
        Log.i(Ads.TAG, nome() + ": " + mensagem);
    }
}
