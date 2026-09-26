package org.libsdl.app;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/**
 * Strict installer for XZIEL .xzp map packages.
 *
 * The package is verified before it is made visible to Vril:
 * - xziel.package.json must be unique and strictReady;
 * - map metadata must match the portable descriptor contract;
 * - every payload member must match manifest size + SHA-256;
 * - extra, missing, duplicate or unsafe paths are rejected;
 * - extraction occurs into a temporary private directory and is renamed only
 *   after the complete payload verifies.
 */
public final class XzielMapPackageInstaller {
    private XzielMapPackageInstaller() {}

    public static final class InstalledMap {
        public final String mapId;
        public final String entryWorld;
        public final String gameDirectoryName;
        public final File gameDirectory;

        InstalledMap(
                String mapId,
                String entryWorld,
                String gameDirectoryName,
                File gameDirectory) {
            this.mapId = mapId;
            this.entryWorld = entryWorld;
            this.gameDirectoryName = gameDirectoryName;
            this.gameDirectory = gameDirectory;
        }
    }

    private static final class ExpectedFile {
        final String path;
        final long bytes;
        final String sha256;

        ExpectedFile(String path, long bytes, String sha256) {
            this.path = path;
            this.bytes = bytes;
            this.sha256 = sha256;
        }
    }

    public static InstalledMap install(File packageFile, File dataRoot)
            throws IOException {
        if (packageFile == null || !packageFile.isFile()) {
            throw new IOException("XZIEL map package does not exist");
        }
        if (dataRoot == null || !dataRoot.isDirectory()) {
            throw new IOException("XZIEL runtime data root is unavailable");
        }

        try (ZipFile zip = new ZipFile(packageFile)) {
            ZipEntry manifestEntry = null;
            int manifestCount = 0;
            Set<String> zipNames = new HashSet<>();

            Enumeration<? extends ZipEntry> enumeration = zip.entries();
            while (enumeration.hasMoreElements()) {
                ZipEntry entry = enumeration.nextElement();
                String name = normalize(entry.getName());
                if (!zipNames.add(name)) {
                    throw new IOException("Duplicate ZIP member: " + name);
                }
                validateSafeRelativePath(name);
                if ("xziel.package.json".equals(name)) {
                    manifestEntry = entry;
                    manifestCount++;
                }
            }

            if (manifestCount != 1 || manifestEntry == null) {
                throw new IOException(
                    "XZIEL package must contain exactly one xziel.package.json");
            }

            JSONObject manifest = parseJson(readAll(zip.getInputStream(manifestEntry)));
            JSONObject summary = object(manifest, "summary");
            if (!summary.optBoolean("strictReady", false)) {
                throw new IOException("XZIEL package inventory is not strictReady");
            }

            JSONObject packageMeta = object(manifest, "package");
            requireString(packageMeta, "format", "xziel_xzp_v1");
            requireString(packageMeta, "payloadRoot", "payload/");
            if (!packageMeta.optBoolean("sourceBytesPreserved", false)) {
                throw new IOException("XZIEL package sourceBytesPreserved is false");
            }

            JSONObject mapMeta = object(manifest, "map");
            String mapId = mapMeta.optString("mapId", "");
            if (!mapId.matches("^[a-z0-9][a-z0-9_]{0,62}$")) {
                throw new IOException("Invalid XZIEL mapId");
            }
            String entryWorld = normalize(mapMeta.optString("entryWorld", ""));
            if (!entryWorld.equals("maps/" + mapId + ".bsp")) {
                throw new IOException(
                    "entryWorld must equal maps/<mapId>.bsp");
            }
            requireString(mapMeta, "gameMode", "round_based_zombies");
            requireString(
                mapMeta,
                "contentContract",
                "xziel_map_content_contract_v1");
            if (!mapMeta.optBoolean("serverAuthoritative", false)) {
                throw new IOException("Map must be server authoritative");
            }
            int maxPlayers = mapMeta.optInt("maxPlayers", 0);
            if (maxPlayers < 1 || maxPlayers > 4) {
                throw new IOException("Map maxPlayers must be 1..4");
            }

            JSONArray files = manifest.optJSONArray("files");
            if (files == null || files.length() == 0) {
                throw new IOException("XZIEL package file inventory is empty");
            }

            Map<String, ExpectedFile> expected = new HashMap<>();
            long totalExpectedBytes = 0L;
            for (int i = 0; i < files.length(); ++i) {
                JSONObject row = files.optJSONObject(i);
                if (row == null) {
                    throw new IOException("Invalid XZIEL file inventory row");
                }
                String rel = normalize(row.optString("path", ""));
                validateSafeRelativePath(rel);
                if (rel.startsWith("payload/")) {
                    throw new IOException("Inventory paths must be payload-relative");
                }

                long bytes = row.optLong("bytes", -1L);
                String digest = row.optString("sha256", "")
                    .toLowerCase(Locale.US);
                if (bytes < 0L || !digest.matches("^[0-9a-f]{64}$")) {
                    throw new IOException("Invalid file metadata for " + rel);
                }

                String archiveName = "payload/" + rel;
                if (expected.put(
                        archiveName,
                        new ExpectedFile(rel, bytes, digest)) != null) {
                    throw new IOException("Duplicate inventory path: " + rel);
                }
                totalExpectedBytes += bytes;
            }

            if (!expected.containsKey("payload/" + entryWorld)) {
                throw new IOException("entryWorld is missing from payload inventory");
            }

            long declaredTotal = summary.optLong("totalBytes", -1L);
            if (declaredTotal != totalExpectedBytes) {
                throw new IOException("XZIEL totalBytes mismatch");
            }

            Set<String> actualPayload = new HashSet<>();
            for (String name : zipNames) {
                if (!name.startsWith("payload/") || name.endsWith("/")) {
                    continue;
                }
                actualPayload.add(name);
            }
            if (!actualPayload.equals(expected.keySet())) {
                Set<String> missing = new HashSet<>(expected.keySet());
                missing.removeAll(actualPayload);
                Set<String> extra = new HashSet<>(actualPayload);
                extra.removeAll(expected.keySet());
                throw new IOException(
                    "XZIEL payload membership mismatch missing="
                    + missing + " extra=" + extra);
            }

            File importRoot = new File(dataRoot, "xziel-import");
            if (!importRoot.mkdirs() && !importRoot.isDirectory()) {
                throw new IOException("Could not create " + importRoot);
            }

            File target = new File(importRoot, mapId);
            File temp = new File(importRoot, "." + mapId + ".installing");
            deleteTree(temp);
            if (!temp.mkdirs() && !temp.isDirectory()) {
                throw new IOException("Could not create " + temp);
            }

            String canonicalTempRoot = temp.getCanonicalPath() + File.separator;
            try {
                for (Map.Entry<String, ExpectedFile> item : expected.entrySet()) {
                    String archiveName = item.getKey();
                    ExpectedFile meta = item.getValue();
                    ZipEntry payloadEntry = zip.getEntry(archiveName);
                    if (payloadEntry == null || payloadEntry.isDirectory()) {
                        throw new IOException("Missing payload member " + archiveName);
                    }

                    File out = new File(temp, meta.path);
                    String canonicalOut = out.getCanonicalPath();
                    if (!canonicalOut.startsWith(canonicalTempRoot)) {
                        throw new IOException(
                            "Blocked invalid extraction path " + meta.path);
                    }

                    File parent = out.getParentFile();
                    if (parent != null
                            && !parent.mkdirs()
                            && !parent.isDirectory()) {
                        throw new IOException("Could not create " + parent);
                    }

                    MessageDigest digest = sha256Digest();
                    long written = 0L;
                    try (InputStream input =
                             new BufferedInputStream(zip.getInputStream(payloadEntry));
                         BufferedOutputStream output =
                             new BufferedOutputStream(new FileOutputStream(out))) {
                        byte[] buffer = new byte[64 * 1024];
                        int count;
                        while ((count = input.read(buffer)) != -1) {
                            digest.update(buffer, 0, count);
                            output.write(buffer, 0, count);
                            written += count;
                        }
                    }

                    if (written != meta.bytes) {
                        throw new IOException("Size mismatch for " + meta.path);
                    }
                    String actualSha = hex(digest.digest());
                    if (!actualSha.equals(meta.sha256)) {
                        throw new IOException("SHA-256 mismatch for " + meta.path);
                    }
                }

                File installedManifest = new File(temp, ".xziel-package.json");
                try (BufferedOutputStream output =
                         new BufferedOutputStream(
                             new FileOutputStream(installedManifest))) {
                    output.write(
                        manifest.toString().getBytes(StandardCharsets.UTF_8));
                    output.write('\n');
                }

                deleteTree(target);
                if (!temp.renameTo(target)) {
                    throw new IOException(
                        "Could not atomically install XZIEL map " + mapId);
                }
            } catch (IOException error) {
                deleteTree(temp);
                throw error;
            }

            return new InstalledMap(
                mapId,
                entryWorld,
                "xziel-import/" + mapId,
                target);
        }
    }

