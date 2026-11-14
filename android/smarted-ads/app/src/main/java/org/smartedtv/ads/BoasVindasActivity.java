package org.smartedtv.ads;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

/**
 * Tela de boas-vindas / instalacao do app PRINCIPAL.
 *
 * Fluxo:
 *  1. Kodi ja instalado e atualizado -> "pronto", botao abre o SMARTEDTV;
 *  2. Kodi ausente -> baixa o APK principal sozinho (DownloadManager) com barra
 *     de progresso e, ao terminar, abre a tela de instalacao do Android;
 *  3. Kodi instalado mas velho -> oferece ATUALIZAR.
 *
 * Nada aqui toca no AdMob: as telas de anuncio (AppOpenActivity/PreRollActivity)
 * e a ponte do StartAndroidActivity seguem exatamente como estavam.
 */
public class BoasVindasActivity extends Activity {

    /** Codigo do retorno da tela de permissao de instalacao. */
    private static final int PEDIDO_PERMISSAO = 4701;
    private static final long INTERVALO_PROGRESSO = 700L;
    private static final long ESPERA_ANTES_DE_BAIXAR = 1500L;

    private final Handler handler = new Handler(Looper.getMainLooper());

    private TextView titulo;
    private TextView status;
    private TextView detalhe;
    private ProgressBar barra;
    private Button principal;
    private Button secundario;

    private boolean instalacaoDisparada;

    private final Runnable acompanhar = new Runnable() {
        @Override
        public void run() {
            atualizar();
            handler.postDelayed(this, INTERVALO_PROGRESSO);
        }
    };

    private final Runnable baixarSozinho = () -> {
        if (Kodi.instalado(this) && !Kodi.desatualizado(this)) {
            return;
        }
        if (Instalador.jaBaixado(this) || Instalador.progresso(this).rodando()) {
            return;
        }
        log("iniciando o download automatico");
        iniciarDownload(true);
    };

