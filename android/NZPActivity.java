package org.libsdl.app;

import android.content.pm.ActivityInfo;
import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * Android launcher for the native NZ:P/Vril build.
 *
 * The complete official NZ:P data archive is bundled inside the APK by CI.
 * Before SDL_main starts, it is expanded into private app storage and Vril is
 * launched with that folder as -basedir. Nothing is streamed from the web at
 * runtime.
 */
public class NZPActivity extends SDLActivity {
    private static final String DATA_ARCHIVE = "nzp-data.zip";
    private static final String DATA_VERSION = "nzp-data.version";

    /**
     * Keep SDL/Vril locked to sensor-landscape. Without this override SDL2
     * treats the resizable desktop-style window as FULL_USER and Android can
     * rotate/recreate the Surface after the GLES context has been created.
     */
    @Override
    public void setOrientationBis(int w, int h, boolean resizable, String hint) {
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
    }

    @Override
    protected String[] getLibraries() {
        return new String[] {
            "SDL2",
            "SDL2_mixer",
            "main"
        };
    }

    @Override
    protected String[] getArguments() {
        File dataRoot = new File(getFilesDir(), "nzp-runtime");

        try {
            ensureBundledGameData(dataRoot);
        } catch (IOException e) {
            throw new RuntimeException("Unable to prepare bundled NZ:P game data", e);
        }

        return new String[] {
            "-basedir", dataRoot.getAbsolutePath()
        };
    }

    private void ensureBundledGameData(File dataRoot) throws IOException {
        String expectedVersion = readAssetText(DATA_VERSION).trim();
        File marker = new File(dataRoot, ".xziel-data-version");

        if (marker.isFile() && expectedVersion.equals(readFileText(marker).trim())) {
            return;
        }

        deleteTree(dataRoot);
        if (!dataRoot.mkdirs() && !dataRoot.isDirectory()) {
            throw new IOException("Could not create " + dataRoot);
        }

        String canonicalRoot = dataRoot.getCanonicalPath() + File.separator;

        try (InputStream raw = getAssets().open(DATA_ARCHIVE);
             ZipInputStream zip = new ZipInputStream(new BufferedInputStream(raw))) {

            ZipEntry entry;
            byte[] buffer = new byte[64 * 1024];

            while ((entry = zip.getNextEntry()) != null) {
                File out = new File(dataRoot, entry.getName());
                String canonicalOut = out.getCanonicalPath();

                if (!canonicalOut.equals(dataRoot.getCanonicalPath())
                        && !canonicalOut.startsWith(canonicalRoot)) {
                    throw new IOException("Blocked invalid archive path: " + entry.getName());
                }

                if (entry.isDirectory()) {
                    if (!out.mkdirs() && !out.isDirectory()) {
                        throw new IOException("Could not create directory " + out);
                    }
                } else {
                    File parent = out.getParentFile();
                    if (parent != null && !parent.mkdirs() && !parent.isDirectory()) {
                        throw new IOException("Could not create directory " + parent);
                    }

                    try (BufferedOutputStream output =
                                 new BufferedOutputStream(new FileOutputStream(out))) {
                        int count;
                        while ((count = zip.read(buffer)) != -1) {
                            output.write(buffer, 0, count);
                        }
                    }
                }

                zip.closeEntry();
            }
        }

        try (FileOutputStream output = new FileOutputStream(marker)) {
            output.write(expectedVersion.getBytes(StandardCharsets.UTF_8));
        }
    }

    private String readAssetText(String name) throws IOException {
        try (InputStream input = getAssets().open(name);
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096];
            int count;
            while ((count = input.read(buffer)) != -1) {
                output.write(buffer, 0, count);
            }
            return output.toString("UTF-8");
        }
    }

    private String readFileText(File file) throws IOException {
        try (FileInputStream input = new FileInputStream(file);
             ByteArrayOutputStream output = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096];
            int count;
            while ((count = input.read(buffer)) != -1) {
                output.write(buffer, 0, count);
            }
            return output.toString("UTF-8");
        }
    }

    private void deleteTree(File file) throws IOException {
        if (!file.exists()) {
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
            throw new IOException("Could not delete old runtime path " + file);
        }
    }
}
