package org.libsdl.app;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.provider.Settings;
import android.text.InputFilter;
import android.view.inputmethod.InputMethodManager;
import android.widget.EditText;
import android.widget.Toast;

import org.json.JSONObject;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Locale;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

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
 * Xziel internet multiplayer test transport.
 *
 * Cloudflare owns room discovery and WebSocket routing. Vril keeps its native
 * Quake datagram protocol unchanged: raw UDP datagrams are wrapped in XZD1,
 * routed by room/player slot, and restored into virtual 10.77.0.x peers.
 */
public final class XzielMultiplayer {
    private static final int MAX_PLAYERS = 4;
    private static final int GAME_HEADER_BYTES = 9;
    private static final int MAX_GAME_DATAGRAM = 4096;
    private static final int MAX_QUEUE_PER_PORT = 256;

    private final Activity activity;
    private final OkHttpClient http;
    private final ConcurrentHashMap<Integer, ConcurrentLinkedQueue<GamePacket>> packetsByPort =
        new ConcurrentHashMap<>();
    private final Set<Integer> connectedSlots = ConcurrentHashMap.newKeySet();
    private final AtomicReference<String> pendingNativeCommand =
        new AtomicReference<>("");

    private volatile String baseUrl;
    private volatile String roomCode = "";
    private volatile String playerId;
    private volatile int localSlot;
    private volatile WebSocket gameSocket;
    private volatile boolean matchStarted;

    private static final class GamePacket {
        final int sourceSlot;
        final int sourcePort;
        final byte[] payload;

        GamePacket(int sourceSlot, int sourcePort, byte[] payload) {
            this.sourceSlot = sourceSlot;
            this.sourcePort = sourcePort;
            this.payload = payload;
        }
    }

    public XzielMultiplayer(Activity activity, String endpoint) {
        this.activity = activity;
        this.baseUrl = normalizeBaseUrl(endpoint);
        this.playerId = loadPlayerId();
        this.http = new OkHttpClient.Builder()
            .pingInterval(15, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build();
    }

    public boolean isOnlineActive() {
        return gameSocket != null && localSlot >= 1 && localSlot <= MAX_PLAYERS;
    }

    public int getLocalSlot() {
        return localSlot;
    }

    public void openMultiplayerMenu() {
        activity.runOnUiThread(() -> {
            if (baseUrl.isEmpty()) {
                Toast.makeText(
                    activity,
                    "This APK was built without the multiplayer backend URL.",
                    Toast.LENGTH_LONG
                ).show();
                return;
            }

            if (isOnlineActive()) {
                showLobbyDialog();
                return;
            }

            new AlertDialog.Builder(activity)
                .setTitle("ONLINE MULTIPLAYER")
                .setMessage("Private internet room - up to 4 players.")
                .setPositiveButton("CREATE ROOM", (d, w) -> createRoom())
                .setNegativeButton("JOIN ROOM", (d, w) -> showJoinDialog())
                .setNeutralButton("CANCEL", null)
                .show();
        });
    }

    private void showJoinDialog() {
        EditText input = new EditText(activity);
        input.setSingleLine(true);
        input.setHint("6-CHARACTER ROOM CODE");
        input.setAllCaps(true);
        input.setFilters(new InputFilter[] { new InputFilter.LengthFilter(6) });

        AlertDialog dialog = new AlertDialog.Builder(activity)
            .setTitle("JOIN ONLINE ROOM")
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
            if (imm != null) {
                imm.showSoftInput(input, InputMethodManager.SHOW_IMPLICIT);
            }
        });

