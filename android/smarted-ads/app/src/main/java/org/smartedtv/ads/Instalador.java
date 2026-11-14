package org.smartedtv.ads;

import android.app.Activity;
import android.app.DownloadManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.database.Cursor;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.Settings;
import android.util.Log;
import android.widget.Toast;

import androidx.core.content.FileProvider;

import java.io.File;
import java.util.Locale;

/**
 * Download e instalacao do APK PRINCIPAL (SMARTED-TV / Kodi).
 *
 * Regras que este arquivo garante:
 *  - o download e feito pelo DownloadManager do sistema: continua mesmo se o
 *    usuario sair da tela, aguenta redirecionamento (GitHub -> CDN) e nao
 *    carrega 242 MB na memoria do app;
 *  - o arquivo fica em getExternalFilesDir(Download) — pasta DO APP, sem
 *    precisar de permissao de armazenamento em nenhuma versao do Android;
 *  - a instalacao vai por FileProvider (content://), nunca por file:// — o
 *    Android 7+ recusa file:// (FileUriExposedException);
 *  - em Android 8+ o sistema exige que o usuario libere "instalar apps
 *    desconhecidos" para este app; a tela leva direto para a regulagem.
 */
public final class Instalador {

    /**
     * Enderecos do APK principal, em ordem de tentativa (BuildConfig vem de
     * android/smarted-ads/apk-url.txt). O primeiro e o URL_APK.
     *
     * Por que uma lista: link de release de repositorio PRIVADO responde 404
     * para quem nao esta autenticado (o app na TV nunca esta), e hospedagem
     * gratuita muda de endereco. Com varios links o app tenta o proximo em vez
     * de mandar o usuario instalar na mao.
     */
    public static final String[] URLS = BuildConfig.APK_URLS.split("\\|");

    /** Endereco principal (primeiro da lista). */
    public static final String URL_APK = BuildConfig.APK_URL;

    /** Pagina humana (release/site) para o botao "Abrir no navegador". */
    public static final String PAGINA = BuildConfig.APK_PAGINA;

    /** versionCode minimo aceito (o "codigo=" do apk-url.txt). */
    public static final int CODIGO_MINIMO = BuildConfig.APK_CODIGO_MINIMO;

    /** Nome do arquivo baixado (fica na pasta privada do app). */
    public static final String NOME_ARQUIVO = "SMARTED-TV.apk";

    /** Autoridade do FileProvider: <pacote>.arquivos (ver o manifesto). */
    public static final String AUTORIDADE = BuildConfig.APPLICATION_ID + ".arquivos";

    private static final String PREFERENCIAS = "instalador";
    private static final String CHAVE_ID = "download";
    private static final String CHAVE_URL = "url_indice";
    private static final String CHAVE_JA_TENTOU = "ja_tentou_baixar";
    private static final String MIME_APK = "application/vnd.android.package-archive";
    private static final long TAMANHO_MINIMO_PLAUSIVEL = 1024L * 1024L;

    private Instalador() {
    }

    /** Resultado de uma consulta ao DownloadManager. status -1 = nao ha download. */
    public static final class Progresso {
        public static final int AUSENTE = -1;

        public final int status;
        public final long baixado;
        public final long total;
        public final String detalhe;

        Progresso(int status, long baixado, long total, String detalhe) {
            this.status = status;
            this.baixado = baixado;
            this.total = total;
            this.detalhe = detalhe;
        }

        public boolean ausente() {
            return status == AUSENTE;
        }

        public boolean rodando() {
            return status == DownloadManager.STATUS_RUNNING
                    || status == DownloadManager.STATUS_PENDING
                    || status == DownloadManager.STATUS_PAUSED;
        }

        public boolean concluido() {
            return status == DownloadManager.STATUS_SUCCESSFUL;
        }

        public boolean falhou() {
            return status == DownloadManager.STATUS_FAILED;
        }

        /** 0..100, ou -1 quando o tamanho total ainda e desconhecido. */
        public int porcento() {
            if (total <= 0) {
                return -1;
            }
            return (int) Math.min(100L, Math.max(0L, (baixado * 100L) / total));
        }

        public String megabytes() {
            if (total <= 0) {
                return mb(baixado);
            }
            return mb(baixado) + " de " + mb(total);
        }
    }

