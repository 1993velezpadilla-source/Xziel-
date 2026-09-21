package com.xziel.engineprototype;

import android.os.Build;
import android.os.Bundle;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.os.VibratorManager;
import android.content.Context;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.view.WindowManager;

import com.google.androidgamesdk.GameActivity;

public final class XzielGameActivity extends GameActivity {
    static {
        System.loadLibrary("xziel-native");
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
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

    private void enterImmersiveMode() {
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

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
