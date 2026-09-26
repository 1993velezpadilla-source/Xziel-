package org.libsdl.app;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.provider.Settings;
import android.text.InputFilter;
import android.util.Log;
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

import okio.ByteString;
import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;

/**
 * Xziel internet multiplayer transport.
 *
 * Cloudflare owns private rooms/public matchmaking and WebSocket routing.
 * Vril keeps its native Quake datagram protocol unchanged: raw UDP datagrams
 * are wrapped in XZD1 and routed between virtual 10.77.0.x peers.
 */
public final class XzielMultiplayer {
    private static final String TAG = "XzielOnline";
    private static final int MAX_PLAYERS = 4;
    private static final int GAME_HEADER_BYTES = 9;
    private static final int MAX_GAME_DATAGRAM = 4096;
    private static final int MAX_QUEUE_PER_PORT = 256;
    private static final long CONNECT_RETRY_MS = 3000L;
    private static final String DEFAULT_MAP = "ndu";
    private static final MediaType JSON =
        MediaType.parse("application/json; charset=utf-8");

    private final Activity activity;
    private final OkHttpClient http;
    private final ConcurrentHashMap<Integer, ConcurrentLinkedQueue<GamePacket>> packetsByPort =
        new ConcurrentHashMap<>();
    private final Set<Integer> connectedSlots = ConcurrentHashMap.newKeySet();
    private final AtomicReference<String> pendingNativeCommand =
        new AtomicReference<>("");

    private volatile String baseUrl;
    private volatile String roomCode = "";
    private volatile String roomMode = "private";
    private volatile String selectedMap = DEFAULT_MAP;
    private volatile String playerId;
    private volatile int localSlot;
    private volatile WebSocket gameSocket;
    private volatile WebSocket matchSocket;
    private volatile AlertDialog activeDialog;

    private volatile boolean matchStarted;
    private volatile boolean hostPreparing;
    private volatile boolean serverReadySent;
    private volatile boolean serverReadyReceived;
    private volatile boolean clientReadySent;
    private volatile boolean engineServerActive;
    private volatile boolean engineClientConnected;
    private volatile int engineSignon;
    private volatile String engineMap = "";
    private volatile long lastConnectAttemptMs;

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

