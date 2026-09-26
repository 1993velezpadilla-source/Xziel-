import { DurableObject } from "cloudflare:workers";

const MAX_PLAYERS = 4;
const CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const GAME_MAGIC = [0x58, 0x5a, 0x44, 0x31]; // XZD1
const GAME_HEADER_BYTES = 9;
const MAX_GAME_DATAGRAM = 4096;
const MAX_VOICE_PACKET = 4096;

function roomCode() {
  const b = new Uint8Array(6);
  crypto.getRandomValues(b);
  let out = "";
  for (const n of b) out += CODE_CHARS[n % CODE_CHARS.length];
  return out;
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "content-type": "application/json",
      "cache-control": "no-store",
    },
  });
}

function upgrade(request) {
  return request.headers.get("Upgrade")?.toLowerCase() === "websocket";
}

function isGamePacket(bytes) {
  return bytes.length >= GAME_HEADER_BYTES &&
    bytes[0] === GAME_MAGIC[0] &&
    bytes[1] === GAME_MAGIC[1] &&
    bytes[2] === GAME_MAGIC[2] &&
    bytes[3] === GAME_MAGIC[3];
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/health") {
      return json({
        ok: true,
        service: "xziel-multiplayer",
        transport: "websocket-datagram-tunnel",
        maxPlayers: MAX_PLAYERS,
      });
    }

    if (request.method === "POST" && url.pathname === "/api/rooms/create") {
      const code = roomCode();
      const id = env.GAME_ROOMS.idFromName(code);
      const stub = env.GAME_ROOMS.get(id);
      await stub.fetch(new Request("https://room/init", {
        method: "POST",
        body: JSON.stringify({ code }),
      }));
      return json({ roomCode: code, maxPlayers: MAX_PLAYERS });
    }

    const match = url.pathname.match(/^\/(game|voice)\/([A-Z0-9]{6})$/);
    if (match && upgrade(request)) {
      const [, kind, code] = match;
      const id = env.GAME_ROOMS.idFromName(code);
      const stub = env.GAME_ROOMS.get(id);
      const target = new URL(request.url);
      target.pathname = "/socket";
      target.searchParams.set("kind", kind);
      target.searchParams.set("room", code);
      return stub.fetch(new Request(target, request));
    }

    return json({ error: "not_found" }, 404);
  },
};

