package org.smartedtv.bootstrap;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.res.ColorStateList;
import android.graphics.Color;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.View;
import android.widget.ProgressBar;
import android.widget.TextView;

import java.io.File;
import java.lang.ref.WeakReference;
import java.lang.reflect.Method;

/** Asynchronous pre-Kodi bootstrap. Must be validated in an isolated emulator. */
public final class ProfileDirectoryBootstrap {
    private static final String TAG = "SMARTED-TV";
    // State is read and modified exclusively on the Android main thread.
    private static WeakReference<Activity> current = new WeakReference<Activity>(null);
    private static boolean working;
    private static long workingSince;
    private static Boolean result;

    private ProfileDirectoryBootstrap() { }

    /** Called on the main thread by the patched Splash.startXBMC(). */
    public static void start(Activity activity) {
        showProgress(activity);
        current = new WeakReference<Activity>(activity);
        if (result != null) {
            deliverResult();
            return;
        }
        // Uma falha anterior nao pode condenar a nova Activity para sempre.
        if (working && System.currentTimeMillis() - workingSince > 120000) {
            working = false;
        }
        if (working) return;
        working = true;
        workingSince = System.currentTimeMillis();
        final Context context = activity.getApplicationContext();
        new Thread(new Runnable() {
            @Override public void run() {
                boolean ok = false;
                try {
                    File home = dataHome(context);
                    File privateDir = context.getFilesDir();
                    File base = new File(assetHome(context), "assets/smarted");
                    File profile = new File(base, "profile");
                    File manifest = new File(base, "profile-manifest.txt");
                    boolean seeded = ProfileDirectorySeed.install(profile, manifest, home, privateDir,
                        "1447de816a44ecc11c42c2c315cf20e61c9baa037e914a13293711cf152d1ede");
                    Log.i(TAG, seeded ? "Perfil inicial preparado" : "Perfil existente preservado");
                    ok = true;
                } catch (Exception ex) {
                    // Never log paths, file contents, credentials or exception messages.
                    Log.e(TAG, "Falha ao preparar perfil inicial: " + ex.getClass().getSimpleName());
                }
                final boolean success = ok;
                new Handler(Looper.getMainLooper()).post(new Runnable() {
                    @Override public void run() {
                        working = false;
                        result = Boolean.valueOf(success);
                        deliverResult();
                    }
                });
            }
        }, "smarted-profile-seed").start();
    }

    private static void deliverResult() {
        final Activity target = current.get();
        // Keep the result for the replacement Activity if this one was recreated.
        if (target == null || target.isFinishing() || target.isDestroyed()) return;
        boolean success = result.booleanValue();
        result = null;
        if (!success) {
            showFailure(target);
            return;
        }
        try {
            Method original = target.getClass().getDeclaredMethod("startXBMCOriginal");
            original.setAccessible(true);
            original.invoke(target);
        } catch (Exception ex) {
            Log.e(TAG, "Falha ao iniciar o aplicativo: " + ex.getClass().getSimpleName());
            showFailure(target);
        }
    }

    private static File dataHome(Context context) throws Exception {
        String configured = System.getProperty("xbmc.data", "");
        if (!configured.isEmpty()) {
            File path = new File(configured);
            if (!path.isDirectory()) throw new IllegalStateException("Configured data directory unavailable");
            return path;
        }
        File external = context.getExternalFilesDir("");
        if (external != null && external.isDirectory()) return external;
        File internal = context.getDir(context.getPackageName(), Context.MODE_PRIVATE);
        if (internal != null && internal.isDirectory()) return internal;
        throw new IllegalStateException("App data directory unavailable");
    }

    private static File assetHome(Context context) {
        String configured = System.getProperty("xbmc.home", "");
        return configured.isEmpty() ? new File(context.getCacheDir(), "apk") : new File(configured);
    }

    private static void showProgress(Activity activity) {
        int progressId = activity.getResources().getIdentifier("progressBar1", "id", activity.getPackageName());
        int layoutId = activity.getResources().getIdentifier("activity_splash", "layout", activity.getPackageName());
        if (progressId == 0 || layoutId == 0) return;
        View view = activity.findViewById(progressId);
        if (view == null) {
            activity.setContentView(layoutId);
            view = activity.findViewById(progressId);
        }
        if (view instanceof ProgressBar) {
            ProgressBar bar = (ProgressBar) view;
            bar.setIndeterminate(true);
            bar.setIndeterminateTintList(ColorStateList.valueOf(Color.WHITE));
            bar.setVisibility(View.VISIBLE);
        }
        int textId = activity.getResources().getIdentifier("textView1", "id", activity.getPackageName());
        View text = activity.findViewById(textId);
        if (text instanceof TextView) ((TextView) text).setText("Preparando o SMARTED-TV...");
    }

    private static void showFailure(final Activity activity) {
        new AlertDialog.Builder(activity)
            .setTitle("SMARTED-TV")
            .setMessage("Não foi possível preparar o perfil inicial. Seus dados existentes não foram substituídos.")
            .setCancelable(false)
            .setPositiveButton("Tentar novamente", new DialogInterface.OnClickListener() {
                @Override public void onClick(DialogInterface dialog, int which) { start(activity); }
            })
            .setNegativeButton("Sair", new DialogInterface.OnClickListener() {
                @Override public void onClick(DialogInterface dialog, int which) { activity.finish(); }
            })
            .show();
    }
}
