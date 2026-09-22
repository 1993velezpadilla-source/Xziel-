package com.xziel.engineprototype;

import android.os.Build;
import android.os.Bundle;
import android.os.PowerManager;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.os.VibratorManager;
import android.content.Context;
import android.content.pm.ActivityInfo;
import android.content.res.Configuration;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;
import android.view.View;

import com.google.androidgamesdk.GameActivity;

public final class XzielGameActivity extends GameActivity {
    static {
        System.loadLibrary("xziel-native");
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setRequestedOrientation(
            ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
        );
        enterImmersiveMode();
    }

    @Override
    public void onConfigurationChanged(Configuration newConfig) {
        super.onConfigurationChanged(newConfig);
        enterImmersiveMode();
    }

    @Override
    protected void onResume() {
        super.onResume();
        enterImmersiveMode();
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            enterImmersiveMode();
        }
    }

    @SuppressWarnings("deprecation")
    public int getXzielDisplayRotation() {
        if (Build.VERSION.SDK_INT >= 30) {
            if (getDisplay() == null) {
                return 0;
            }
            return getDisplay().getRotation();
        }

        return getWindowManager()
            .getDefaultDisplay()
            .getRotation();
    }

    public int getXzielThermalStatus() {
        if (Build.VERSION.SDK_INT < 29) {
            return 0;
        }

        PowerManager manager =
            (PowerManager) getSystemService(
                Context.POWER_SERVICE
            );

        return manager != null
            ? manager.getCurrentThermalStatus()
            : 0;
    }

    public boolean isXzielPowerSaveMode() {
        PowerManager manager =
            (PowerManager) getSystemService(
                Context.POWER_SERVICE
            );

        return manager != null
            && manager.isPowerSaveMode();
    }

    public float getXzielRefreshRate() {
        if (getDisplay() == null) {
            return 60.0f;
        }

        return getDisplay().getRefreshRate();
    }

    @SuppressWarnings("deprecation")
    private Vibrator getXzielVibrator() {
        if (Build.VERSION.SDK_INT >= 31) {
            VibratorManager manager =
                (VibratorManager) getSystemService(
                    Context.VIBRATOR_MANAGER_SERVICE
                );

            return manager != null
                ? manager.getDefaultVibrator()
                : null;
        }

        return (Vibrator) getSystemService(
            Context.VIBRATOR_SERVICE
        );
    }

    public boolean hasXzielVibrator() {
        Vibrator vibrator = getXzielVibrator();
        return vibrator != null && vibrator.hasVibrator();
    }

    public boolean hasXzielAmplitudeControl() {
        Vibrator vibrator = getXzielVibrator();
        return vibrator != null
            && vibrator.hasVibrator()
            && Build.VERSION.SDK_INT >= 26
            && vibrator.hasAmplitudeControl();
    }

    @SuppressWarnings("deprecation")
    public void playXzielHaptic(
        float amplitude,
        float durationMs
    ) {
        Vibrator vibrator = getXzielVibrator();

        if (vibrator == null ||
            !vibrator.hasVibrator()) {
            return;
        }

        long duration =
            Math.max(
                1L,
                Math.min(
                    120L,
                    Math.round(durationMs)
                )
            );

        if (Build.VERSION.SDK_INT >= 26) {
            int strength =
                VibrationEffect.DEFAULT_AMPLITUDE;

            if (vibrator.hasAmplitudeControl()) {
                float clamped =
                    Math.max(
                        0.0f,
                        Math.min(
                            1.0f,
                            amplitude
                        )
                    );

                strength =
                    Math.max(
                        1,
                        Math.min(
                            255,
                            Math.round(clamped * 255.0f)
                        )
                    );
            }

            vibrator.vibrate(
                VibrationEffect.createOneShot(
                    duration,
                    strength
                )
            );
        } else {
            vibrator.vibrate(duration);
        }
    }

    @SuppressWarnings("deprecation")
    private void enterImmersiveMode() {
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        // Keep a true fullscreen gameplay surface on OEM skins and foldables
        // that still honor the legacy sticky flags more reliably than insets
        // alone. The modern API below remains authoritative on Android 11+.
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                | View.SYSTEM_UI_FLAG_FULLSCREEN
                | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
        );

        if (Build.VERSION.SDK_INT >= 30) {
            getWindow().setDecorFitsSystemWindows(false);
            WindowInsetsController controller = getWindow().getInsetsController();
            if (controller != null) {
                controller.hide(
                    WindowInsets.Type.statusBars()
                        | WindowInsets.Type.navigationBars()
                );
                controller.setSystemBarsBehavior(
                    WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
                );
            }
        }
    }
}
