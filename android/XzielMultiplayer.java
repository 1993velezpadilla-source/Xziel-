package org.libsdl.app;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.pm.PackageManager;
import android.media.AudioAttributes;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioRecord;
import android.media.AudioTrack;
import android.media.MediaRecorder;
import android.media.audiofx.AcousticEchoCanceler;
import android.media.audiofx.AutomaticGainControl;
import android.media.audiofx.NoiseSuppressor;
import android.os.Build;
import android.provider.Settings;
import android.text.InputFilter;
import android.view.inputmethod.InputMethodManager;
import android.widget.EditText;
import android.widget.Toast;

import org.json.JSONObject;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

import okhttp3.ByteString;
import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;

/**
 * Xziel online-room and voice-chat client.
 *
 * Voice v1 intentionally uses small PCM16/16 kHz/mono frames over the
 * room's Cloudflare WebSocket. Four-player rooms keep this bounded while
 * avoiding codec/platform integration risk for the first device-to-device
 * test. The packet format already leaves room for an Opus transport upgrade.
 */
public final class XzielMultiplayer {
    public static final int MIC_PERMISSION_REQUEST = 7741;

    private static final int SAMPLE_RATE = 16000;
    private static final int FRAME_SAMPLES = 320; // 20 ms
    private static final int FRAME_BYTES = FRAME_SAMPLES * 2;
    private static final int HEADER_BYTES = 24;

    private static final float PROX_FULL_DISTANCE = 192.0f;
    private static final float PROX_MAX_DISTANCE = 1200.0f;

    private final Activity activity;
    private final OkHttpClient http;
    private final ConcurrentHashMap<Integer, AudioTrack> remoteTracks =
        new ConcurrentHashMap<>();

    private final AtomicBoolean micMuted = new AtomicBoolean(true);
    private final AtomicBoolean speakerMuted = new AtomicBoolean(false);
    private final AtomicBoolean proximityMode = new AtomicBoolean(false);
    private final AtomicInteger sequence = new AtomicInteger();

    private volatile String baseUrl = "";
    private volatile String roomCode = "";
    private volatile String playerId;
    private volatile int localSlot = 0;

    private volatile float localX;
    private volatile float localY;
    private volatile float localZ;

    private volatile WebSocket gameSocket;
    private volatile WebSocket voiceSocket;
    private volatile AudioRecord recorder;
    private volatile Thread captureThread;
    private volatile boolean captureRunning;

    private AcousticEchoCanceler echoCanceler;
    private NoiseSuppressor noiseSuppressor;
    private AutomaticGainControl automaticGainControl;

    public XzielMultiplayer(Activity activity, String endpoint) {
        this.activity = activity;
        this.baseUrl = normalizeBaseUrl(endpoint);
        this.playerId = loadPlayerId();
        this.http = new OkHttpClient.Builder()
            .pingInterval(java.time.Duration.ofSeconds(15))
            .build();
    }

    public void setEndpoint(String endpoint) {
        this.baseUrl = normalizeBaseUrl(endpoint);
    }

    public boolean isInRoom() {
        return !roomCode.isEmpty() && gameSocket != null;
    }

    public boolean isMicMuted() {
        return micMuted.get();
    }

    public boolean isSpeakerMuted() {
        return speakerMuted.get();
    }

    public boolean isProximityMode() {
        return proximityMode.get();
    }

    public String getRoomCode() {
        return roomCode;
    }

    public void openMultiplayerMenu() {
        activity.runOnUiThread(() -> {
            if (baseUrl.isEmpty()) {
                Toast.makeText(activity,
                    "Multiplayer backend is not configured in this APK yet.",
                    Toast.LENGTH_LONG).show();
                return;
            }

            if (isInRoom()) {
                showLobbyDialog();
                return;
            }

            new AlertDialog.Builder(activity)
                .setTitle("MULTIPLAYER")
                .setMessage("Create a private Zombies room or join with a 6-character code.")
                .setPositiveButton("CREATE ROOM", (dialog, which) -> createRoom())
                .setNegativeButton("JOIN ROOM", (dialog, which) -> showJoinDialog())
                .setNeutralButton("CANCEL", null)
                .show();
        });
    }

