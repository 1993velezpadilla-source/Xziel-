export const MAX_PLAYERS = 4;
export const MAX_REPLICATED_ZOMBIES = 24;
export const MAGIC = 0x5a58;
export const VERSION = 1;
export const HEADER_BYTES = 8;
export const MAX_PACKET_BYTES = 1200;
export const SERVER_TICK_HZ = 20;
export const SNAPSHOT_INTERVAL_MS = 1000 / SERVER_TICK_HZ;

export enum MessageType {
  Invalid = 0,
  Hello = 1,
  Welcome = 2,
  PlayerInput = 3,
  Snapshot = 4,
  GameplayEvent = 5,
  Ping = 6,
  Pong = 7,
  Disconnect = 8,
}

export interface PlayerInput {
  sequence: number;
  clientTick: number;
  buttons: number;
  moveX: number;
  moveY: number;
  yawCentidegrees: number;
  pitchCentidegrees: number;
  fireSequence: number;
  interactId: number;
}

export interface PlayerState {
  playerId: number;
  flags: number;
  health: number;
  points: number;
  xMillimeters: number;
  yMillimeters: number;
  zMillimeters: number;
  yawCentidegrees: number;
  pitchCentidegrees: number;
  weaponId: number;
  ammo: number;
  lastInputSequence: number;
  lastSeenMs: number;
}

export function decodePlayerInput(data: ArrayBuffer): PlayerInput | null {
  if (data.byteLength !== 26 || data.byteLength > MAX_PACKET_BYTES) return null;

  const view = new DataView(data);
  if (
    view.getUint16(0, true) !== MAGIC ||
    view.getUint8(2) !== VERSION ||
    view.getUint8(3) !== MessageType.PlayerInput ||
    view.getUint16(6, true) !== 18
  ) {
    return null;
  }

  return {
    sequence: view.getUint16(4, true),
    clientTick: view.getUint32(8, true),
    buttons: view.getUint16(12, true),
    moveX: view.getInt16(14, true),
    moveY: view.getInt16(16, true),
    yawCentidegrees: view.getInt16(18, true),
    pitchCentidegrees: view.getInt16(20, true),
    fireSequence: view.getUint16(22, true),
    interactId: view.getUint16(24, true),
  };
}

export function encodeWelcome(playerId: number, serverTick: number): ArrayBuffer {
  const buffer = new ArrayBuffer(14);
  const view = new DataView(buffer);
  view.setUint16(0, MAGIC, true);
  view.setUint8(2, VERSION);
  view.setUint8(3, MessageType.Welcome);
  view.setUint16(4, 0, true);
  view.setUint16(6, 6, true);
  view.setUint8(8, playerId);
  view.setUint8(9, MAX_PLAYERS);
  view.setUint32(10, serverTick, true);
  return buffer;
}

export function encodeSnapshot(
  sequence: number,
  serverTick: number,
  round: number,
  players: readonly PlayerState[],
): ArrayBuffer {
  const count = Math.min(players.length, MAX_PLAYERS);
  const payloadBytes = 10 + count * 28;
  const buffer = new ArrayBuffer(HEADER_BYTES + payloadBytes);
  const view = new DataView(buffer);

  view.setUint16(0, MAGIC, true);
  view.setUint8(2, VERSION);
  view.setUint8(3, MessageType.Snapshot);
  view.setUint16(4, sequence & 0xffff, true);
  view.setUint16(6, payloadBytes, true);

  view.setUint32(8, serverTick >>> 0, true);
  view.setUint16(12, 0, true);
  view.setUint16(14, round & 0xffff, true);
  view.setUint8(16, count);
  view.setUint8(17, 0);

  let offset = 18;
  for (let i = 0; i < count; ++i) {
    const p = players[i]!;
    view.setUint8(offset + 0, p.playerId);
    view.setUint8(offset + 1, p.flags);
    view.setUint16(offset + 2, p.health, true);
    view.setUint32(offset + 4, p.points >>> 0, true);
    view.setInt32(offset + 8, p.xMillimeters, true);
    view.setInt32(offset + 12, p.yMillimeters, true);
    view.setInt32(offset + 16, p.zMillimeters, true);
    view.setInt16(offset + 20, p.yawCentidegrees, true);
    view.setInt16(offset + 22, p.pitchCentidegrees, true);
    view.setUint16(offset + 24, p.weaponId, true);
    view.setUint16(offset + 26, p.ammo, true);
    offset += 28;
  }

  return buffer;
}
