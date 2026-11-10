package org.smartedtv.bootstrap;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.RandomAccessFile;
import java.nio.channels.FileLock;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Enumeration;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import java.util.zip.CRC32;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/** Offline pre-start profile seed. Must run before Kodi opens the profile.
 * The existing .kodi directory is never merged with or overwritten.
 * This class is not yet wired into the Android APK.
 */
public final class ProfileSeed {
    public static final String BACKUP_SHA256 = "e38ee0e23356948a008a895fbefd8b659f62504b72d50712ac91c7305a774cde";
    private static final long LIMIT_BYTES = 256L * 1024L * 1024L;
    private static final int LIMIT_ENTRIES = 10000;
    private static final String ROOT = "files/.kodi/";
    private static final String OLD_SKIN = "<setting id=\"lookandfeel.skin\" default=\"true\">skin.estuary</setting>";
    private static final String NEW_SKIN = "<setting id=\"lookandfeel.skin\">skin.novatv</setting>";

    private ProfileSeed() { }

    /** Return true only if a fresh profile was installed; false means existing data was kept. */
    public static boolean installFresh(File backup, File home, File privateDir) throws IOException {
        return installFreshChecked(backup, home, privateDir, BACKUP_SHA256);
    }

    // Test hook: production callers use the pinned digest via installFresh.
    static boolean installFreshChecked(File backup, File home, File privateDir, String expected) throws IOException {
        if (!home.isDirectory() || !privateDir.isDirectory()) throw new IOException("Missing home or private directory");
        File target = new File(home, ".kodi");
        File marker = new File(privateDir, "smarted-seed-reserved.flag");
        File lockFile = new File(privateDir, "smarted-seed.lock");
        try (RandomAccessFile lock = new RandomAccessFile(lockFile, "rw"); FileLock ignored = lock.getChannel().lock()) {
            // Only remove an empty directory that our interrupted reservation created.
            // File.delete() refuses nonempty directories, so data is never deleted here.
            if (marker.exists()) {
                if (target.isDirectory()) {
                    String[] contents = target.list();
                    if (contents != null && contents.length == 0 && !target.delete())
                        throw new IOException("Unable to recover interrupted empty reservation");
                }
                if (!marker.delete()) throw new IOException("Unable to clear reservation marker");
            }
            if (target.exists()) return false;
            if (!hash(backup).equalsIgnoreCase(expected)) throw new IOException("Backup SHA-256 mismatch");
            File stage = new File(home, ".smarted-seed-" + UUID.randomUUID().toString());
            if (!stage.mkdir()) throw new IOException("Unable to create private staging directory");
            try {
                extractVerified(backup, stage);
                setDefaultSkin(new File(stage, "userdata/guisettings.xml"));
                // Detect source changes while reading; commit only complete, verified content.
                if (!hash(backup).equalsIgnoreCase(expected)) throw new IOException("Backup changed during extraction");
                if (target.exists()) return false;
                if (!marker.createNewFile()) throw new IOException("Reservation marker already exists");
                if (!target.mkdir()) {
                    marker.delete();
                    if (target.exists()) return false;
                    throw new IOException("Unable to reserve profile directory");
                }
                if (!stage.renameTo(target)) {
                    target.delete(); // removes only an empty reserved directory
                    marker.delete();
                    throw new IOException("Unable to publish staged profile");
                }
                if (!marker.delete()) throw new IOException("Profile installed but reservation marker remains");
                return true;
            } finally {
                removeOwned(stage);
            }
        }
    }

