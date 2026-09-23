package com.xziel.engineprototype;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicInteger;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;
import okio.ByteString;

final class XzielRealtimeBridge {
    static final int STATE_DISCONNECTED = 0;
    static final int STATE_CONNECTING = 1;
    static final int STATE_CONNECTED = 2;
    static final int STATE_FAILED = 3;

    private static final int MAX_INBOUND_PACKETS = 128;

    private final OkHttpClient client =
        new OkHttpClient.Builder().build();

    private final ConcurrentLinkedQueue<byte[]> inbound =
        new ConcurrentLinkedQueue<>();

    private final AtomicInteger inboundCount =
        new AtomicInteger(0);

    private volatile WebSocket socket = null;
    private volatile int state = STATE_DISCONNECTED;

    boolean connect(
        String baseUrl,
        String roomCode,
        String displayName,
        String testKey
    ) {
        if (baseUrl == null ||
            baseUrl.isBlank() ||
            roomCode == null ||
            roomCode.isBlank()) {
            state = STATE_FAILED;
            return false;
        }

        disconnect();
        state = STATE_CONNECTING;

        String trimmed = baseUrl.endsWith("/")
            ? baseUrl.substring(0, baseUrl.length() - 1)
            : baseUrl;

        String room = roomCode
            .trim()
            .toUpperCase()
            .replaceAll("[^A-Z0-9_-]", "");

        if (room.length() < 4 || room.length() > 16) {
            state = STATE_FAILED;
            return false;
        }

        String name = displayName == null ||
            displayName.isBlank()
            ? "Player"
            : displayName.trim();

        if (name.length() > 20) {
            name = name.substring(0, 20);
        }

        String encodedName = URLEncoder.encode(
            name,
            StandardCharsets.UTF_8
        );

        Request.Builder builder =
            new Request.Builder()
                .url(
                    trimmed +
                    "/v1/rooms/" +
                    room +
                    "?name=" +
                    encodedName
                );

        if (testKey != null && !testKey.isBlank()) {
            builder.header(
                "X-Xziel-Test-Key",
                testKey
            );
        }

        socket = client.newWebSocket(
            builder.build(),
            new WebSocketListener() {
                @Override
                public void onOpen(
                    WebSocket webSocket,
                    Response response
                ) {
                    socket = webSocket;
                    state = STATE_CONNECTED;
                }

                @Override
                public void onMessage(
                    WebSocket webSocket,
                    ByteString bytes
                ) {
                    enqueue(bytes.toByteArray());
                }

                @Override
                public void onClosing(
                    WebSocket webSocket,
                    int code,
                    String reason
                ) {
                    webSocket.close(code, reason);
                }

                @Override
                public void onClosed(
                    WebSocket webSocket,
                    int code,
                    String reason
                ) {
                    if (socket == webSocket) {
                        socket = null;
                    }
                    state = STATE_DISCONNECTED;
                }

                @Override
                public void onFailure(
                    WebSocket webSocket,
                    Throwable throwable,
                    Response response
                ) {
                    if (socket == webSocket) {
                        socket = null;
                    }
                    state = STATE_FAILED;
                }
            }
        );

        return true;
    }

    void disconnect() {
        WebSocket current = socket;
        socket = null;

        if (current != null) {
            current.close(1000, "client_disconnect");
        }

        state = STATE_DISCONNECTED;
        inbound.clear();
        inboundCount.set(0);
    }

    boolean send(byte[] payload) {
        WebSocket current = socket;

        if (current == null ||
            state != STATE_CONNECTED ||
            payload == null ||
            payload.length == 0 ||
            payload.length > 1200) {
            return false;
        }

        return current.send(ByteString.of(payload));
    }

    byte[] poll() {
        byte[] packet = inbound.poll();
        if (packet != null) {
            inboundCount.decrementAndGet();
        }
        return packet;
    }

    int state() {
        return state;
    }

    private void enqueue(byte[] payload) {
        if (payload == null ||
            payload.length == 0 ||
            payload.length > 1200) {
            return;
        }

        while (inboundCount.get() >= MAX_INBOUND_PACKETS) {
            byte[] dropped = inbound.poll();
            if (dropped == null) {
                break;
            }
            inboundCount.decrementAndGet();
        }

        inbound.offer(payload);
        inboundCount.incrementAndGet();
    }
}
