import {
  MAX_PLAYERS,
  SNAPSHOT_INTERVAL_MS,
  decodePlayerInput,
  encodeSnapshot,
  encodeWelcome,
  type PlayerState,
} from "./protocol";

export interface Env {
  MATCH_ROOMS: DurableObjectNamespace<MatchRoom>;
  XZIEL_TEST_KEY?: string;
  XZIEL_BUILD_CHANNEL?: string;
}

interface SocketAttachment extends PlayerState {
  displayName: string;
  joinedAtMs: number;
}

const SPAWNS = [
  { x: -1200, y: -1480, z: -2200 },
  { x: 1200, y: -1480, z: -2200 },
  { x: -1200, y: -1480, z: -800 },
  { x: 1200, y: -1480, z: -800 },
] as const;

function json(value: unknown, init: ResponseInit = {}): Response {
  const headers = new Headers(init.headers);
  headers.set("content-type", "application/json; charset=utf-8");
  headers.set("cache-control", "no-store");
  return new Response(JSON.stringify(value), { ...init, headers });
}

function validRoomCode(value: string): boolean {
  return /^[A-Z0-9_-]{4,16}$/.test(value);
}

function safeDisplayName(value: string | null): string {
  const normalized = (value ?? "Player").trim().slice(0, 20);
  return normalized.length > 0 ? normalized : "Player";
}

function nextFreePlayerId(sockets: readonly WebSocket[]): number | null {
  const used = new Set<number>();

  for (const socket of sockets) {
    const attachment = socket.deserializeAttachment() as SocketAttachment | null;
    if (attachment && attachment.playerId >= 0 && attachment.playerId < MAX_PLAYERS) {
      used.add(attachment.playerId);
    }
  }

  for (let id = 0; id < MAX_PLAYERS; ++id) {
    if (!used.has(id)) return id;
  }

  return null;
}

export class MatchRoom extends DurableObject<Env> {
  private lastBroadcastMs = 0;
  private snapshotSequence = 0;

  constructor(ctx: DurableObjectState, env: Env) {
    super(ctx, env);
  }

  async fetch(request: Request): Promise<Response> {
    if (request.headers.get("upgrade")?.toLowerCase() !== "websocket") {
      const sockets = this.ctx.getWebSockets();
      return json({
        ok: true,
        players: sockets.length,
        capacity: MAX_PLAYERS,
      });
    }

    const sockets = this.ctx.getWebSockets();

    if (sockets.length >= MAX_PLAYERS) {
      return json(
        { error: "room_full", capacity: MAX_PLAYERS },
        { status: 409 },
      );
    }

    const playerId = nextFreePlayerId(sockets);
    if (playerId === null) {
      return json({ error: "room_full" }, { status: 409 });
    }

    const url = new URL(request.url);
    const displayName = safeDisplayName(url.searchParams.get("name"));
    const now = Date.now();
    const spawn = SPAWNS[playerId]!;

    const pair = new WebSocketPair();
    const client = pair[0];
    const server = pair[1];

    const attachment: SocketAttachment = {
      playerId,
      displayName,
      joinedAtMs: now,
      flags: 1,
      health: 100,
      points: 500,
      xMillimeters: spawn.x,
      yMillimeters: spawn.y,
      zMillimeters: spawn.z,
      yawCentidegrees: 0,
      pitchCentidegrees: 0,
      weaponId: 1,
      ammo: 96,
      lastInputSequence: 0,
      lastSeenMs: now,
    };

    server.serializeAttachment(attachment);
    this.ctx.acceptWebSocket(server, [`player:${playerId}`]);

    server.send(
      encodeWelcome(
        playerId,
        this.serverTick(now),
      ),
    );

    this.broadcastSnapshot(now, true);

    return new Response(null, {
      status: 101,
      webSocket: client,
    });
  }