            AlertDialog dialog = new AlertDialog.Builder(activity)
                .setTitle("ONLINE MULTIPLAYER")
                .setMessage("Private rooms or automatic public matchmaking - up to 4 players.")
                .setPositiveButton("PRIVATE ROOM", (d, w) -> showPrivateMenu())
                .setNegativeButton("FIND PUBLIC MATCH", (d, w) -> findPublicMatch())
                .setNeutralButton("CANCEL", null)
                .create();
            showTracked(dialog);
        });
    }

    private void showPrivateMenu() {
        activity.runOnUiThread(() -> {
            AlertDialog dialog = new AlertDialog.Builder(activity)
                .setTitle("PRIVATE ROOM")
                .setMessage("Create a room and share the 6-character code, or join a friend's room.")
                .setPositiveButton("CREATE ROOM", (d, w) -> showMapSelection())
                .setNegativeButton("JOIN ROOM", (d, w) -> showJoinDialog())
                .setNeutralButton("BACK", (d, w) -> openMultiplayerMenu())
                .create();
            showTracked(dialog);
        });
    }

    private void showMapSelection() {
        activity.runOnUiThread(() -> {
            final String[] labels = { "NACHT DER UNTOTEN" };
            final String[] maps = { "ndu" };
            AlertDialog dialog = new AlertDialog.Builder(activity)
                .setTitle("SELECT MAP")
                .setItems(labels, (d, which) -> {
                    selectedMap = maps[which];
                    createRoom(selectedMap);
                })
                .setNegativeButton("BACK", (d, w) -> showPrivateMenu())
                .create();
            showTracked(dialog);
        });
    }

    private void showJoinDialog() {
        activity.runOnUiThread(() -> {
            EditText input = new EditText(activity);
            input.setSingleLine(true);
            input.setHint("6-CHARACTER ROOM CODE");
            input.setAllCaps(true);
            input.setFilters(new InputFilter[] { new InputFilter.LengthFilter(6) });

            AlertDialog dialog = new AlertDialog.Builder(activity)
                .setTitle("JOIN PRIVATE ROOM")
                .setView(input)
                .setPositiveButton("JOIN", null)
                .setNegativeButton("BACK", (d, w) -> showPrivateMenu())
                .create();

            dialog.setOnShowListener(v -> {
                dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(button -> {
                    String code = input.getText().toString().trim().toUpperCase(Locale.US);
                    if (!code.matches("[A-HJ-NP-Z2-9]{6}")) {
                        input.setError("Enter the 6-character room code");
                        return;
                    }
                    dialog.dismiss();
                    activeDialog = null;
                    joinRoom(code, false);
                });

                input.requestFocus();
                InputMethodManager imm = (InputMethodManager)
                    activity.getSystemService(Context.INPUT_METHOD_SERVICE);
                if (imm != null) {
                    imm.showSoftInput(input, InputMethodManager.SHOW_IMPLICIT);
                }
            });

            showTracked(dialog);
        });
    }

    private void createRoom(String map) {
        JSONObject body = new JSONObject();
        try {
            body.put("playerId", playerId);
            body.put("map", map);
        } catch (Exception ignored) {}

        Request request = new Request.Builder()
            .url(baseUrl + "/api/rooms/create")
            .post(RequestBody.create(body.toString(), JSON))
            .build();

        toast("Creating private room...");
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

                    JSONObject answer = new JSONObject(r.body().string());
                    String code = answer.optString("roomCode", "");
                    if (code.length() != 6) {
                        toast("Server returned an invalid room");
                        return;
                    }
                    selectedMap = answer.optString("map", DEFAULT_MAP);
                    joinRoom(code, false);
                } catch (Exception e) {
                    toast("Could not read room response");
                }
            }
        });
    }

    public void findPublicMatch() {
        findPublicMatch("public-v1");
    }

    public void findPublicMatch(String queueName) {
        cancelMatchmaking();
        leaveGameRoomOnly();

        selectedMap = DEFAULT_MAP;
        roomMode = "public";

        String queue = queueName == null ? "public-v1"
            : queueName.replaceAll("[^A-Za-z0-9_-]", "");
        if (queue.isEmpty()) queue = "public-v1";

        String wsUrl = websocketBase() + "/matchmake?playerId=" + playerId +
            "&map=" + selectedMap + "&queue=" + queue;
        Request request = new Request.Builder().url(wsUrl).build();

        toast("Searching public match...");
        matchSocket = http.newWebSocket(request, new WebSocketListener() {
            @Override
            public void onMessage(WebSocket webSocket, String text) {
                try {
                    JSONObject message = new JSONObject(text);
                    String type = message.optString("type", "");
                    if ("searching".equals(type)) {
                        int queued = message.optInt("queued", 1);
                        toast("Searching... " + queued + "/" + MAX_PLAYERS);
                        return;
                    }
                    if ("match_found".equals(type)) {
                        String code = message.optString("roomCode", "");
                        selectedMap = message.optString("map", DEFAULT_MAP);
                        matchSocket = null;
                        try { webSocket.close(1000, "matched"); } catch (Exception ignored) {}
                        if (code.length() == 6) {
                            toast("Match found");
                            joinRoom(code, true);
                        }
                    }
                } catch (Exception ignored) {}
            }

            @Override
            public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                if (matchSocket == webSocket) {
                    matchSocket = null;
                    toast("Public matchmaking connection failed");
                }
            }
        });
    }

    private void joinRoom(String code, boolean publicMatch) {
        leaveGameRoomOnly();

        roomCode = code;
        roomMode = publicMatch ? "public" : "private";
        localSlot = 0;
        matchStarted = false;
        hostPreparing = false;
        serverReadySent = false;
        serverReadyReceived = false;
        clientReadySent = false;
        lastConnectAttemptMs = 0;
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
                if (gameSocket == webSocket) {
                    gameSocket = null;
                    localSlot = 0;
                }
            }

            @Override
            public void onClosed(WebSocket webSocket, int codeValue, String reason) {
                if (gameSocket == webSocket) {
                    gameSocket = null;
                    localSlot = 0;
                }
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
                selectedMap = message.optString("map", DEFAULT_MAP);
                roomMode = message.optString("mode", roomMode);
                connectedSlots.add(slot);
                queueNativeCommand("name XzielP" + slot + "\n");
                Log.i(TAG, "WELCOME room=" + roomCode + " mode=" + roomMode +
                    " slot=" + slot + " map=" + selectedMap);
                toast(("public".equals(roomMode) ? "Public match" : "Room " + roomCode) +
                    " - Player " + slot);

                if ("private".equals(roomMode)) {
                    activity.runOnUiThread(this::showLobbyDialog);
                }
                return;
            }

            if ("player_joined".equals(type)) {
                int slot = message.optInt("slot", 0);
                if (slot >= 1 && slot <= MAX_PLAYERS) {
                    connectedSlots.add(slot);
                    Log.i(TAG, "PLAYER_JOINED slot=" + slot + " count=" + connectedSlots.size());
                    toast("Player " + slot + " connected");
                }
                return;
            }

            if ("player_left".equals(type)) {
                int slot = message.optInt("slot", 0);
                connectedSlots.remove(slot);
                toast("Player " + slot + " left");
                return;
            }

            if ("room_full".equals(type)) {
                if ("public".equals(roomMode) && localSlot == 1 && !hostPreparing) {
                    startHostMatch(true);
                } else if ("public".equals(roomMode)) {
                    toast("4/4 players - starting match...");
                }
                return;
            }

            if ("prepare_game".equals(type) && localSlot != 1) {
                selectedMap = message.optString("map", selectedMap);
                matchStarted = true;
                dismissTrackedDialog();
                Log.i(TAG, "PREPARE_GAME slot=" + localSlot + " map=" + selectedMap);
                toast("Host is loading " + prettyMap(selectedMap) + "...");
                return;
            }

            if ("server_ready".equals(type) && localSlot != 1) {
                selectedMap = message.optString("map", selectedMap);
                serverReadyReceived = true;
                matchStarted = true;
                dismissTrackedDialog();
                Log.i(TAG, "SERVER_READY slot=" + localSlot + " map=" + selectedMap);
                beginClientConnection(false);
                return;
            }

            if ("client_ready".equals(type) && localSlot == 1) {
                int slot = message.optInt("slot", 0);
                if (slot >= 2 && slot <= MAX_PLAYERS) {
                    Log.i(TAG, "CLIENT_READY host=1 clientSlot=" + slot);
                    toast("Player " + slot + " entered the match");
                }
            }
        } catch (Exception ignored) {
        }
    }

    private void showLobbyDialog() {
        if (!isOnlineActive()) return;

        activity.runOnUiThread(() -> {
            if (!isOnlineActive()) return;
            boolean host = localSlot == 1;
            String message =
                "ROOM CODE: " + roomCode +
                "\nMAP: " + prettyMap(selectedMap) +
                "\nPLAYER: " + localSlot +
                "\nPLAYERS CONNECTED: " + connectedSlots.size() + "/" + MAX_PLAYERS +
                (host
                    ? "\n\nShare the code. Start when everyone is ready."
                    : "\n\nWaiting for Player 1 to start the match.");

            AlertDialog.Builder builder = new AlertDialog.Builder(activity)
                .setTitle(host ? "PRIVATE ROOM - HOST" : "PRIVATE ROOM")
                .setMessage(message)
                .setNegativeButton("LEAVE ROOM", (d, w) -> leaveRoom())
                .setNeutralButton("CLOSE", null);

            if (host && !matchStarted && !hostPreparing) {
                builder.setPositiveButton("START MATCH", (d, w) -> startHostMatch(false));
            }

            showTracked(builder.create());
        });
    }

    private void startHostMatch(boolean automaticPublicStart) {
        if (localSlot != 1 || hostPreparing || gameSocket == null) return;

        hostPreparing = true;
        matchStarted = true;
        serverReadySent = false;
        serverReadyReceived = false;
        dismissTrackedDialog();

        JSONObject prepare = new JSONObject();
        try {
            prepare.put("type", "prepare_game");
            prepare.put("map", selectedMap);
            gameSocket.send(prepare.toString());
        } catch (Exception ignored) {}

        queueNativeCommand(
            "disconnect\n" +
            "maxplayers 4\n" +
            "coop 1\n" +
            "deathmatch 0\n" +
            "listen 1\n" +
            "map " + selectedMap + "\n"
        );

        Log.i(TAG, "HOST_PREPARE mode=" + roomMode + " map=" + selectedMap +
            " players=" + connectedSlots.size());
        toast((automaticPublicStart ? "Public match ready - " : "Starting ") +
            prettyMap(selectedMap) + "...");
    }

    private void beginClientConnection(boolean retry) {
        if (localSlot <= 1 || gameSocket == null || !serverReadyReceived) return;

        long now = System.currentTimeMillis();
        if (retry && now - lastConnectAttemptMs < CONNECT_RETRY_MS) return;
        lastConnectAttemptMs = now;

        Log.i(TAG, (retry ? "CONNECT_RETRY" : "CONNECT_START") +
            " slot=" + localSlot + " target=10.77.0.1:26000");
        if (retry) {
            queueNativeCommand("disconnect\nconnect 10.77.0.1:26000\n");
            toast("Reconnecting to host...");
        } else {
            queueNativeCommand("connect 10.77.0.1:26000\n");
            toast("Server ready - entering match...");
        }
    }

    /**
     * Called from the native Vril game thread at a low frequency.
     * This closes the old race where clients tried to connect before the host
     * had actually opened its Quake listen socket.
     */
    public void onEngineState(boolean serverActive, boolean clientConnected,
                              int signon, String map) {
        engineServerActive = serverActive;
        engineClientConnected = clientConnected;
        engineSignon = signon;
        engineMap = map == null ? "" : map;

        if (!isOnlineActive()) return;

        if (localSlot == 1 && hostPreparing && !serverReadySent &&
            serverActive && selectedMap.equals(engineMap)) {
            serverReadySent = true;
            hostPreparing = false;

            JSONObject ready = new JSONObject();
            try {
                ready.put("type", "server_ready");
                ready.put("map", selectedMap);
                WebSocket socket = gameSocket;
                if (socket != null) socket.send(ready.toString());
            } catch (Exception ignored) {}

            Log.i(TAG, "HOST_SERVER_READY map=" + selectedMap);
            toast("Server ready - bringing players in");
            return;
        }

        if (localSlot > 1 && serverReadyReceived) {
            if (!clientConnected || signon < 4) {
                beginClientConnection(true);
            } else if (!clientReadySent) {
                clientReadySent = true;
                JSONObject ready = new JSONObject();
                try {
                    ready.put("type", "client_ready");
                    WebSocket socket = gameSocket;
                    if (socket != null) socket.send(ready.toString());
                } catch (Exception ignored) {}
                Log.i(TAG, "SIGNON_COMPLETE slot=" + localSlot +
                    " signon=" + signon + " map=" + engineMap);
                toast("Connected to match");
            }
        }
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
        cancelMatchmaking();
        leaveGameRoomOnly();
        dismissTrackedDialog();
    }

    private void leaveGameRoomOnly() {
        WebSocket socket = gameSocket;
        gameSocket = null;
        if (socket != null) {
            try { socket.close(1000, "leave"); } catch (Exception ignored) {}
        }

        roomCode = "";
        localSlot = 0;
        matchStarted = false;
        hostPreparing = false;
        serverReadySent = false;
        serverReadyReceived = false;
        clientReadySent = false;
        connectedSlots.clear();
        packetsByPort.clear();
        pendingNativeCommand.set("");
    }

    private void cancelMatchmaking() {
        WebSocket socket = matchSocket;
        matchSocket = null;
        if (socket != null) {
            try { socket.close(1000, "cancel"); } catch (Exception ignored) {}
        }
    }

    public void shutdown() {
        leaveRoom();
        http.dispatcher().executorService().shutdown();
        http.connectionPool().evictAll();
    }

    private void showTracked(AlertDialog dialog) {
        dismissTrackedDialog();
        activeDialog = dialog;
        dialog.setOnDismissListener(d -> {
            if (activeDialog == dialog) activeDialog = null;
        });
        dialog.show();
    }

    private void dismissTrackedDialog() {
        activity.runOnUiThread(() -> {
            AlertDialog dialog = activeDialog;
            activeDialog = null;
            if (dialog != null && dialog.isShowing()) {
                try { dialog.dismiss(); } catch (Exception ignored) {}
            }
        });
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

    private static String prettyMap(String map) {
        return "ndu".equals(map) ? "Nacht der Untoten" : map;
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