    private static void extractVerified(File backup, File stage) throws IOException {
        try (ZipFile zip = new ZipFile(backup)) {
            if (zip.size() > LIMIT_ENTRIES) throw new IOException("Too many backup entries");
            Set<String> files = new HashSet<String>();
            Set<String> dirs = new HashSet<String>();
            Enumeration<? extends ZipEntry> entries = zip.entries();
            long announced = 0;
            while (entries.hasMoreElements()) {
                ZipEntry e = entries.nextElement();
                String relative = relativeName(e);
                if (e.getSize() < 0 || e.getSize() > LIMIT_BYTES || announced > LIMIT_BYTES - e.getSize())
                    throw new IOException("Backup exceeds size limit");
                announced += e.getSize();
                String key = relative.toLowerCase(Locale.ROOT);
                if (relative.isEmpty()) continue;
                if (e.isDirectory()) {
                    if (files.contains(key) || !dirs.add(key)) throw new IOException("Duplicate or conflicting directory");
                } else {
                    if (dirs.contains(key) || !files.add(key)) throw new IOException("Duplicate or conflicting file");
                }
            }
            for (String file : files) {
                int pos = file.lastIndexOf('/');
                while (pos >= 0) {
                    if (files.contains(file.substring(0, pos))) throw new IOException("File used as directory");
                    pos = file.lastIndexOf('/', pos - 1);
                }
            }
            entries = zip.entries();
            long total = 0;
            String prefix = stage.getCanonicalPath() + File.separator;
            byte[] buffer = new byte[65536];
            while (entries.hasMoreElements()) {
                ZipEntry e = entries.nextElement();
                String relative = relativeName(e);
                if (relative.isEmpty()) continue;
                File output = new File(stage, relative);
                if (!output.getCanonicalPath().startsWith(prefix)) throw new IOException("Unsafe archive path");
                if (e.isDirectory()) {
                    if (!output.isDirectory() && !output.mkdirs()) throw new IOException("Cannot create directory");
                    continue;
                }
                File parent = output.getParentFile();
                if (!parent.isDirectory() && !parent.mkdirs()) throw new IOException("Cannot create parent directory");
                if (!output.createNewFile()) throw new IOException("Output file already exists");
                long written = 0;
                CRC32 crc = new CRC32();
                try (InputStream in = zip.getInputStream(e); FileOutputStream out = new FileOutputStream(output)) {
                    int count;
                    while ((count = in.read(buffer)) != -1) {
                        written += count;
                        total += count;
                        if (written > e.getSize() || total > LIMIT_BYTES) throw new IOException("Backup exceeds size limit");
                        crc.update(buffer, 0, count);
                        out.write(buffer, 0, count);
                    }
                }
                if (written != e.getSize() || crc.getValue() != e.getCrc()) throw new IOException("Backup entry failed integrity check");
            }
        }
    }

    private static String relativeName(ZipEntry entry) throws IOException {
        String name = entry.getName();
        if (name == null || name.isEmpty() || name.startsWith("/") || name.indexOf('\\') >= 0 || name.indexOf('\0') >= 0)
            throw new IOException("Unsafe archive path");
        if (name.equals("files/") || name.equals("files/.kodi/")) {
            if (!entry.isDirectory()) throw new IOException("Expected root directory");
            return "";
        }
        if (!name.startsWith(ROOT)) throw new IOException("Unexpected archive root");
        String relative = name.substring(ROOT.length());
        if (relative.endsWith("/")) relative = relative.substring(0, relative.length() - 1);
        if (relative.isEmpty()) throw new IOException("Empty archive path");
        for (String part : relative.split("/", -1))
            if (part.isEmpty() || part.equals(".") || part.equals("..")) throw new IOException("Unsafe archive path");
        return relative;
    }

    private static void setDefaultSkin(File settings) throws IOException {
        if (!settings.isFile() || settings.length() > 5L * 1024L * 1024L) throw new IOException("Profile settings missing or too large");
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (FileInputStream in = new FileInputStream(settings)) {
            byte[] buffer = new byte[8192]; int count;
            while ((count = in.read(buffer)) != -1) bytes.write(buffer, 0, count);
        }
        String xml = new String(bytes.toByteArray(), StandardCharsets.UTF_8);
        int at = xml.indexOf(OLD_SKIN);
        if (at < 0 || xml.indexOf(OLD_SKIN, at + 1) >= 0) throw new IOException("Unexpected skin setting in profile");
        String updated = xml.substring(0, at) + NEW_SKIN + xml.substring(at + OLD_SKIN.length());
        try (FileOutputStream out = new FileOutputStream(settings)) {
            out.write(updated.getBytes(StandardCharsets.UTF_8));
            out.getFD().sync();
        }
    }

    private static String hash(File source) throws IOException {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            try (FileInputStream in = new FileInputStream(source)) {
                byte[] buffer = new byte[65536]; int count;
                while ((count = in.read(buffer)) != -1) md.update(buffer, 0, count);
            }
            StringBuilder s = new StringBuilder();
            for (byte b : md.digest()) s.append(String.format(Locale.ROOT, "%02x", b & 0xff));
            return s.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IOException("SHA-256 unavailable", e);
        }
    }

    private static void removeOwned(File root) throws IOException {
        if (!root.exists()) return;
        if (root.isDirectory()) {
            File[] children = root.listFiles();
            if (children == null) throw new IOException("Cannot list staging directory");
            for (File child : children) removeOwned(child);
        }
        if (!root.delete()) throw new IOException("Cannot remove staging file");
    }
}