export class GameRoom extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.ctx = ctx;
  }

  async fetch(request) {
    const url = new URL(request.url);

    if (request.method === "POST" && url.pathname === "/init") {
      const body = await request.json();
      await this.ctx.storage.put("roomCode", String(body.code || ""));
      return json({ ok: true });
    }

    if (url.pathname !== "/socket" || !upgrade(request)) {
      return json({ error: "upgrade_required" }, 426);
    }

    const expectedRoom = String((await this.ctx.storage.get("roomCode")) || "");
    const requestedRoom = String(url.searchParams.get("room") || "");
    if (!expectedRoom || requestedRoom !== expectedRoom) {
      return json({ error: "room_not_found" }, 404);
    }

    const kind = url.searchParams.get("kind") === "voice" ? "voice" : "game";
    const playerId = String(
      url.searchParams.get("playerId") || crypto.randomUUID()
    ).slice(0, 64);
    const sockets = this.ctx.getWebSockets();

    const gameByPlayer = new Map();
    const usedSlots = new Set();
    for (const socket of sockets) {
      const a = socket.deserializeAttachment() || {};
      if (a.kind === "game") {
        gameByPlayer.set(a.playerId, a);
        usedSlots.add(a.slot);
      }
    }

    let slot = 0;
    if (kind === "game") {
      const existing = gameByPlayer.get(playerId);
      if (existing) {
        slot = existing.slot;
      } else {
        if (gameByPlayer.size >= MAX_PLAYERS) {
          return json({ error: "room_full", maxPlayers: MAX_PLAYERS }, 409);
        }
        for (let candidate = 1; candidate <= MAX_PLAYERS; candidate += 1) {
          if (!usedSlots.has(candidate)) {
            slot = candidate;
            break;
          }
        }
      }
    } else {
      const game = gameByPlayer.get(playerId);
      if (!game) {
        return json({ error: "join_game_socket_first" }, 403);
      }
      slot = game.slot;
    }

    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    this.ctx.acceptWebSocket(server);
    server.serializeAttachment({ kind, playerId, slot });

    if (kind === "game") {
      try {
        server.send(JSON.stringify({
          type: "welcome",
          roomCode: expectedRoom,
          playerId,
          slot,
          maxPlayers: MAX_PLAYERS,
          hostSlot: 1,
          serverTime: Date.now(),
        }));
      } catch {}
      this.broadcastJson(
        { type: "player_joined", playerId, slot },
        server,
      );
    } else {
      try {
        server.send(JSON.stringify({
          type: "voice_ready",
          playerId,
          slot,
          serverTime: Date.now(),
        }));
      } catch {}
    }

    return new Response(null, { status: 101, webSocket: client });
  }

  webSocketMessage(ws, message) {
    const sender = ws.deserializeAttachment() || {};

    if (typeof message === "string") {
      if (sender.kind !== "game" || message.length > 32768) return;

      let parsed;
      try {
        parsed = JSON.parse(message);
      } catch {
        return;
      }
      if (!parsed || typeof parsed !== "object") return;

      if (parsed.type === "start_game") {
        // Slot 1 is room authority. Clients cannot spoof a game start.
        if (sender.slot !== 1) return;
        parsed.map = "ndu";
      }

      parsed.playerId = sender.playerId;
      parsed.slot = sender.slot;
      parsed.serverTime = Date.now();
      this.broadcastText(JSON.stringify(parsed), ws, "game");
      return;
    }

    if (!(message instanceof ArrayBuffer)) return;

    if (sender.kind === "voice") {
      if (message.byteLength > MAX_VOICE_PACKET) return;
      this.broadcastBinary(message, ws, "voice");
      return;
    }

    if (sender.kind !== "game") return;

    const bytes = new Uint8Array(message);
    if (!isGamePacket(bytes)) return;
    if (bytes.length > GAME_HEADER_BYTES + MAX_GAME_DATAGRAM) return;

    const destinationSlot = bytes[4];
    if (destinationSlot < 1 || destinationSlot > MAX_PLAYERS) return;
    if (destinationSlot === sender.slot) return;

    // Client packet header:
    // XZD1 | dstSlot | srcPort(be16) | dstPort(be16) | raw Quake datagram
    // Receiver packet uses the same shape but byte 4 becomes srcSlot.
    const forwarded = new Uint8Array(bytes.length);
    forwarded.set(bytes);
    forwarded[4] = sender.slot;

    for (const socket of this.ctx.getWebSockets()) {
      const a = socket.deserializeAttachment() || {};
      if (a.kind !== "game" || a.slot !== destinationSlot) continue;
      try {
        socket.send(forwarded.buffer);
      } catch {}
      break;
    }
  }

  webSocketClose(ws) {
    const sender = ws.deserializeAttachment() || {};
    if (sender.kind === "game") {
      this.broadcastJson(
        { type: "player_left", playerId: sender.playerId, slot: sender.slot },
        ws,
      );
    }
  }

  webSocketError() {}

  broadcastJson(value, except) {
    this.broadcastText(
      JSON.stringify({ ...value, serverTime: Date.now() }),
      except,
      "game",
    );
  }

  broadcastText(text, except, kind) {
    for (const socket of this.ctx.getWebSockets()) {
      if (socket === except) continue;
      const a = socket.deserializeAttachment() || {};
      if (a.kind !== kind) continue;
      try {
        socket.send(text);
      } catch {}
    }
  }

  broadcastBinary(buffer, except, kind) {
    for (const socket of this.ctx.getWebSockets()) {
      if (socket === except) continue;
      const a = socket.deserializeAttachment() || {};
      if (a.kind !== kind) continue;
      try {
        socket.send(buffer);
      } catch {}
    }
  }
}