        dialog.show();
    }

    private void createRoom() {
        Request request = new Request.Builder()
            .url(baseUrl + "/api/rooms/create")
            .post(RequestBody.create(new byte[0], null))
            .build();

        toast("Creating online room...");
        http.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, java.io.IOException e) {
                toast("Could not reach multiplayer service");
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
        matchStarted = false;
        connectedSlots.clear();
        packetsByPort.clear();

        String wsUrl = websocketBase() + "/game/" + code + "?playerId=" + playerId;
        Request request = new Request.Builder().url(wsUrl).build();

        toast("Joining room " + code + "...");
        gameSocket = http.newWebSocket(request, new WebSocketListener() {
            @Override
            public void onOpen(WebSocket webSocket, Response response) {
                webSocket.send("{\"type\":\"hello\"}");
            }

            @Override
            public void onMessage(WebSocket webSocket, String text) {
                handleControlMessage(text);
            }

            @Override
            public void onMessage(WebSocket webSocket, ByteString bytes) {
                handleGamePacket(bytes.toByteArray());
            }

            @Override
            public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                int status = response != null ? response.code() : 0;
                if (!roomCode.isEmpty()) {
                    if (status == 404) toast("Room not found");
                    else if (status == 409) toast("Room is full");
                    else toast("Online connection lost");
                }
                gameSocket = null;
                localSlot = 0;
            }

            @Override
            public void onClosed(WebSocket webSocket, int codeValue, String reason) {
                gameSocket = null;
                localSlot = 0;
            }
        });
    }

    private void handleControlMessage(String text) {
        try {
            JSONObject message = new JSONObject(text);
            String type = message.optString("type", "");

            if ("welcome".equals(type)) {
                int slot = message.optInt("slot", 0);
                if (slot < 1 || slot > MAX_PLAYERS) {
                    toast("Invalid multiplayer slot");
                    leaveRoom();
                    return;
                }

                localSlot = slot;
                connectedSlots.add(slot);
                toast("Room " + roomCode + " - Player " + slot);
                activity.runOnUiThread(this::showLobbyDialog);
                return;
            }

            if ("player_joined".equals(type)) {
                int slot = message.optInt("slot", 0);
                if (slot >= 1 && slot <= MAX_PLAYERS) {
                    connectedSlots.add(slot);
                    toast("Player " + slot + " joined");
                }
                return;
            }

            if ("player_left".equals(type)) {
                int slot = message.optInt("slot", 0);
                connectedSlots.remove(slot);
                toast("Player " + slot + " left");
                return;
            }

            if ("start_game".equals(type) && localSlot != 1) {
                matchStarted = true;
                // Slot 1 is represented by the virtual tunnel address.
                queueNativeCommand("connect 10.77.0.1:26000\n");
                toast("Host started Nacht - connecting...");
            }
        } catch (Exception ignored) {
        }
    }

    private void showLobbyDialog() {
        if (!isOnlineActive()) return;

        boolean host = localSlot == 1;
        String message =
            "ROOM CODE: " + roomCode +
            "\nPLAYER: " + localSlot +
            "\nPLAYERS CONNECTED: " + connectedSlots.size() + "/" + MAX_PLAYERS +
            (host
                ? "\n\nSend this room code to your cousin. Press START NACHT when ready."
                : "\n\nWaiting for Player 1 to start Nacht.");

        AlertDialog.Builder builder = new AlertDialog.Builder(activity)
            .setTitle(host ? "HOST ONLINE ROOM" : "ONLINE ROOM")
            .setMessage(message)
            .setNegativeButton("LEAVE", (d, w) -> leaveRoom())
            .setNeutralButton("CLOSE", null);

        if (host && !matchStarted) {
            builder.setPositiveButton("START NACHT", (d, w) -> startHostMatch());
        }

        builder.show();
    }

    private void startHostMatch() {
        if (localSlot != 1 || matchStarted || gameSocket == null) return;

        matchStarted = true;

        // Configure the existing Vril/NZ:P Quake server as 4-player co-op.
        // The host remains authoritative; the tunnel only moves datagrams.
        queueNativeCommand(
            "maxplayers 4\n" +
            "coop 1\n" +
            "deathmatch 0\n" +
            "listen 1\n" +
            "map ndu\n"
        );

        gameSocket.send("{\"type\":\"start_game\",\"map\":\"ndu\"}");
        toast("Starting Nacht online...");
    }

    public boolean sendGameDatagram(byte[] payload, int destinationSlot,
                                    int sourcePort, int destinationPort) {
        WebSocket socket = gameSocket;
        if (socket == null || payload == null ||
            payload.length <= 0 || payload.length > MAX_GAME_DATAGRAM ||
            destinationSlot < 1 || destinationSlot > MAX_PLAYERS ||
            sourcePort < 0 || sourcePort > 65535 ||
            destinationPort < 0 || destinationPort > 65535) {
            return false;
        }

        ByteBuffer packet = ByteBuffer
            .allocate(GAME_HEADER_BYTES + payload.length)
            .order(ByteOrder.BIG_ENDIAN);

        packet.put((byte)'X');
        packet.put((byte)'Z');
        packet.put((byte)'D');
        packet.put((byte)'1');
        packet.put((byte)destinationSlot);
        packet.putShort((short)(sourcePort & 0xffff));
        packet.putShort((short)(destinationPort & 0xffff));
        packet.put(payload);

        return socket.send(ByteString.of(packet.array()));
    }

    private void handleGamePacket(byte[] data) {
        if (data == null || data.length <= GAME_HEADER_BYTES) return;

        ByteBuffer packet = ByteBuffer.wrap(data).order(ByteOrder.BIG_ENDIAN);
        if (packet.get() != 'X' || packet.get() != 'Z' ||
            packet.get() != 'D' || packet.get() != '1') {
            return;
        }

        int sourceSlot = packet.get() & 0xff;
        int sourcePort = packet.getShort() & 0xffff;
        int destinationPort = packet.getShort() & 0xffff;

        if (sourceSlot < 1 || sourceSlot > MAX_PLAYERS ||
            sourceSlot == localSlot || destinationPort <= 0 ||
            packet.remaining() <= 0 || packet.remaining() > MAX_GAME_DATAGRAM) {
            return;
        }

        byte[] payload = new byte[packet.remaining()];
        packet.get(payload);

        ConcurrentLinkedQueue<GamePacket> queue = packetsByPort.computeIfAbsent(
            destinationPort,
            ignored -> new ConcurrentLinkedQueue<>()
        );

        while (queue.size() >= MAX_QUEUE_PER_PORT) {
            queue.poll();
        }
        queue.offer(new GamePacket(sourceSlot, sourcePort, payload));
    }

    /**
     * Native poll packet format:
     * byte 0 = source slot
     * bytes 1..2 = source port, network byte order
     * bytes 3.. = raw Quake datagram
     */
    public byte[] pollGameDatagram(int localPort) {
        ConcurrentLinkedQueue<GamePacket> queue = packetsByPort.get(localPort);
        if (queue == null) return null;

        GamePacket packet = queue.poll();
        if (packet == null) return null;

        byte[] out = new byte[3 + packet.payload.length];
        out[0] = (byte)packet.sourceSlot;
        out[1] = (byte)((packet.sourcePort >>> 8) & 0xff);
        out[2] = (byte)(packet.sourcePort & 0xff);
        System.arraycopy(packet.payload, 0, out, 3, packet.payload.length);
        return out;
    }

    public boolean hasGameDatagram(int localPort) {
        ConcurrentLinkedQueue<GamePacket> queue = packetsByPort.get(localPort);
        return queue != null && queue.peek() != null;
    }

    public String pollNativeCommand() {
        String command = pendingNativeCommand.getAndSet("");
        return command == null ? "" : command;
    }

    private void queueNativeCommand(String command) {
        if (command == null || command.isEmpty()) return;
        pendingNativeCommand.updateAndGet(existing ->
            existing == null || existing.isEmpty() ? command : existing + command
        );
    }

    public void leaveRoom() {
        WebSocket socket = gameSocket;
        gameSocket = null;
        if (socket != null) {
            try {
                socket.close(1000, "leave");
            } catch (Exception ignored) {
            }
        }

        roomCode = "";
        localSlot = 0;
        matchStarted = false;
        connectedSlots.clear();
        packetsByPort.clear();
        pendingNativeCommand.set("");
    }

    public void shutdown() {
        leaveRoom();
        http.dispatcher().executorService().shutdown();
        http.connectionPool().evictAll();
    }

    private String websocketBase() {
        if (baseUrl.startsWith("https://")) {
            return "wss://" + baseUrl.substring(8);
        }
        if (baseUrl.startsWith("http://")) {
            return "ws://" + baseUrl.substring(7);
        }
        return baseUrl;
    }

    private static String normalizeBaseUrl(String value) {
        if (value == null) return "";
        String out = value.trim();
        while (out.endsWith("/")) {
            out = out.substring(0, out.length() - 1);
        }
        return out;
    }

    private String loadPlayerId() {
        String saved = activity
            .getSharedPreferences("xziel_multiplayer", Context.MODE_PRIVATE)
            .getString("player_id", "");

        if (saved != null && !saved.isEmpty()) return saved;

        String androidId = Settings.Secure.getString(
            activity.getContentResolver(),
            Settings.Secure.ANDROID_ID
        );

        String generated =
            (androidId == null || androidId.isEmpty())
                ? UUID.randomUUID().toString()
                : "android-" + androidId;

        activity
            .getSharedPreferences("xziel_multiplayer", Context.MODE_PRIVATE)
            .edit()
            .putString("player_id", generated)
            .apply();

        return generated;
    }

    private void toast(String text) {
        activity.runOnUiThread(() ->
            Toast.makeText(activity, text, Toast.LENGTH_SHORT).show()
        );
    }
}