    public static String mb(long bytes) {
        if (bytes <= 0) {
            return "0 MB";
        }
        return String.format(Locale.US, "%.1f MB", bytes / 1048576.0);
    }

    private static SharedPreferences prefs(Context contexto) {
        return contexto.getSharedPreferences(PREFERENCIAS, Context.MODE_PRIVATE);
    }

    /** Arquivo final do APK baixado. */
    public static File arquivo(Context contexto) {
        File pasta = contexto.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
        if (pasta == null) {
            pasta = new File(contexto.getFilesDir(), "downloads");
        }
        return new File(pasta, NOME_ARQUIVO);
    }

    /** Link que sera usado agora (indice salvo nas preferencias). */
    public static String urlAtual(Context contexto) {
        int indice = prefs(contexto).getInt(CHAVE_URL, 0);
        if (indice < 0 || indice >= URLS.length) {
            return URLS.length == 0 ? "" : URLS[0];
        }
        return URLS[indice];
    }

    /** 1-based, para mostrar "link 2 de 3". */
    public static int urlNumero(Context contexto) {
        return Math.min(URLS.length, prefs(contexto).getInt(CHAVE_URL, 0) + 1);
    }

    public static int totalDeUrls() {
        return URLS.length;
    }

    public static boolean temProximoUrl(Context contexto) {
        return prefs(contexto).getInt(CHAVE_URL, 0) + 1 < URLS.length;
    }

    /** Passa para o proximo link. Devolve false quando a lista acabou. */
    public static boolean avancarUrl(Context contexto) {
        int indice = prefs(contexto).getInt(CHAVE_URL, 0) + 1;
        if (indice >= URLS.length) {
            return false;
        }
        prefs(contexto).edit().putInt(CHAVE_URL, indice).apply();
        Log.i(Ads.TAG, "Instalador: passando para o link " + (indice + 1) + "/" + URLS.length
                + " -> " + URLS[indice]);
        return true;
    }

    /** Volta para o primeiro link (botao "Tentar de novo"). */
    public static void reiniciarUrls(Context contexto) {
        prefs(contexto).edit().putInt(CHAVE_URL, 0).apply();
    }

    public static boolean jaTentouBaixar(Context contexto) {
        return prefs(contexto).getBoolean(CHAVE_JA_TENTOU, false);
    }

    public static void marcarTentativa(Context contexto) {
        prefs(contexto).edit().putBoolean(CHAVE_JA_TENTOU, true).apply();
    }