  webSocketMessage(
    socket: WebSocket,
    message: string | ArrayBuffer,
  ): void {
    if (!(message instanceof ArrayBuffer)) {
      return;
    }

    const input = decodePlayerInput(message);
    if (!input) {
      socket.close(1003, "invalid_packet");
      return;
    }

    const attachment =
      socket.deserializeAttachment() as SocketAttachment | null;

    if (!attachment) {
      socket.close(1011, "missing_state");
      return;
    }

    const now = Date.now();
    const elapsedMs = Math.max(
      0,
      Math.min(100, now - attachment.lastSeenMs),
    );

    const moveX = Math.max(-1, Math.min(1, input.moveX / 32767));
    const moveY = Math.max(-1, Math.min(1, input.moveY / 32767));
    const length = Math.hypot(moveX, moveY);
    const normalizedX = length > 1 ? moveX / length : moveX;
    const normalizedY = length > 1 ? moveY / length : moveY;

    const maxSpeedMillimetersPerSecond =
      (input.buttons & (1 << 5)) !== 0 ? 6200 : 4700;
    const seconds = elapsedMs / 1000;

    const yawRadians =
      (input.yawCentidegrees / 100) *
      (Math.PI / 180);

    const forwardX = Math.sin(yawRadians);
    const forwardZ = Math.cos(yawRadians);
    const rightX = forwardZ;
    const rightZ = -forwardX;

    const velocityX =
      (rightX * normalizedX + forwardX * normalizedY) *
      maxSpeedMillimetersPerSecond;
    const velocityZ =
      (rightZ * normalizedX + forwardZ * normalizedY) *
      maxSpeedMillimetersPerSecond;

    attachment.xMillimeters += Math.round(velocityX * seconds);
    attachment.zMillimeters += Math.round(velocityZ * seconds);

    // Coarse global safety bounds. Map-specific collision/doors are the next
    // server-authority layer and will replace these with XZMAP collision data.
    attachment.xMillimeters = Math.max(
      -250_000,
      Math.min(250_000, attachment.xMillimeters),
    );
    attachment.zMillimeters = Math.max(
      -250_000,
      Math.min(250_000, attachment.zMillimeters),
    );

    attachment.yawCentidegrees = input.yawCentidegrees;
    attachment.pitchCentidegrees = input.pitchCentidegrees;
    attachment.lastInputSequence = input.sequence;
    attachment.lastSeenMs = now;

    socket.serializeAttachment(attachment);
    this.broadcastSnapshot(now, false);
  }

  webSocketClose(
    socket: WebSocket,
    code: number,
    reason: string,
    wasClean: boolean,
  ): void {
    void code;
    void reason;
    void wasClean;
    socket.close();
    this.broadcastSnapshot(Date.now(), true);
  }

  webSocketError(socket: WebSocket): void {
    socket.close(1011, "socket_error");
  }

  private serverTick(nowMs: number): number {
    return Math.floor(nowMs / SNAPSHOT_INTERVAL_MS) >>> 0;
  }

  private broadcastSnapshot(now: number, force: boolean): void {
    if (!force && now - this.lastBroadcastMs < SNAPSHOT_INTERVAL_MS) {
      return;
    }

    const sockets = this.ctx.getWebSockets();
    const players: PlayerState[] = [];

    for (const socket of sockets) {
      const attachment =
        socket.deserializeAttachment() as SocketAttachment | null;
      if (!attachment) continue;

      players.push({
        playerId: attachment.playerId,
        flags: attachment.flags,
        health: attachment.health,
        points: attachment.points,
        xMillimeters: attachment.xMillimeters,
        yMillimeters: attachment.yMillimeters,
        zMillimeters: attachment.zMillimeters,
        yawCentidegrees: attachment.yawCentidegrees,
        pitchCentidegrees: attachment.pitchCentidegrees,
        weaponId: attachment.weaponId,
        ammo: attachment.ammo,
        lastInputSequence: attachment.lastInputSequence,
        lastSeenMs: attachment.lastSeenMs,
      });
    }

    players.sort((a, b) => a.playerId - b.playerId);

    const packet = encodeSnapshot(
      this.snapshotSequence++,
      this.serverTick(now),
      1,
      players,
    );

    for (const socket of sockets) {
      try {
        socket.send(packet);
      } catch {
        // The close/error callback owns cleanup. A single dead peer must
        // never stop snapshots for the remaining players.
      }
    }

    this.lastBroadcastMs = now;
  }
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return json({
        ok: true,
        service: "xziel-match-server",
        protocol: 1,
        maxPlayers: MAX_PLAYERS,
        buildChannel: env.XZIEL_BUILD_CHANNEL ?? "dev",
      });
    }

    const match = /^\/v1\/rooms\/([A-Za-z0-9_-]{4,16})$/.exec(
      url.pathname,
    );

    if (!match) {
      return json(
        {
          error: "not_found",
          hint: "/v1/rooms/ROOMCODE?name=Player",
        },
        { status: 404 },
      );
    }

    const roomCode = match[1]!.toUpperCase();
    if (!validRoomCode(roomCode)) {
      return json({ error: "invalid_room" }, { status: 400 });
    }

    if (env.XZIEL_TEST_KEY) {
      const supplied = request.headers.get("x-xziel-test-key");
      if (supplied !== env.XZIEL_TEST_KEY) {
        return json({ error: "unauthorized" }, { status: 401 });
      }
    }

    const id = env.MATCH_ROOMS.idFromName(roomCode);
    const room = env.MATCH_ROOMS.get(id);

    const forwarded = new Request(
      `${url.origin}/room${url.search}`,
      request,
    );

    return room.fetch(forwarded);
  },
} satisfies ExportedHandler<Env>;