    @Override
    protected void onCreate(Bundle estado) {
        super.onCreate(estado);
        setRequestedOrientation(android.content.pm.ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        montarTela();
        log("aberta | pacote=" + getPackageName()
                + " versao=" + BuildConfig.VERSION_NAME + "(" + BuildConfig.VERSION_CODE + ")"
                + " kodi=" + (Kodi.instalado(this) ? Kodi.versaoInstalada(this) : "ausente")
                + " url=" + Instalador.URL_APK);
        // deixa a tela aparecer antes de comecar a puxar 242 MB
        handler.postDelayed(baixarSozinho, ESPERA_ANTES_DE_BAIXAR);
    }

    @Override
    protected void onResume() {
        super.onResume();
        handler.removeCallbacks(acompanhar);
        handler.post(acompanhar);
    }

    @Override
    protected void onPause() {
        handler.removeCallbacks(acompanhar);
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacks(baixarSozinho);
        handler.removeCallbacks(acompanhar);
        super.onDestroy();
    }

    @Override
    public void onConfigurationChanged(Configuration nova) {
        super.onConfigurationChanged(nova);
    }

    @Override
    protected void onActivityResult(int pedido, int resultado, android.content.Intent dados) {
        super.onActivityResult(pedido, resultado, dados);
        if (pedido == PEDIDO_PERMISSAO) {
            log("voltou da permissao de instalacao: podeInstalar=" + Instalador.podeInstalar(this));
            if (Instalador.podeInstalar(this) && Instalador.jaBaixado(this)) {
                Instalador.instalar(this);
            }
            atualizar();
        }
    }

    // ------------------------------------------------------------------ tela

    private void montarTela() {
        FrameLayout fundo = new FrameLayout(this);
        fundo.setBackgroundColor(Color.rgb(12, 12, 12));

        LinearLayout coluna = new LinearLayout(this);
        coluna.setOrientation(LinearLayout.VERTICAL);
        coluna.setGravity(Gravity.CENTER);
        int margem = dp(56);
        coluna.setPadding(margem, margem, margem, margem);

        titulo = texto("SMARTEDTV", 40f, Color.WHITE, true);
        titulo.setGravity(Gravity.CENTER);
        coluna.addView(titulo);

        status = texto("Verificando o aparelho...", 22f, Color.rgb(210, 210, 210), false);
        status.setGravity(Gravity.CENTER);
        status.setPadding(0, dp(18), 0, 0);
        coluna.addView(status);

        barra = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        barra.setIndeterminate(false);
        barra.setMax(100);
        LinearLayout.LayoutParams medidaBarra =
                new LinearLayout.LayoutParams(dp(520), dp(14));
        medidaBarra.topMargin = dp(26);
        barra.setLayoutParams(medidaBarra);
        barra.setVisibility(View.GONE);
        coluna.addView(barra);

        detalhe = texto("", 16f, Color.rgb(150, 150, 150), false);
        detalhe.setGravity(Gravity.CENTER);
        detalhe.setPadding(0, dp(16), 0, 0);
        coluna.addView(detalhe);

        principal = botao("Baixar e instalar");
        LinearLayout.LayoutParams medidaBotao =
                new LinearLayout.LayoutParams(dp(420), ViewGroup.LayoutParams.WRAP_CONTENT);
        medidaBotao.topMargin = dp(30);
        principal.setLayoutParams(medidaBotao);
        principal.setOnClickListener(v -> aoTocarPrincipal());
        coluna.addView(principal);

        secundario = botao("Verificar de novo");
        LinearLayout.LayoutParams medidaSecundario =
                new LinearLayout.LayoutParams(dp(300), ViewGroup.LayoutParams.WRAP_CONTENT);
        medidaSecundario.topMargin = dp(12);
        secundario.setLayoutParams(medidaSecundario);
        secundario.setOnClickListener(v -> atualizar());
        coluna.addView(secundario);

        fundo.addView(coluna, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
        setContentView(fundo);
        entrarEmTelaCheia();
    }

    private TextView texto(String conteudo, float tamanho, int cor, boolean negrito) {
        TextView vista = new TextView(this);
        vista.setText(conteudo);
        vista.setTextSize(TypedValue.COMPLEX_UNIT_SP, tamanho);
        vista.setTextColor(cor);
        if (negrito) {
            vista.setTypeface(Typeface.DEFAULT_BOLD);
        }
        return vista;
    }

    private Button botao(String rotulo) {
        Button vista = new Button(this);
        vista.setText(rotulo);
        vista.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18f);
        vista.setAllCaps(false);
        return vista;
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

    private int dp(int valor) {
        return Math.round(valor * getResources().getDisplayMetrics().density);
    }

    // --------------------------------------------------------------- estados

    private void atualizar() {
        if (isFinishing()) {
            return;
        }
        Instalador.Progresso progresso = Instalador.progresso(this);
        String kodi = Kodi.versaoInstalada(this);

        if (Kodi.instalado(this) && !Kodi.desatualizado(this)) {
            titulo.setText("SMARTEDTV instalado");
            status.setText("O aplicativo principal ja esta no aparelho.");
            detalhe.setText("Versao " + kodi + "  •  anuncios prontos");
            barra.setVisibility(View.GONE);
            mostrar(principal, "Abrir SMARTEDTV", true);
            mostrar(secundario, "Baixar de novo", true);
            return;
        }

        if (progresso.rodando()) {
            titulo.setText("Baixando o SMARTEDTV");
            int porcento = progresso.porcento();
            barra.setVisibility(View.VISIBLE);
            barra.setIndeterminate(porcento < 0);
            if (porcento >= 0) {
                barra.setProgress(porcento);
            }
            status.setText(porcento < 0
                    ? "Iniciando o download..."
                    : "Baixando... " + porcento + "%");
            detalhe.setText(progresso.megabytes()
                    + "\nO download continua mesmo se voce sair desta tela.");
            mostrar(principal, "Baixando...", false);
            mostrar(secundario, "Continuar em segundo plano", true);
            return;
        }

        if (progresso.falhou()) {
            titulo.setText("O download falhou");
            status.setText("Nao consegui baixar o SMARTEDTV.");
            detalhe.setText(progresso.detalhe + "\nVerifique a internet e tente de novo.");
            barra.setVisibility(View.GONE);
            mostrar(principal, "Tentar de novo", true);
            mostrar(secundario, Kodi.instalado(this) ? "Abrir SMARTEDTV" : "Verificar de novo", true);
            return;
        }

        if (Instalador.jaBaixado(this)) {
            titulo.setText("Download concluido");
            status.setText("Toque em INSTALAR e confirme na tela do Android.");
            detalhe.setText(Instalador.mb(Instalador.arquivo(this).length())
                    + "  •  " + (Kodi.instalado(this) ? "atualizando " + kodi : "instalacao nova"));
            barra.setVisibility(View.GONE);
            barra.setProgress(100);
            mostrar(principal, "Instalar agora", true);
            mostrar(secundario, "Baixar de novo", true);
            if (!instalacaoDisparada) {
                instalacaoDisparada = true;
                log("download pronto: abrindo o instalador");
                Instalador.instalar(this);
            }
            return;
        }

        // nada baixado ainda
        instalacaoDisparada = false;
        titulo.setText("Bem-vindo ao SMARTEDTV");
        status.setText("O aplicativo principal ainda nao esta no aparelho.");
        detalhe.setText("O download do aplicativo (cerca de 242 MB) e automatico:\n"
                + "ao terminar, a tela de instalacao do Android aparece para voce confirmar."
                + (Instalador.podeInstalar(this)
                        ? ""
                        : "\nDepois autorize 'instalar apps desconhecidos' para este app."));
        barra.setVisibility(View.GONE);
        mostrar(principal, "Baixar e instalar", true);
        mostrar(secundario, "Ja tenho o SMARTEDTV instalado", true);
    }

    private void mostrar(Button vista, String rotulo, boolean habilitado) {
        vista.setText(rotulo);
        vista.setEnabled(habilitado);
        vista.setAlpha(habilitado ? 1f : 0.5f);
    }

    private void aoTocarPrincipal() {
        Instalador.Progresso progresso = Instalador.progresso(this);
        if (Kodi.instalado(this) && !Kodi.desatualizado(this) && !progresso.rodando()) {
            abrirKodi();
            return;
        }
        if (Instalador.jaBaixado(this)) {
            Instalador.instalar(this);
            return;
        }
        if (progresso.falhou()) {
            // tentar de novo precisa de um pedido novo
            Instalador.apagarArquivo(this);
        }
        iniciarDownload(false);
    }

    private void iniciarDownload(boolean automatico) {
        long id = Instalador.baixar(this);
        if (id <= 0L) {
            log("nao consegui enfileirar o download");
            Toast.makeText(this, "SMARTEDTV: nao consegui iniciar o download", Toast.LENGTH_LONG).show();
            status.setText("Nao consegui iniciar o download.");
            detalhe.setText("Confira a internet do aparelho e tente de novo.");
            return;
        }
        if (automatico) {
            log("download automatico iniciado id=" + id);
        }
        atualizar();
    }

    private void abrirKodi() {
        if (Kodi.abrir(this)) {
            finish();
            return;
        }
        Toast.makeText(this, "SMARTEDTV: nao consegui abrir o aplicativo", Toast.LENGTH_LONG).show();
        try {
            // plano B: a tela de regulagem de apps do sistema
            startActivity(new android.content.Intent(
                    android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    android.net.Uri.parse("package:" + Kodi.PACOTE)));
        } catch (ActivityNotFoundException ignorado) {
            Log.w(Ads.TAG, "BoasVindas: sem tela de detalhes do app");
        }
    }

    private void log(String mensagem) {
        Log.i(Ads.TAG, "BoasVindas: " + mensagem);
    }
}
