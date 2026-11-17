package org.smartedtv.bootstrap;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.RandomAccessFile;
import java.nio.channels.FileLock;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;

/** Installs manifest-verified bundled profile files only when no profile exists. */
public final class ProfileDirectorySeed {
    private static final long LIMIT = 256L * 1024 * 1024;
    private static final int MAX_FILES = 10000;
    private ProfileDirectorySeed() { }

    public static boolean install(File source, File manifest, File home, File privateDir, String expectedManifest) throws IOException {
        if (!home.isDirectory() || !privateDir.isDirectory()) throw new IOException("Missing directories");
        File target = new File(home, ".kodi");
        File lockFile = new File(privateDir, "smarted-seed.lock");
        try (RandomAccessFile lock = new RandomAccessFile(lockFile, "rw"); FileLock ignored = lock.getChannel().lock()) {
            sweepStaleStages(home);
            // Do not alter an existing profile, even an empty or interrupted one.
            if (target.exists()) return false;
            if (!source.isDirectory() || !manifest.isFile() || manifest.length() > 2 * 1024 * 1024 ||
                    !hash(manifest).equals(expectedManifest)) throw new IOException("Invalid profile manifest");
            File stage = new File(home, ".smarted-seed-" + UUID.randomUUID().toString());
            if (!stage.mkdir()) throw new IOException("Cannot create staging directory");
            try {
                copyVerified(source, manifest, stage);
                ProfileSeed.setDefaultSkin(new File(stage, "userdata/guisettings.xml"));
                if (!hash(manifest).equals(expectedManifest)) throw new IOException("Manifest changed");
                if (target.exists()) return false;
                // Reserve the name without overwriting an existing profile.
                if (!target.mkdir()) {
                    if (target.exists()) return false;
                    throw new IOException("Cannot reserve target");
                }
                if (!stage.renameTo(target)) {
                    target.delete(); // succeeds only for an empty directory we just created
                    throw new IOException("Cannot publish profile");
                }
                return true;
            } finally { removeOwned(stage); }
        }
    }

    private static void copyVerified(File source, File manifest, File stage) throws IOException {
        String srcRoot = source.getCanonicalPath() + File.separator;
        String dstRoot = stage.getCanonicalPath() + File.separator;
        long total = 0; int count = 0;
        Set<String> seen = new HashSet<String>();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(new FileInputStream(manifest), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                String[] fields = line.split("\\t", -1);
                if (fields.length != 3 || !fields[0].matches("[0-9a-f]{64}") || !fields[1].matches("[0-9]{1,12}")) throw new IOException("Invalid manifest row");
                String path = fields[2];
                if (path.isEmpty() || path.startsWith("/") || path.indexOf('\\') >= 0 || path.indexOf('\0') >= 0) throw new IOException("Invalid profile path");
                for (String part : path.split("/", -1)) if (part.isEmpty() || part.equals(".") || part.equals("..")) throw new IOException("Invalid profile path");
                if (!seen.add(path.toLowerCase(Locale.ROOT)) || ++count > MAX_FILES) throw new IOException("Duplicate profile file");
                long length;
                try { length = Long.parseLong(fields[1]); } catch (NumberFormatException e) { throw new IOException("Invalid size", e); }
                if (length > LIMIT || total > LIMIT - length) throw new IOException("Profile too large");
                total += length;
                File in = new File(source, path), out = new File(stage, path);
                if (!in.getCanonicalPath().startsWith(srcRoot) || !out.getCanonicalPath().startsWith(dstRoot) || !in.isFile() || in.length() != length) throw new IOException("Profile file missing");
                File parent = out.getParentFile();
                if (!parent.isDirectory() && !parent.mkdirs()) throw new IOException("Cannot create directory");
                if (!out.createNewFile()) throw new IOException("Duplicate output");
                MessageDigest digest = sha(); long copied = 0;
                try (FileInputStream input = new FileInputStream(in); FileOutputStream output = new FileOutputStream(out)) {
                    byte[] buffer = new byte[65536]; int n;
                    while ((n = input.read(buffer)) != -1) {
                        copied += n;
                        if (copied > length) throw new IOException("Profile changed");
                        digest.update(buffer, 0, n); output.write(buffer, 0, n);
                    }
                }
                if (copied != length || !hex(digest.digest()).equals(fields[0])) throw new IOException("Profile integrity error");
            }
        }
        if (count == 0) throw new IOException("Empty profile");
    }

    private static MessageDigest sha() throws IOException {
        try { return MessageDigest.getInstance("SHA-256"); }
        catch (NoSuchAlgorithmException e) { throw new IOException(e); }
    }
    private static String hex(byte[] bytes) {
        StringBuilder result = new StringBuilder();
        for (byte b : bytes) result.append(String.format(Locale.ROOT, "%02x", b & 0xff));
        return result.toString();
    }
    private static String hash(File file) throws IOException {
        MessageDigest md = sha();
        try (FileInputStream input = new FileInputStream(file)) {
            byte[] b = new byte[65536]; int n;
            while ((n = input.read(b)) != -1) md.update(b, 0, n);
        }
        return hex(md.digest());
    }
    /**
     * Remove restos de um seed interrompido sem tocar em .kodi nem em addon_data.
     * O limite de 10 minutos evita apagar o estagio de uma execucao viva.
     */
    private static void sweepStaleStages(File home) {
        File[] children = home.listFiles();
        if (children == null) return;
        long limit = System.currentTimeMillis() - 10L * 60 * 1000;
        for (File child : children) {
            String name = child.getName();
            if (!name.startsWith(".smarted-seed-") || !child.isDirectory()) continue;
            if (child.lastModified() > limit) continue;
            try { removeOwned(child); } catch (IOException ignored) { }
        }
    }

    private static void removeOwned(File path) throws IOException {
        if (!path.exists()) return;
        if (path.isDirectory()) {
            File[] children = path.listFiles();
            if (children == null) throw new IOException("Cannot clean staging directory");
            for (File child : children) removeOwned(child);
        }
        if (!path.delete()) throw new IOException("Cannot clean staging file");
    }
}