    private void showJoinDialog() {
        EditText input = new EditText(activity);
        input.setSingleLine(true);
        input.setHint("ROOM CODE");
        input.setAllCaps(true);
        input.setFilters(new InputFilter[] { new InputFilter.LengthFilter(6) });

        AlertDialog dialog = new AlertDialog.Builder(activity)
            .setTitle("JOIN ROOM")
            .setView(input)
            .setPositiveButton("JOIN", null)
            .setNegativeButton("BACK", null)
            .create();

        dialog.setOnShowListener(v -> {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(button -> {
                String code = input.getText().toString().trim().toUpperCase(Locale.US);
                if (!code.matches("[A-HJ-NP-Z2-9]{6}")) {
                    input.setError("Enter the 6-character room code");
                    return;
                }
                dialog.dismiss();
                joinRoom(code);
            });
            input.requestFocus();
            InputMethodManager imm = (InputMethodManager)
                activity.getSystemService(Context.INPUT_METHOD_SERVICE);
            if (imm != null) imm.showSoftInput(input, InputMethodManager.SHOW_IMPLICIT);
        });

        dialog.show();
    }

    private void createRoom() {
        Request request = new Request.Builder()
            .url(baseUrl + "/api/rooms/create")
            .post(RequestBody.create(new byte[0], null))
            .build();

        toast("Creating room...");
        http.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, java.io.IOException e) {
                toast("Could not reach multiplayer server");
            }

