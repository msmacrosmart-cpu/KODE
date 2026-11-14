package org.smartedtv.ads;

import android.app.Activity;
import android.content.pm.ActivityInfo;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.View;
import android.view.WindowManager;
import android.widget.FrameLayout;

/**
 * Base das telas de anuncio.
 *
 * Regras que valem para as duas:
 *  - SEMPRE horizontal (TV Box / projetor nao tem vertical);
 *  - tela cheia de verdade (sem barra de status, sem navegacao);
 *  - tela nao apaga durante o anuncio;
 *  - nunca prende o usuario: se o anuncio nao carregar ou nao fechar, a tela
 *    se fecha sozinha em {@link #LIMITE_SEM_ANUNCIO} ms e o Kodi continua.
 */
public abstract class AdActivity extends Activity {

    private static final String TAG = "SmartAd";

    /** Depois disso a tela de anuncio se fecha e devolve o usuario ao Kodi. */
    protected static final long LIMITE_SEM_ANUNCIO = 20000L;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean fechando;

    private final Runnable fecharPorTempo = () -> {
        Log.w(TAG, getClass().getSimpleName() + ": tempo esgotado, fechando sem anuncio");
        fechar();
    };

    @Override
    protected void onCreate(Bundle estado) {
        super.onCreate(estado);
        Ads.init(getApplicationContext());

        // horizontal sempre, mesmo se o Kodi estiver em outra orientacao
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        entrarEmTelaCheia();

        FrameLayout fundo = new FrameLayout(this);
        fundo.setBackgroundColor(Color.BLACK);
        setContentView(fundo);

        handler.postDelayed(fecharPorTempo, LIMITE_SEM_ANUNCIO);
        carregar();
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
    protected synchronized void fechar() {
        if (fechando) {
            return;
        }
        fechando = true;
        handler.removeCallbacks(fecharPorTempo);
        try {
            if (!isFinishing()) {
                finish();
            }
        } catch (Throwable erro) {
            Log.w(TAG, "fechar: " + erro);
        }
        // devolve o foco para quem chamou (Kodi)
        overridePendingTransition(0, 0);
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacks(fecharPorTempo);
        super.onDestroy();
    }

    protected void log(String mensagem) {
        Log.i(TAG, getClass().getSimpleName() + ": " + mensagem);
    }
}
