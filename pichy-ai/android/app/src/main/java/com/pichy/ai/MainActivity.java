package com.pichy.ai;

import android.app.Activity;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private final ExecutorService io = Executors.newSingleThreadExecutor();

    private LinearLayout transcript;
    private ScrollView scroll;
    private EditText prompt;
    private EditText endpoint;
    private EditText serverToken;
    private LinearLayout settingsPanel;
    private Button chatButton;
    private Button researchButton;
    private Button codeButton;
    private Button imageButton;
    private Button mapButton;
    private Button createButton;
    private LinearLayout createMenu;
    private TextView status;

    private String sessionId;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        sessionId = getPreferences(MODE_PRIVATE).getString("sessionId", "");
        if (sessionId.isEmpty()) {
            sessionId = UUID.randomUUID().toString().replace("-", "");
            getPreferences(MODE_PRIVATE).edit().putString("sessionId", sessionId).apply();
        }
        getWindow().setStatusBarColor(Color.rgb(13, 13, 16));
        getWindow().setNavigationBarColor(Color.rgb(13, 13, 16));
        setContentView(buildUi());
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(12), dp(10), dp(12), dp(10));
        root.setBackgroundColor(Color.rgb(13, 13, 16));
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            int left = insets.getSystemWindowInsetLeft();
            int top = insets.getSystemWindowInsetTop();
            int right = insets.getSystemWindowInsetRight();
            int bottom = insets.getSystemWindowInsetBottom();
            v.setPadding(dp(12) + left, dp(10) + top, dp(12) + right, dp(10) + bottom);
            return insets;
        });

        LinearLayout header = new LinearLayout(this);
        header.setGravity(Gravity.CENTER_VERTICAL);

        TextView title = new TextView(this);
        title.setText("PICHY AI");
        title.setTextSize(24);
        title.setTextColor(Color.WHITE);
        title.setTypeface(null, 1);
        header.addView(title, new LinearLayout.LayoutParams(0, dp(48), 1));

        Button settings = makeButton("⚙");
        header.addView(settings, new LinearLayout.LayoutParams(dp(64), dp(48)));
        root.addView(header);

        status = new TextView(this);
        status.setText("LAB v0.2.3 • independent from HAYUYA");
        status.setTextColor(Color.rgb(155, 155, 170));
        status.setPadding(0, 0, 0, dp(6));
        root.addView(status);

        settingsPanel = buildSettings();
        settingsPanel.setVisibility(View.GONE);
        root.addView(settingsPanel);
        settings.setOnClickListener(v -> settingsPanel.setVisibility(
                settingsPanel.getVisibility() == View.VISIBLE ? View.GONE : View.VISIBLE));

        scroll = new ScrollView(this);
        transcript = new LinearLayout(this);
        transcript.setOrientation(LinearLayout.VERTICAL);
        transcript.setPadding(0, dp(6), 0, dp(6));
        scroll.addView(transcript);
        root.addView(scroll, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1));

        prompt = new EditText(this);
        prompt.setHint("Ask Pichy anything...");
        prompt.setHintTextColor(Color.rgb(130, 130, 145));
        prompt.setTextColor(Color.WHITE);
        prompt.setBackgroundColor(Color.rgb(28, 28, 34));
        prompt.setPadding(dp(12), dp(10), dp(12), dp(10));
        prompt.setMinLines(2);
        prompt.setMaxLines(7);
        prompt.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        root.addView(prompt);

        createMenu = new LinearLayout(this);
        createMenu.setGravity(Gravity.CENTER);
        createMenu.setVisibility(View.GONE);
        imageButton = makeButton("Image");
        mapButton = makeButton("Map Modeling");
        createMenu.addView(imageButton, weight());
        createMenu.addView(mapButton, weight());
        root.addView(createMenu);

        LinearLayout actions = new LinearLayout(this);
        actions.setGravity(Gravity.CENTER);
        chatButton = makeButton("Chat");
        researchButton = makeButton("Research");
        codeButton = makeButton("Code");
        createButton = makeButton("Create");
        actions.addView(chatButton, weight());
        actions.addView(researchButton, weight());
        actions.addView(codeButton, weight());
        actions.addView(createButton, weight());
        root.addView(actions);

        chatButton.setOnClickListener(v -> {
            createMenu.setVisibility(View.GONE);
            sendChat("general");
        });
        researchButton.setOnClickListener(v -> {
            createMenu.setVisibility(View.GONE);
            sendChat("research");
        });
        codeButton.setOnClickListener(v -> {
            createMenu.setVisibility(View.GONE);
            sendChat("coding");
        });
        createButton.setOnClickListener(v -> createMenu.setVisibility(
                createMenu.getVisibility() == View.VISIBLE ? View.GONE : View.VISIBLE));
        imageButton.setOnClickListener(v -> {
            createMenu.setVisibility(View.GONE);
            sendImage(false);
        });
        mapButton.setOnClickListener(v -> {
            createMenu.setVisibility(View.GONE);
            sendChat("map_modeling");
        });

        addBubble("Pichy", "Ready. Chat, Research and Code stay on the main bar. Tap Create for Image or Map Modeling.");
        return root;
    }

    private LinearLayout buildSettings() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(0, 0, 0, dp(8));

        endpoint = new EditText(this);
        endpoint.setHint("Server URL, e.g. https://pichy.example.com");
        endpoint.setText(getPreferences(MODE_PRIVATE).getString("endpoint", ""));
        endpoint.setTextColor(Color.WHITE);
        endpoint.setHintTextColor(Color.GRAY);
        endpoint.setSingleLine(true);

        serverToken = new EditText(this);
        serverToken.setHint("Server token (optional)");
        serverToken.setText(getPreferences(MODE_PRIVATE).getString("serverToken", ""));
        serverToken.setTextColor(Color.WHITE);
        serverToken.setHintTextColor(Color.GRAY);
        serverToken.setSingleLine(true);
        serverToken.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);

        Button save = makeButton("Save settings");
        save.setOnClickListener(v -> {
            getPreferences(MODE_PRIVATE).edit()
                    .putString("endpoint", value(endpoint))
                    .putString("serverToken", value(serverToken))
                    .apply();
            Toast.makeText(this, "Saved", Toast.LENGTH_SHORT).show();
            checkHealth();
        });

        Button newChat = makeButton("New conversation");
        newChat.setOnClickListener(v -> {
            sessionId = UUID.randomUUID().toString().replace("-", "");
            getPreferences(MODE_PRIVATE).edit().putString("sessionId", sessionId).apply();
            transcript.removeAllViews();
            addBubble("Pichy", "New conversation started.");
        });

        box.addView(endpoint);
        box.addView(serverToken);
        box.addView(save);
        box.addView(newChat);
        return box;
    }

    private void sendChat(String route) {
        String text = value(prompt);
        if (text.isEmpty()) return;
        if (value(endpoint).isEmpty()) {
            Toast.makeText(this, "Set the server URL first.", Toast.LENGTH_SHORT).show();
            settingsPanel.setVisibility(View.VISIBLE);
            return;
        }
        prompt.setText("");
        addBubble("You", text);
        setBusy(true, route);

        io.execute(() -> {
            try {
                JSONObject req = new JSONObject();
                req.put("session_id", sessionId);
                req.put("message", text);
                req.put("route", route);
                JSONObject out = postJson("/v1/chat", req);
                sessionId = out.optString("session_id", sessionId);
                String answer = out.optString("answer", "");
                runOnUiThread(() -> addBubble("Pichy • " + route, answer));
            } catch (Exception e) {
                runOnUiThread(() -> addBubble("Error", message(e)));
            } finally {
                runOnUiThread(() -> setBusy(false, ""));
            }
        });
    }

    private void sendImage(boolean newConcept) {
        String text = value(prompt);
        if (text.isEmpty()) return;
        if (value(endpoint).isEmpty()) {
            Toast.makeText(this, "Set the server URL first.", Toast.LENGTH_SHORT).show();
            settingsPanel.setVisibility(View.VISIBLE);
            return;
        }
        prompt.setText("");
        addBubble("You • Image", text);
        setBusy(true, "image");

        io.execute(() -> {
            try {
                JSONObject req = new JSONObject();
                req.put("session_id", sessionId);
                req.put("prompt", text);
                req.put("new_concept", newConcept);
                req.put("size", "1024x1024");
                JSONObject out = postJson("/v1/image", req);
                sessionId = out.optString("session_id", sessionId);
                String effective = out.optString("effective_prompt", text);
                Bitmap bitmap = null;

                String b64 = out.optString("b64_json", "");
                String url = out.optString("url", "");
                if (!b64.isEmpty()) {
                    byte[] data = android.util.Base64.decode(b64, android.util.Base64.DEFAULT);
                    bitmap = BitmapFactory.decodeStream(new ByteArrayInputStream(data));
                } else if (!url.isEmpty()) {
                    bitmap = downloadBitmap(url);
                }

                Bitmap finalBitmap = bitmap;
                runOnUiThread(() -> {
                    addBubble("Pichy • Image", "Iteration ready. I kept the prior image instructions unless you started a new concept.\n\n" + effective);
                    if (finalBitmap != null) addImage(finalBitmap);
                });
            } catch (Exception e) {
                runOnUiThread(() -> addBubble("Error", message(e)));
            } finally {
                runOnUiThread(() -> setBusy(false, ""));
            }
        });
    }

    private void checkHealth() {
        String base = value(endpoint);
        if (base.isEmpty()) return;
        io.execute(() -> {
            try {
                HttpURLConnection c = open("/health", "GET");
                String body = read(c);
                int responseCode = c.getResponseCode();
                if (responseCode >= 200 && responseCode < 300) {
                    JSONObject out = new JSONObject(body);
                    runOnUiThread(() -> status.setText("Connected • Pichy " + out.optString("version", "?")));
                } else {
                    runOnUiThread(() -> status.setText("Server error " + responseCode));
                }
            } catch (Exception e) {
                runOnUiThread(() -> status.setText("Offline • " + message(e)));
            }
        });
    }

    private JSONObject postJson(String path, JSONObject body) throws Exception {
        HttpURLConnection c = open(path, "POST");
        c.setRequestProperty("Content-Type", "application/json");
        c.setDoOutput(true);
        try (OutputStream os = c.getOutputStream()) {
            os.write(body.toString().getBytes(StandardCharsets.UTF_8));
        }
        String text = read(c);
        if (c.getResponseCode() < 200 || c.getResponseCode() >= 300) {
            throw new IllegalStateException("HTTP " + c.getResponseCode() + ": " + text);
        }
        return new JSONObject(text);
    }

    private HttpURLConnection open(String path, String method) throws Exception {
        String base = value(endpoint);
        while (base.endsWith("/")) base = base.substring(0, base.length() - 1);
        HttpURLConnection c = (HttpURLConnection) new URL(base + path).openConnection();
        c.setRequestMethod(method);
        c.setConnectTimeout(20000);
        c.setReadTimeout(300000);
        String token = value(serverToken);
        if (!token.isEmpty()) c.setRequestProperty("X-Pichy-Token", token);
        return c;
    }

    private String read(HttpURLConnection c) throws Exception {
        InputStream stream = c.getResponseCode() >= 400 ? c.getErrorStream() : c.getInputStream();
        if (stream == null) return "";
        try (BufferedReader br = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = br.readLine()) != null) sb.append(line).append('\n');
            return sb.toString();
        }
    }

    private Bitmap downloadBitmap(String url) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(20000);
        c.setReadTimeout(180000);
        try (InputStream in = c.getInputStream()) {
            return BitmapFactory.decodeStream(in);
        }
    }

    private void addBubble(String who, String text) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(12), dp(10), dp(12), dp(10));
        card.setBackgroundColor(who.startsWith("You") ? Color.rgb(47, 35, 65) : Color.rgb(28, 28, 34));

        TextView head = new TextView(this);
        head.setText(who);
        head.setTextColor(who.startsWith("You") ? Color.rgb(225, 188, 255) : Color.rgb(180, 220, 255));
        head.setTypeface(null, 1);
        card.addView(head);

        TextView body = new TextView(this);
        body.setText(text);
        body.setTextSize(16);
        body.setTextColor(Color.WHITE);
        body.setTextIsSelectable(true);
        card.addView(body);

        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        p.setMargins(0, dp(4), 0, dp(4));
        transcript.addView(card, p);
        scroll.post(() -> scroll.fullScroll(View.FOCUS_DOWN));
    }

    private void addImage(Bitmap bitmap) {
        ImageView iv = new ImageView(this);
        iv.setAdjustViewBounds(true);
        iv.setImageBitmap(bitmap);
        iv.setPadding(0, dp(6), 0, dp(12));
        transcript.addView(iv, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT));
        scroll.post(() -> scroll.fullScroll(View.FOCUS_DOWN));
    }

    private Button makeButton(String text) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        return b;
    }

    private LinearLayout.LayoutParams weight() {
        return new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1);
    }

    private String value(EditText e) {
        return e.getText().toString().trim();
    }

    private void setBusy(boolean busy, String mode) {
        prompt.setEnabled(!busy);
        chatButton.setEnabled(!busy);
        researchButton.setEnabled(!busy);
        codeButton.setEnabled(!busy);
        imageButton.setEnabled(!busy);
        mapButton.setEnabled(!busy);
        createButton.setEnabled(!busy);
        if (busy) createMenu.setVisibility(View.GONE);
        status.setText(busy ? "Working • " + mode : "Ready • session " + sessionId.substring(0, 8));
    }

    private String message(Exception e) {
        String m = e.getMessage();
        return m == null ? e.getClass().getSimpleName() : m;
    }

    private int dp(int v) {
        return (int) (v * getResources().getDisplayMetrics().density);
    }

    @Override
    protected void onDestroy() {
        io.shutdownNow();
        super.onDestroy();
    }
}
