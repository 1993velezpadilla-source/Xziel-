import WebSocket from "ws";

const base = process.env.XZIEL_MATCH_SERVER_WS;
const testKey = process.env.XZIEL_TEST_KEY;

if (!base || !testKey) {
  throw new Error("Missing XZIEL_MATCH_SERVER_WS or XZIEL_TEST_KEY");
}

const MAGIC = 0x5a58;
const VERSION = 1;
const WELCOME = 2;
const PLAYER_INPUT = 3;
const SNAPSHOT = 4;

const suffix = Date.now().toString(36).toUpperCase().slice(-8);
const room = `CI${suffix}`;

function openPlayer(index) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(
      `${base}/v1/rooms/${room}?name=CI-${index + 1}`,
      {
        headers: {
          "X-Xziel-Test-Key": testKey,
        },
      },
    );

    let opened = false;
    let welcome = null;

    const timer = setTimeout(() => {
      ws.terminate();
      reject(new Error(`player ${index} connect/welcome timeout`));
    }, 15000);

    const maybeResolve = () => {
      if (!opened || welcome === null) return;
      clearTimeout(timer);
      resolve({ ws, welcome });
    };

    ws.on("message", (data, isBinary) => {
      if (!isBinary || welcome !== null) return;

      const bytes = Buffer.from(data);
      if (bytes.length < 14) return;
      if (bytes.readUInt16LE(0) !== MAGIC) return;
      if (bytes.readUInt8(2) !== VERSION) return;
      if (bytes.readUInt8(3) !== WELCOME) return;

      welcome = {
        playerId: bytes.readUInt8(8),
        maxPlayers: bytes.readUInt8(9),
      };

      maybeResolve();
    });

    ws.once("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });

    ws.once("open", () => {
      opened = true;
      maybeResolve();
    });
  });
}

function waitForFourPlayerSnapshot(ws) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error("four-player snapshot timeout"));
    }, 15000);

    const onMessage = (data, isBinary) => {
      if (!isBinary) return;
      const bytes = Buffer.from(data);
      if (bytes.length < 18) return;
      if (bytes.readUInt16LE(0) !== MAGIC) return;
      if (bytes.readUInt8(2) !== VERSION) return;
      if (bytes.readUInt8(3) !== SNAPSHOT) return;
      const playerCount = bytes.readUInt8(16);
      if (playerCount !== 4) return;

      clearTimeout(timer);
      ws.off("message", onMessage);
      resolve(playerCount);
    };

    ws.on("message", onMessage);
  });
}

function makeInput(sequence, moveX, moveY) {
  const bytes = Buffer.alloc(26);
  bytes.writeUInt16LE(MAGIC, 0);
  bytes.writeUInt8(VERSION, 2);
  bytes.writeUInt8(PLAYER_INPUT, 3);
  bytes.writeUInt16LE(sequence, 4);
  bytes.writeUInt16LE(18, 6);
  bytes.writeUInt32LE(sequence, 8);
  bytes.writeUInt16LE(0, 12);
  bytes.writeInt16LE(moveX, 14);
  bytes.writeInt16LE(moveY, 16);
  bytes.writeInt16LE(0, 18);
  bytes.writeInt16LE(0, 20);
  bytes.writeUInt16LE(0, 22);
  bytes.writeUInt16LE(0, 24);
  return bytes;
}

function expectFifthRejected() {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(
      `${base}/v1/rooms/${room}?name=CI-5`,
      {
        headers: {
          "X-Xziel-Test-Key": testKey,
        },
      },
    );

    const timer = setTimeout(() => {
      ws.terminate();
      reject(new Error("fifth player was not rejected"));
    }, 10000);

    ws.once("open", () => {
      clearTimeout(timer);
      ws.close();
      reject(new Error("fifth player unexpectedly connected"));
    });

    ws.once("unexpected-response", (_request, response) => {
      const status = response.statusCode;
      response.resume();
      clearTimeout(timer);
      if (status !== 409) {
        reject(new Error(`unexpected fifth-player status ${status}`));
        return;
      }
      resolve(status);
    });

    ws.once("error", () => {
      // unexpected-response is the authoritative path; ignore the follow-up
      // socket error emitted by some ws versions after the 409 response.
    });
  });
}

const sockets = [];

try {
  const connected = await Promise.all(
    Array.from(
      { length: 4 },
      (_unused, index) => openPlayer(index),
    ),
  );

  sockets.push(
    ...connected.map((entry) => entry.ws),
  );

  const welcomes = connected.map(
    (entry) => entry.welcome,
  );

  const ids = welcomes
    .map((welcome) => welcome.playerId)
    .sort((a, b) => a - b);

  if (JSON.stringify(ids) !== JSON.stringify([0, 1, 2, 3])) {
    throw new Error(`unexpected player IDs: ${ids.join(",")}`);
  }

  if (!welcomes.every((welcome) => welcome.maxPlayers === 4)) {
    throw new Error("server did not advertise maxPlayers=4");
  }

  const snapshots = sockets.map((ws) =>
    waitForFourPlayerSnapshot(ws),
  );

  sockets.forEach((ws, index) => {
    ws.send(
      makeInput(
        index + 1,
        index % 2 === 0 ? 12000 : -12000,
        18000,
      ),
    );
  });

  await Promise.all(snapshots);
  await expectFifthRejected();

  console.log(
    `XZIEL_LIVE_4P_SMOKE_OK room=${room} ids=${ids.join(",")} fifth=409`,
  );
} finally {
  for (const ws of sockets) {
    try {
      ws.terminate();
    } catch {
      // Best-effort cleanup. CI must not keep the Node event loop alive.
    }
  }
}