    private static JSONObject parseJson(byte[] bytes) throws IOException {
        try {
            return new JSONObject(new String(bytes, StandardCharsets.UTF_8));
        } catch (JSONException error) {
            throw new IOException("Invalid xziel.package.json", error);
        }
    }

    private static JSONObject object(JSONObject parent, String name)
            throws IOException {
        JSONObject value = parent.optJSONObject(name);
        if (value == null) {
            throw new IOException("Missing JSON object: " + name);
        }
        return value;
    }

    private static void requireString(
            JSONObject object,
            String key,
            String expected) throws IOException {
        if (!expected.equals(object.optString(key, ""))) {
            throw new IOException("XZIEL manifest " + key + " mismatch");
        }
    }

    private static byte[] readAll(InputStream input) throws IOException {
        try (InputStream in = new BufferedInputStream(input);
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[16 * 1024];
            int count;
            while ((count = in.read(buffer)) != -1) {
                out.write(buffer, 0, count);
            }
            return out.toByteArray();
        }
    }

    private static String normalize(String path) {
        String result = path == null ? "" : path.replace('\\', '/');
        while (result.startsWith("./")) {
            result = result.substring(2);
        }
        while (result.contains("//")) {
            result = result.replace("//", "/");
        }
        return result;
    }

    private static void validateSafeRelativePath(String path)
            throws IOException {
        if (path == null
                || path.isEmpty()
                || path.startsWith("/")
                || path.contains("/../")
                || path.startsWith("../")
                || path.endsWith("/..")
                || path.indexOf('\0') >= 0) {
            throw new IOException("Unsafe XZIEL package path: " + path);
        }
    }

    private static MessageDigest sha256Digest() throws IOException {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException error) {
            throw new IOException("SHA-256 unavailable", error);
        }
    }

    private static String hex(byte[] bytes) {
        StringBuilder out = new StringBuilder(bytes.length * 2);
        for (byte value : bytes) {
            out.append(String.format(Locale.US, "%02x", value & 0xff));
        }
        return out.toString();
    }

    private static void deleteTree(File file) throws IOException {
        if (file == null || !file.exists()) {
            return;
        }
        if (file.isDirectory()) {
            File[] children = file.listFiles();
            if (children != null) {
                for (File child : children) {
                    deleteTree(child);
                }
            }
        }
        if (!file.delete()) {
            throw new IOException("Could not delete " + file);
        }
    }
}
