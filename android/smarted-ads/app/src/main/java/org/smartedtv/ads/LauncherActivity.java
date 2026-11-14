package org.smartedtv.ads;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.widget.Toast;

/**
 * Plano B da ponte.
 *
 * Motivo: no Kodi (CXBMCApp::StartActivity) o parametro "intent" vazio faz o
 * builtin procurar a activity de LAUNCHER do pacote — e se o app nao tem
 * launcher, o disparo morre ali (return false), antes de olhar o className.
 * Esta tela resolve os dois casos: da um launcher ao pacote e roteia pelo data
 * URI ("smartedtv://ads/preroll" ou "smartedtv://ads/appopen").
 */
public class LauncherActivity extends Activity {

    @Override
    protected void onCreate(Bundle estado) {
        super.onCreate(estado);
        Ads.aplicarIntent(getIntent());
        String uri = getIntent() == null ? null : getIntent().getDataString();
        Log.i(Ads.TAG, "LauncherActivity: abriu com data=" + uri);

        boolean preroll = uri != null && uri.contains("preroll");
        Toast.makeText(this, "SMARTEDTV Ads: " + (preroll ? "video" : "abertura"),
                Toast.LENGTH_SHORT).show();

        Class<?> destino = preroll ? PreRollActivity.class : AppOpenActivity.class;
        try {
            Intent intent = new Intent(this, destino);
            Intent recebida = getIntent();
            if (recebida != null && recebida.getExtras() != null) {
                intent.putExtras(recebida.getExtras());
            }
            startActivity(intent);
            Log.i(Ads.TAG, "LauncherActivity: encaminhado para " + destino.getSimpleName());
        } catch (Throwable erro) {
            Log.e(Ads.TAG, "LauncherActivity: falha ao encaminhar: " + erro, erro);
            Toast.makeText(this, "SMARTEDTV Ads: falha " + erro, Toast.LENGTH_LONG).show();
        }
        // fecha esta ponte depois de um instante (a tela de anuncio fica na frente)
        new Handler(Looper.getMainLooper()).postDelayed(this::finish, 800);
    }
}
