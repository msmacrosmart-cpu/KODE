package smartedtv.full;

import android.app.Activity;
import android.app.Application;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import java.io.File;

/** Private hand-off to the EXISTING AdMob activity. No ad clicks, SDK changes or timers. */
public final class AdBreak extends Activity {
    private static ReturnListener listener;

    // Same data roots as the Kodi Splash/SeedBase. The intent carries only a nonce, never a path.
    private File pending(String token) {
        String custom = System.getProperty("xbmc.data", "");
        File[] roots = {custom.isEmpty() ? null : new File(custom), getExternalFilesDir(null),
                        getDir(getPackageName(), MODE_PRIVATE), getFilesDir()};
        for (File root : roots) {
            if (root == null) continue;
            File f = new File(root, ".kodi/temp/smarted-ad/" + token + ".pending");
            if (f.isFile()) return f;
        }
        return null;
    }

    // Back/OK no controle não podem fechar a ponte antes de o anúncio abrir:
    // isso vira um anúncio que nunca aparece e um player pausado sem retorno.
    @Override public void onBackPressed() { }

    @Override protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        if (saved != null) { if (listener == null) finish(); return; }
        Uri uri = getIntent().getData();
        String token = uri == null ? null : uri.getLastPathSegment();
        if (token == null || !token.matches("[a-f0-9]{32}")) { finish(); return; }
        File request = pending(token);
        if (request == null) { finish(); return; } // cancelled / late intent
        File open = new File(request.getParentFile(), token + ".open");
        if (!request.renameTo(open)) { finish(); return; }
        Application app = getApplication();
        if (listener != null) app.unregisterActivityLifecycleCallbacks(listener);
        listener = new ReturnListener(open, new File(open.getParentFile(), token + ".returned"));
        app.registerActivityLifecycleCallbacks(listener);
        try {
            startActivityForResult(new Intent("smartedtv.ads.PREROLL")
                    .setClassName(this, "smartedtv.full.PreRollActivity"), 1);
        } catch (RuntimeException e) {
            Log.w("SmartAds", "Pre-roll indisponível; devolvendo o player", e);
            finish();
        }
    }

    // Duas provas possíveis de fim do anúncio: (1) a PreRollActivity devolve o
    // resultado — a cadeia inteira (inclusive a activity do SDK) terminou, mesmo
    // quando a tela do anúncio não pausa a Main; (2) a Main volta a ser resumed.
    // Sem (1), um anúncio translúcido deixaria o vídeo pausado para sempre.
    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request != 1) return;
        if (listener != null) listener.marcar();
        finish();
    }

    // Sem (1) — anúncio que não pausa a Main, como um intersticial translúcido —
    // o retorno serializado ao foco abaixo libera o player.
    private static final class ReturnListener implements Application.ActivityLifecycleCallbacks {
        final File open, returned;
        ReturnListener(File open, File returned) { this.open = open; this.returned = returned; }
        @Override public void onActivityResumed(Activity a) {
            if (!"smartedtv.full.Main".equals(a.getClass().getName())) return;
            marcar();
            a.getApplication().unregisterActivityLifecycleCallbacks(this);
        }

        void marcar() {
            open.renameTo(returned);
            if (listener == this) listener = null;
        }
        public void onActivityCreated(Activity a, Bundle b) {}
        public void onActivityStarted(Activity a) {}
        public void onActivityPaused(Activity a) {}
        public void onActivityStopped(Activity a) {}
        public void onActivitySaveInstanceState(Activity a, Bundle b) {}
        public void onActivityDestroyed(Activity a) {}
    }
}
