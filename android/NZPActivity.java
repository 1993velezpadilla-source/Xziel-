package org.libsdl.app;

import android.content.pm.ActivityInfo;
import android.view.WindowInsetsController;
import android.view.WindowInsets;
import android.os.Bundle;
import android.os.Build;
import android.view.View;
import android.view.WindowManager;
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

    private void applyImmersiveMode() {
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN);

        if (Build.VERSION.SDK_INT >= 30) {
            getWindow().setDecorFitsSystemWindows(false);
            WindowInsetsController controller = getWindow().getInsetsController();
            if (controller != null) {
                controller.hide(WindowInsets.Type.statusBars() | WindowInsets.Type.navigationBars());
                controller.setSystemBarsBehavior(
                    WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
                );
            }
        } else {
            getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                    | View.SYSTEM_UI_FLAG_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            );
        }

        WindowManager.LayoutParams attrs = getWindow().getAttributes();
        if (Build.VERSION.SDK_INT >= 28) {
            attrs.layoutInDisplayCutoutMode =
                WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
            getWindow().setAttributes(attrs);
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        applyImmersiveMode();
        getWindow().getDecorView().postDelayed(new Runnable() {
            @Override
            public void run() {
                applyImmersiveMode();
            }
        }, 350);
    }

    @Override
    protected void onResume() {
        super.onResume();
        applyImmersiveMode();
    }

    public void requestFullExitFromNative() {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                if (Build.VERSION.SDK_INT >= 21) {
                    finishAndRemoveTask();
                } else {
                    finish();
                }
            }
        });
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            applyImmersiveMode();
        }
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

        boolean hudPreview = getIntent() != null
            && getIntent().getBooleanExtra("xziel_ci_hud_preview", false);
        boolean fogPreview = getIntent() != null
            && getIntent().getBooleanExtra("xziel_ci_fog_preview", false);
        String ciMap = getIntent() != null
            ? getIntent().getStringExtra("xziel_ci_map")
            : null;
        if (ciMap == null || ciMap.isEmpty()) {
            ciMap = "ndu";
        }

        if (hudPreview && fogPreview) {
            // CI parity probe: selectable real maps let the workflow exercise
            // both exposed sky and actual water geometry in separate boots.
            return new String[] {
                "-basedir", dataRoot.getAbsolutePath(),
                "+map", ciMap,
                "+fog", "96", "768", "16", "20", "24",
                "++attack",
                "++r_shadows", "1"
            };
        }

        if (hudPreview) {
            // CI-only visual validation path. "ndu" is the bundled Nacht der
            // Untoten map; starting it directly lets the workflow capture the
            // actual gameplay HUD rather than only a menu/loading screen.
            return new String[] {
                "-basedir", dataRoot.getAbsolutePath(),
                "+map", "ndu"
            };
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