    /**
     * Baixa o APK principal. Devolve o id do DownloadManager (0 = nao deu para
     * enfileirar). Um download igual ja em andamento e reaproveitado.
     */
    public static long baixar(Context contexto) {
        Progresso atual = progresso(contexto);
        if (atual.rodando()) {
            Log.i(Ads.TAG, "Instalador: download ja em andamento (" + atual.megabytes() + ")");
            return prefs(contexto).getLong(CHAVE_ID, 0L);
        }
        if (jaBaixado(contexto)) {
            Log.i(Ads.TAG, "Instalador: APK ja esta no aparelho, nao baixa de novo");
            return prefs(contexto).getLong(CHAVE_ID, 0L);
        }
        String url = urlAtual(contexto);
        if (url == null || !url.startsWith("http")) {
            Log.e(Ads.TAG, "Instalador: URL do APK invalida (" + url + ")");
            return 0L;
        }
        try {
            apagarArquivo(contexto);
            DownloadManager dm = (DownloadManager) contexto.getSystemService(Context.DOWNLOAD_SERVICE);
            if (dm == null) {
                Log.e(Ads.TAG, "Instalador: o sistema nao tem DownloadManager");
                return 0L;
            }
            DownloadManager.Request pedido = new DownloadManager.Request(Uri.parse(url));
            pedido.setTitle("SMARTEDTV");
            pedido.setDescription("Baixando o aplicativo principal");
            pedido.setMimeType(MIME_APK);
            pedido.setNotificationVisibility(
                    DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
            pedido.setAllowedOverMetered(true);
            pedido.setAllowedOverRoaming(true);
            pedido.setDestinationInExternalFilesDir(contexto, Environment.DIRECTORY_DOWNLOADS, NOME_ARQUIVO);
            long id = dm.enqueue(pedido);
            prefs(contexto).edit().putLong(CHAVE_ID, id).putBoolean(CHAVE_JA_TENTOU, true).apply();
            Log.i(Ads.TAG, "Instalador: download enfileirado id=" + id
                    + " link=" + urlNumero(contexto) + "/" + URLS.length + " url=" + url);
            return id;
        } catch (Throwable erro) {
            Log.e(Ads.TAG, "Instalador: nao conseguiu baixar: " + erro, erro);
            return 0L;
        }
    }

    public static Progresso progresso(Context contexto) {
        long id = prefs(contexto).getLong(CHAVE_ID, 0L);
        if (id <= 0L) {
            // pode ser que o registro do download tenha se perdido mas o APK esteja la
            File arquivo = arquivo(contexto);
            if (arquivo.isFile() && arquivo.length() > TAMANHO_MINIMO_PLAUSIVEL) {
                return new Progresso(DownloadManager.STATUS_SUCCESSFUL, arquivo.length(),
                        arquivo.length(), "arquivo ja no aparelho");
            }
            return new Progresso(Progresso.AUSENTE, 0L, 0L, "nenhum download");
        }
        DownloadManager dm = (DownloadManager) contexto.getSystemService(Context.DOWNLOAD_SERVICE);
        if (dm == null) {
            return new Progresso(Progresso.AUSENTE, 0L, 0L, "sem DownloadManager");
        }
        Cursor cursor = null;
        try {
            cursor = dm.query(new DownloadManager.Query().setFilterById(id));
            if (cursor == null || !cursor.moveToFirst()) {
                File arquivo = arquivo(contexto);
                if (arquivo.isFile() && arquivo.length() > TAMANHO_MINIMO_PLAUSIVEL) {
                    return new Progresso(DownloadManager.STATUS_SUCCESSFUL, arquivo.length(),
                            arquivo.length(), "arquivo ja no aparelho");
                }
                return new Progresso(Progresso.AUSENTE, 0L, 0L, "registro do download sumiu");
            }
            int status = lerInteiro(cursor, DownloadManager.COLUMN_STATUS, Progresso.AUSENTE);
            long baixado = lerLongo(cursor, DownloadManager.COLUMN_BYTES_DOWNLOADED_SO_FAR);
            long total = lerLongo(cursor, DownloadManager.COLUMN_TOTAL_SIZE_BYTES);
            int motivo = lerInteiro(cursor, DownloadManager.COLUMN_REASON, 0);
            return new Progresso(status, baixado, total,
                    status == DownloadManager.STATUS_FAILED ? explicar(motivo) : "");
            // COLUMN_REASON carrega o codigo HTTP (404/403/...) nesses casos
        } catch (Throwable erro) {
            Log.w(Ads.TAG, "Instalador: falha ao consultar o download: " + erro);
            return new Progresso(Progresso.AUSENTE, 0L, 0L, "consulta falhou: " + erro);
        } finally {
            if (cursor != null) {
                cursor.close();
            }
        }
    }

    private static int lerInteiro(Cursor cursor, String coluna, int padrao) {
        int indice = cursor.getColumnIndex(coluna);
        if (indice < 0 || cursor.isNull(indice)) {
            return padrao;
        }
        return cursor.getInt(indice);
    }

    private static long lerLongo(Cursor cursor, String coluna) {
        int indice = cursor.getColumnIndex(coluna);
        if (indice < 0 || cursor.isNull(indice)) {
            return -1L;
        }
        return cursor.getLong(indice);
    }

    private static String explicar(int motivo) {
        // O DownloadManager guarda o codigo HTTP cru em COLUMN_REASON quando o
        // servidor responde erro — e 404 aqui quase sempre quer dizer
        // "repositorio privado" (o GitHub esconde o anexo de quem nao logou).
        if (motivo >= 400 && motivo <= 599) {
            String dica;
            switch (motivo) {
                case 401:
                case 403:
                    dica = "acesso negado (o link exige login)";
                    break;
                case 404:
                    dica = "nao encontrado — release privada ou link antigo";
                    break;
                default:
                    dica = "o servidor recusou o download";
                    break;
            }
            return "HTTP " + motivo + " (" + dica + ")";
        }
        switch (motivo) {
            case DownloadManager.ERROR_INSUFFICIENT_SPACE:
                return "sem espaco livre no aparelho";
            case DownloadManager.ERROR_DEVICE_NOT_FOUND:
                return "cartao/armazenamento indisponivel";
            case DownloadManager.ERROR_FILE_ERROR:
                return "erro ao gravar o arquivo";
            case DownloadManager.ERROR_UNHANDLED_HTTP_CODE:
            case DownloadManager.ERROR_HTTP_DATA_ERROR:
                return "o servidor recusou o download (HTTP)";
            case DownloadManager.ERROR_CANNOT_RESUME:
                return "download interrompido e sem retomada";
            case DownloadManager.ERROR_TOO_MANY_REDIRECTS:
                return "redirecionamentos demais no link";
            default:
                return "codigo " + motivo;
        }
    }

    public static boolean jaBaixado(Context contexto) {
        Progresso progresso = progresso(contexto);
        if (progresso.concluido()) {
            File arquivo = arquivo(contexto);
            return arquivo.isFile() && arquivo.length() > TAMANHO_MINIMO_PLAUSIVEL;
        }
        return false;
    }

    public static void apagarArquivo(Context contexto) {
        try {
            File arquivo = arquivo(contexto);
            if (arquivo.isFile() && !arquivo.delete()) {
                Log.w(Ads.TAG, "Instalador: nao apagou o APK antigo");
            }
        } catch (Throwable erro) {
            Log.w(Ads.TAG, "Instalador: erro ao apagar: " + erro);
        }
    }

    /** Android 8+: este app pode instalar APK? (regulagem por app) */
    public static boolean podeInstalar(Context contexto) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return true;
        }
        try {
            return contexto.getPackageManager().canRequestPackageInstalls();
        } catch (Throwable erro) {
            Log.w(Ads.TAG, "Instalador: canRequestPackageInstalls falhou: " + erro);
            return false;
        }
    }

    /** Abre a regulagem "instalar apps desconhecidos" para este app. */
    public static void pedirPermissaoDeInstalacao(Activity tela, int codigo) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return;
        }
        try {
            Intent intent = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                    Uri.parse("package:" + tela.getPackageName()));
            tela.startActivityForResult(intent, codigo);
            Log.i(Ads.TAG, "Instalador: pedindo permissao de instalar apps");
        } catch (Throwable erro) {
            Log.e(Ads.TAG, "Instalador: sem tela de permissao: " + erro, erro);
            Toast.makeText(tela, "Autorize 'instalar apps desconhecidos' nas configuracoes",
                    Toast.LENGTH_LONG).show();
        }
    }

    /**
     * Dispara a tela de instalacao do Android (o usuario confirma; nao existe
     * instalacao silenciosa fora do Play).
     */
    public static boolean instalar(Activity tela) {
        File arquivo = arquivo(tela);
        Log.i(Ads.TAG, "Instalador: instalando " + arquivo.getAbsolutePath()
                + " (" + arquivo.length() + " bytes)");
        if (!arquivo.isFile() || arquivo.length() <= TAMANHO_MINIMO_PLAUSIVEL) {
            Log.e(Ads.TAG, "Instalador: APK ausente ou incompleto");
            Toast.makeText(tela, "SMARTEDTV: o APK ainda nao foi baixado", Toast.LENGTH_LONG).show();
            return false;
        }
        if (!podeInstalar(tela)) {
            Toast.makeText(tela, "SMARTEDTV: libere 'instalar apps desconhecidos' para este app",
                    Toast.LENGTH_LONG).show();
            pedirPermissaoDeInstalacao(tela, 4701);
            return false;
        }
        try {
            Uri uri = FileProvider.getUriForFile(tela, AUTORIDADE, arquivo);
            Intent intent = new Intent(Intent.ACTION_VIEW);
            intent.setDataAndType(uri, MIME_APK);
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            tela.startActivity(intent);
            Log.i(Ads.TAG, "Instalador: tela de instalacao aberta (" + uri + ")");
            return true;
        } catch (Throwable erro) {
            Log.e(Ads.TAG, "Instalador: falha ao abrir o instalador: " + erro, erro);
            Toast.makeText(tela, "SMARTEDTV: nao consegui abrir o instalador (" + erro + ")",
                    Toast.LENGTH_LONG).show();
            return false;
        }
    }
}