            @Override
            public void onResponse(Call call, Response response) {
                try (Response r = response) {
                    if (!r.isSuccessful() || r.body() == null) {
                        toast("Room creation failed (" + r.code() + ")");
                        return;
                    }
                    JSONObject body = new JSONObject(r.body().string());
                    String code = body.optString("roomCode", "");
                    if (code.length() != 6) {
                        toast("Server returned an invalid room");
                        return;
                    }
                    joinRoom(code);
                } catch (Exception e) {
                    toast("Could not read room response");
                }
            }
        });
    }

    private void joinRoom(String code) {
        leaveRoom();
        roomCode = code;
        localSlot = 0;

        String wsUrl = websocketBase() + "/game/" + code + "?playerId=" + playerId;
        Request request = new Request.Builder().url(wsUrl).build();

        toast("Joining " + code + "...");
        gameSocket = http.newWebSocket(request, new WebSocketListener() {
            @Override
            public void onOpen(WebSocket webSocket, Response response) {
                webSocket.send("{\"type\":\"hello\"}");
            }

            @Override
            public void onMessage(WebSocket webSocket, String text) {
                try {
                    JSONObject message = new JSONObject(text);
                    String type = message.optString("type", "");
                    if ("welcome".equals(type)) {
                        localSlot = message.optInt("slot", 0);
                        if (localSlot < 1 || localSlot > 4) {
                            toast("Server assigned an invalid player slot");
                            leaveRoom();
                            return;
                        }
                        connectVoice();
                        toast("Joined room " + roomCode + " as Player " + localSlot);
                        activity.runOnUiThread(() -> showLobbyDialog());
                    } else if ("player_joined".equals(type)) {
                        toast("Player " + message.optInt("slot", 0) + " joined");
                    } else if ("player_left".equals(type)) {
                        toast("Player " + message.optInt("slot", 0) + " left");
                    }
                } catch (Exception ignored) {
                }
            }

            @Override
            public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                if (!roomCode.isEmpty()) {
                    int codeValue = response != null ? response.code() : 0;
                    if (codeValue == 404) toast("Room not found");
                    else if (codeValue == 409) toast("Room is full");
                    else toast("Multiplayer connection lost");
                }
                gameSocket = null;
            }

            @Override
            public void onClosed(WebSocket webSocket, int codeValue, String reason) {
                gameSocket = null;
            }
        });
    }

    private void connectVoice() {
        if (roomCode.isEmpty() || localSlot == 0) return;

        WebSocket old = voiceSocket;
        if (old != null) old.close(1000, "reconnect");

        String wsUrl = websocketBase() + "/voice/" + roomCode + "?playerId=" + playerId;
        Request request = new Request.Builder().url(wsUrl).build();

        voiceSocket = http.newWebSocket(request, new WebSocketListener() {
            @Override
            public void onMessage(WebSocket webSocket, ByteString bytes) {
                handleVoicePacket(bytes.toByteArray());
            }

            @Override
            public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                voiceSocket = null;
                stopCapture();
            }

            @Override
            public void onClosed(WebSocket webSocket, int codeValue, String reason) {
                voiceSocket = null;
                stopCapture();
            }
        });

        if (!micMuted.get()) startCaptureIfPermitted();
    }

    public void toggleMic() {
        boolean nowMuted = !micMuted.get();
        micMuted.set(nowMuted);
        if (nowMuted) {
            stopCapture();
            toast("MIC MUTED");
        } else {
            startCaptureIfPermitted();
            toast("MIC ON");
        }
    }

    public void toggleSpeaker() {
        boolean muted = !speakerMuted.get();
        speakerMuted.set(muted);
        for (AudioTrack track : remoteTracks.values()) {
            try { track.setVolume(muted ? 0.0f : 1.0f); } catch (Exception ignored) {}
        }
        toast(muted ? "VOICE MUTED" : "VOICE AUDIO ON");
    }

    public void toggleVoiceMode() {
        boolean prox = !proximityMode.get();
        proximityMode.set(prox);
        toast(prox ? "VOICE: PROXIMITY" : "VOICE: GROUP");
    }

    public void updateLocalPosition(float x, float y, float z) {
        localX = x;
        localY = y;
        localZ = z;
    }

    public void onMicrophonePermissionResult(boolean granted) {
        if (granted && !micMuted.get()) {
            startCaptureIfPermitted();
        } else if (!granted) {
            micMuted.set(true);
            toast("Microphone permission is required for voice chat");
        }
    }

    public void leaveRoom() {
        stopCapture();

        WebSocket voice = voiceSocket;
        voiceSocket = null;
        if (voice != null) {
            try { voice.close(1000, "leave"); } catch (Exception ignored) {}
        }

        WebSocket game = gameSocket;
        gameSocket = null;
        if (game != null) {
            try { game.close(1000, "leave"); } catch (Exception ignored) {}
        }

        for (AudioTrack track : remoteTracks.values()) {
            try {
                track.pause();
                track.flush();
                track.release();
            } catch (Exception ignored) {}
        }
        remoteTracks.clear();
        roomCode = "";
        localSlot = 0;
    }

    public void shutdown() {
        leaveRoom();
        http.dispatcher().executorService().shutdown();
        http.connectionPool().evictAll();
    }

    private void showLobbyDialog() {
        if (!isInRoom()) return;

        String mic = micMuted.get() ? "MUTED" : "ON";
        String speaker = speakerMuted.get() ? "MUTED" : "ON";
        String mode = proximityMode.get() ? "PROXIMITY" : "GROUP";

        new AlertDialog.Builder(activity)
            .setTitle("ROOM " + roomCode)
            .setMessage(
                "Player " + localSlot +
                "\n\nMIC: " + mic +
                "\nVOICE AUDIO: " + speaker +
                "\nMODE: " + mode +
                "\n\nThe same voice controls remain available in-game.")
            .setPositiveButton(micMuted.get() ? "TURN MIC ON" : "MUTE MIC",
                (d, w) -> toggleMic())
            .setNegativeButton(proximityMode.get() ? "USE GROUP" : "USE PROXIMITY",
                (d, w) -> toggleVoiceMode())
            .setNeutralButton("CLOSE", null)
            .show();
    }

    private void startCaptureIfPermitted() {
        if (voiceSocket == null || micMuted.get() || captureRunning) return;

        if (Build.VERSION.SDK_INT >= 23 &&
            activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            activity.runOnUiThread(() ->
                activity.requestPermissions(
                    new String[] { Manifest.permission.RECORD_AUDIO },
                    MIC_PERMISSION_REQUEST));
            return;
        }

        int minBuffer = AudioRecord.getMinBufferSize(
            SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT);
        int bufferSize = Math.max(minBuffer, FRAME_BYTES * 8);

        AudioRecord record;
        try {
            record = new AudioRecord(
                MediaRecorder.AudioSource.VOICE_COMMUNICATION,
                SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                bufferSize);
        } catch (Exception e) {
            micMuted.set(true);
            toast("Could not open microphone");
            return;
        }

        if (record.getState() != AudioRecord.STATE_INITIALIZED) {
            record.release();
            micMuted.set(true);
            toast("Microphone initialization failed");
            return;
        }

        recorder = record;
        enableVoiceEffects(record.getAudioSessionId());
        captureRunning = true;

        record.startRecording();
        captureThread = new Thread(() -> {
            byte[] pcm = new byte[FRAME_BYTES];

            while (captureRunning && recorder == record) {
                int offset = 0;
                while (offset < pcm.length && captureRunning) {
                    int read = record.read(pcm, offset, pcm.length - offset);
                    if (read <= 0) {
                        offset = 0;
                        break;
                    }
                    offset += read;
                }

                if (offset != pcm.length || micMuted.get()) continue;

                WebSocket socket = voiceSocket;
                if (socket != null) {
                    socket.send(ByteString.of(buildVoicePacket(pcm)));
                }
            }
        }, "XzielVoiceCapture");
        captureThread.setDaemon(true);
        captureThread.start();
    }

    private byte[] buildVoicePacket(byte[] pcm) {
        ByteBuffer packet = ByteBuffer.allocate(HEADER_BYTES + pcm.length)
            .order(ByteOrder.LITTLE_ENDIAN);
        packet.put((byte)'X');
        packet.put((byte)'V');
        packet.put((byte)'C');
        packet.put((byte)'1');
        packet.put((byte)localSlot);
        packet.put((byte)(proximityMode.get() ? 1 : 0));
        packet.putShort((short)0);
        packet.putInt(sequence.incrementAndGet());
        packet.putFloat(localX);
        packet.putFloat(localY);
        packet.putFloat(localZ);
        packet.put(pcm);
        return packet.array();
    }

    private void handleVoicePacket(byte[] data) {
        if (speakerMuted.get() || data == null || data.length <= HEADER_BYTES) return;

        ByteBuffer packet = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN);
        if (packet.get() != 'X' || packet.get() != 'V' ||
            packet.get() != 'C' || packet.get() != '1') return;

        int senderSlot = packet.get() & 0xff;
        boolean senderProximity = (packet.get() & 0xff) == 1;
        packet.getShort();
        packet.getInt();
        float senderX = packet.getFloat();
        float senderY = packet.getFloat();
        float senderZ = packet.getFloat();

        if (senderSlot < 1 || senderSlot > 4 || senderSlot == localSlot) return;

        float volume = 1.0f;
        if (senderProximity) {
            float dx = senderX - localX;
            float dy = senderY - localY;
            float dz = senderZ - localZ;
            float distance = (float)Math.sqrt(dx * dx + dy * dy + dz * dz);
            volume = proximityGain(distance);
            if (volume <= 0.001f) return;
        }

        byte[] pcm = new byte[packet.remaining()];
        packet.get(pcm);

        AudioTrack track = remoteTracks.computeIfAbsent(senderSlot, this::createPlaybackTrack);
        if (track == null) return;

        try {
            track.setVolume(speakerMuted.get() ? 0.0f : volume);
            track.write(pcm, 0, pcm.length, AudioTrack.WRITE_NON_BLOCKING);
        } catch (Exception ignored) {
        }
    }

    private float proximityGain(float distance) {
        if (distance <= PROX_FULL_DISTANCE) return 1.0f;
        if (distance >= PROX_MAX_DISTANCE) return 0.0f;
        float t = (distance - PROX_FULL_DISTANCE) /
            (PROX_MAX_DISTANCE - PROX_FULL_DISTANCE);
        float smooth = 1.0f - t;
        return smooth * smooth;
    }

    private AudioTrack createPlaybackTrack(int ignoredSlot) {
        try {
            int minBuffer = AudioTrack.getMinBufferSize(
                SAMPLE_RATE,
                AudioFormat.CHANNEL_OUT_MONO,
                AudioFormat.ENCODING_PCM_16BIT);

            AudioAttributes attributes = new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_VOICE_COMMUNICATION)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                .build();

            AudioFormat format = new AudioFormat.Builder()
                .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                .setSampleRate(SAMPLE_RATE)
                .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                .build();

            AudioTrack track = new AudioTrack(
                attributes,
                format,
                Math.max(minBuffer, FRAME_BYTES * 8),
                AudioTrack.MODE_STREAM,
                AudioManager.AUDIO_SESSION_ID_GENERATE);
            track.play();
            return track;
        } catch (Exception e) {
            return null;
        }
    }

    private void stopCapture() {
        captureRunning = false;
        AudioRecord record = recorder;
        recorder = null;

        if (record != null) {
            try { record.stop(); } catch (Exception ignored) {}
            try { record.release(); } catch (Exception ignored) {}
        }

        Thread thread = captureThread;
        captureThread = null;
        if (thread != null && thread != Thread.currentThread()) {
            try { thread.join(250); } catch (InterruptedException ignored) {
                Thread.currentThread().interrupt();
            }
        }
        releaseVoiceEffects();
    }

    private void enableVoiceEffects(int audioSessionId) {
        try {
            if (AcousticEchoCanceler.isAvailable()) {
                echoCanceler = AcousticEchoCanceler.create(audioSessionId);
                if (echoCanceler != null) echoCanceler.setEnabled(true);
            }
        } catch (Exception ignored) {}

        try {
            if (NoiseSuppressor.isAvailable()) {
                noiseSuppressor = NoiseSuppressor.create(audioSessionId);
                if (noiseSuppressor != null) noiseSuppressor.setEnabled(true);
            }
        } catch (Exception ignored) {}

        try {
            if (AutomaticGainControl.isAvailable()) {
                automaticGainControl = AutomaticGainControl.create(audioSessionId);
                if (automaticGainControl != null) automaticGainControl.setEnabled(true);
            }
        } catch (Exception ignored) {}
    }

    private void releaseVoiceEffects() {
        try { if (echoCanceler != null) echoCanceler.release(); } catch (Exception ignored) {}
        try { if (noiseSuppressor != null) noiseSuppressor.release(); } catch (Exception ignored) {}
        try { if (automaticGainControl != null) automaticGainControl.release(); } catch (Exception ignored) {}
        echoCanceler = null;
        noiseSuppressor = null;
        automaticGainControl = null;
    }

    private String websocketBase() {
        if (baseUrl.startsWith("https://")) return "wss://" + baseUrl.substring(8);
        if (baseUrl.startsWith("http://")) return "ws://" + baseUrl.substring(7);
        return baseUrl;
    }

    private static String normalizeBaseUrl(String value) {
        if (value == null) return "";
        String out = value.trim();
        while (out.endsWith("/")) out = out.substring(0, out.length() - 1);
        return out;
    }

    private String loadPlayerId() {
        String saved = activity.getSharedPreferences("xziel_multiplayer", Context.MODE_PRIVATE)
            .getString("player_id", "");
        if (saved != null && !saved.isEmpty()) return saved;

        String androidId = Settings.Secure.getString(
            activity.getContentResolver(), Settings.Secure.ANDROID_ID);
        String generated = (androidId == null || androidId.isEmpty())
            ? UUID.randomUUID().toString()
            : "android-" + androidId;

        activity.getSharedPreferences("xziel_multiplayer", Context.MODE_PRIVATE)
            .edit().putString("player_id", generated).apply();
        return generated;
    }

    private void toast(String text) {
        activity.runOnUiThread(() ->
            Toast.makeText(activity, text, Toast.LENGTH_SHORT).show());
    }
}
