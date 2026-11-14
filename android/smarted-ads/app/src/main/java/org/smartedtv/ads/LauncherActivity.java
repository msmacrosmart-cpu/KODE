package org.smartedtv.ads;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.Process;
import android.util.Log;
import android.widget.Toast;

/**
 * Porta de entrada e plano B da ponte.
 *
 * Duas funcoes, decididas pelo DATA do intent — a ponte nunca e afetada por
 * esta tela:
 *
 *  1. POnte (plano B): no Kodi, `CXBMCApp::StartActivity` com o parametro
 *     "intent" vazio procura a activity de LAUNCHER do pacote e, se o app nao
 *     tem launcher, faz `return false`. Por isso este app TEM launcher, e ele
 *     roteia pelo data URI "smartedtv://ads/preroll" / "smartedtv://ads/appopen"
 *     para a tela de anuncio correspondente.
 *
 *  2. Icone do app (sem data): e o instalador leve. Se o SMARTEDTV (Kodi) ja
 *     esta instalado e atualizado, so abre o app; se nao esta, vai para a tela
 *     de boas-vindas que baixa e instala o APK principal.
 */
public class LauncherActivity extends Activity {

    private static final String URI_ADS = "smartedtv://ads";

    @Override
    protected void onCreate(Bundle estado) {
        super.onCreate(estado);
        Ads.aplicarIntent(getIntent());
        String uri = getIntent() == null ? null : getIntent().getDataString();
        Log.i(Ads.TAG, "LauncherActivity: abriu com data=" + uri);

        if (ehAnuncio(uri)) {
            rotearAnuncio(uri);
            return;
        }
        abrirInstaladorOuKodi();
    }

    /** Só o data URI da ponte vai para anuncio; o icone do app nunca. */
    private boolean ehAnuncio(String uri) {
        return uri != null && uri.startsWith(URI_ADS);
    }

    private void rotearAnuncio(String uri) {
        boolean preroll = uri.contains("preroll");
        Toast.makeText(this, "SMARTEDTV Ads: " + (preroll ? "video" : "abertura"),
                Toast.LENGTH_SHORT).show();

        Class<?> destino = preroll ? PreRollActivity.class : AppOpenActivity.class;
        try {
            Intent intent = new Intent(this, destino);
            Intent recebida = getIntent();
            if (recebida != null && recebida.getExtras() != null) {
                intent.putExtras(recebida.getExtras());
            }
            intent.setData(recebida == null ? null : recebida.getData());
            startActivity(intent);
            Log.i(Ads.TAG, "LauncherActivity: encaminhado para " + destino.getSimpleName());
        } catch (Throwable erro) {
            Log.e(Ads.TAG, "LauncherActivity: falha ao encaminhar: " + erro, erro);
            Toast.makeText(this, "SMARTEDTV Ads: falha " + erro, Toast.LENGTH_LONG).show();
        }
        // fecha esta ponte depois de um instante (a tela de anuncio fica na frente)
        new Handler(Looper.getMainLooper()).postDelayed(this::finish, 800);
    }

    private void abrirInstaladorOuKodi() {
        if (Kodi.instalado(this) && !Kodi.desatualizado(this)) {
            Log.i(Ads.TAG, "LauncherActivity: SMARTEDTV ja instalado ("
                    + Kodi.versaoInstalada(this) + "), abrindo");
            if (Kodi.abrir(this)) {
                finish();
                return;
            }
        }
        Log.i(Ads.TAG, "LauncherActivity: indo para a tela de instalacao (kodi="
                + (Kodi.instalado(this) ? Kodi.versaoInstalada(this) : "ausente") + ")");
        try {
            startActivity(new Intent(this, BoasVindasActivity.class));
        } catch (Throwable erro) {
            Log.e(Ads.TAG, "LauncherActivity: falha ao abrir BoasVindas: " + erro, erro);
        }
        finish();
    }

    /** O icone do app e o instalador: nao deixa a activity presa no historico. */
    @Override
    protected void onPause() {
        super.onPause();
        if (isFinishing() && !ehAnuncio(getIntent() == null ? null : getIntent().getDataString())) {
            Log.i(Ads.TAG, "LauncherActivity: saindo (pid " + Process.myPid() + ")");
        }
    }
}
