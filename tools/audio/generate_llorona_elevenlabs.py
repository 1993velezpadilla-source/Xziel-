#!/usr/bin/env python3
"""Generate original La Llorona-style game voice assets with ElevenLabs.

This script does NOT clone a specific performer. It creates a new designed voice
with grief/wailing/whisper characteristics, then renders gameplay variants.

Required:
  ELEVENLABS_API_KEY in the environment
  ffmpeg on PATH
"""

from __future__ import annotations

import base64
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.elevenlabs.io/v1"
OUT = pathlib.Path(os.environ.get("LLORONA_OUT_DIR", "dist/llorona-elevenlabs"))
API_KEY = os.environ.get("ELEVENLABS_API_KEY", "").strip()

VOICE_DESCRIPTION = (
    "Native Latin American Spanish female, around 35 to 45 years old. "
    "A deeply grieving supernatural mother inspired by Latin American ghost folklore, "
    "but an original character rather than an imitation of any existing performer. "
    "Her voice remains recognizably human: exhausted from crying, breath trembling, "
    "occasional voice cracks, long unstable vowels, restrained sobs, intimate whispers "
    "that can suddenly break into anguished wails. Dark cinematic horror, believable "
    "and emotionally devastated. Avoid nasal tone, cartoon witch acting, monster growls, "
    "robotic cadence, or word-by-word delivery. Prayer passages must flow naturally "
    "as complete phrases."
)

PREVIEW_TEXT = (
    "[sorrowful] [crying] ¿Dónde están mis hijos? Llevo tanto tiempo buscándolos. "
    "[whispers] Escucho sus pasos, pero cuando vuelvo la mirada ya no están. "
    "[sighs] Padre nuestro que estás en el cielo... no permitas que vuelva a perderlos. "
    "[crying] Mis hijos... mis hijos..."
)

VARIANTS = {
    "llorona_prayer": (
        "[whispers] [sorrowful] Padre nuestro que estás en el cielo, "
        "santificado sea tu nombre; venga a nosotros tu reino; hágase tu voluntad, "
        "en la tierra como en el cielo. [sighs] Danos hoy nuestro pan de cada día; "
        "perdona nuestras ofensas, como también nosotros perdonamos a los que nos ofenden; "
        "[crying] no nos dejes caer en la tentación y líbranos del mal. [whispers] Amén."
    ),
    "llorona_mis_hijos": (
        "[crying] Mis hijos... [sighs] ¿Dónde están mis hijos? "
        "[whispers] Yo los escucho... yo sé que están aquí. "
        "[crying] Mis hijos... mis hijos... [shouts] ¡MIS HIJOS!"
    ),
    "llorona_rage_trigger": (
        "[crying] Mi hijo... [gasps] mi niño... "
        "[whispers] ¿Qué le hicieron? [sorrowful] ¿Qué le hicieron a mi hijo? "
        "[shouts] ¡MI HIJO! [shouts] ¡DEVUÉLVANME A MI HIJO!"
    ),
}

def request_json(path: str, payload: dict, *, query: dict | None = None) -> dict:
    url = API + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "xi-api-key": API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Xziel-Llorona-Audio-Pipeline/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ElevenLabs HTTP {e.code} for {path}: {detail}") from e
    return json.loads(body.decode("utf-8"))

def request_audio(path: str, payload: dict, output_path: pathlib.Path) -> None:
    url = API + path + "?" + urllib.parse.urlencode({"output_format": "mp3_44100_128"})
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "xi-api-key": API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
            "User-Agent": "Xziel-Llorona-Audio-Pipeline/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            output_path.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ElevenLabs HTTP {e.code} for {path}: {detail}") from e

def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)

def process_audio(name: str, raw_mp3: pathlib.Path) -> list[str]:
    dry_wav = OUT / f"{name}_dry_48k.wav"
    game_wav = OUT / f"{name}_game_48k.wav"
    game_ogg = OUT / f"{name}_game_48k.ogg"

    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(raw_mp3), "-ar", "48000", "-ac", "2",
        "-c:a", "pcm_s24le", str(dry_wav),
    ])

    filter_graph = (
        "[0:a]aresample=48000,highpass=f=90,lowpass=f=9000,asplit=3[d][g1][g2];"
        "[d]aecho=0.82:0.72:420|980|1900:0.28|0.18|0.10[drywet];"
        "[g1]asetrate=47280,aresample=48000,adelay=110|145,volume=0.10[ghost1];"
        "[g2]asetrate=48864,aresample=48000,adelay=175|135,volume=0.07[ghost2];"
        "[drywet][ghost1][ghost2]amix=inputs=3:normalize=0,"
        "alimiter=limit=0.94[out]"
    )
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(raw_mp3),
        "-filter_complex", filter_graph,
        "-map", "[out]", "-ar", "48000", "-ac", "2",
        "-c:a", "pcm_s24le", str(game_wav),
    ])
    run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-i", str(game_wav),
        "-c:a", "libopus", "-b:a", "96k", "-vbr", "on",
        str(game_ogg),
    ])
    return [dry_wav.name, game_wav.name, game_ogg.name]

def main() -> int:
    if not API_KEY:
        print("ELEVENLABS_API_KEY is missing.", file=sys.stderr)
        return 2

    OUT.mkdir(parents=True, exist_ok=True)

    design = request_json(
        "/text-to-voice/design",
        {
            "voice_description": VOICE_DESCRIPTION,
            "model_id": "eleven_ttv_v3",
            "text": PREVIEW_TEXT,
            "auto_generate_text": False,
        },
        query={"output_format": "mp3_44100_128"},
    )

    previews = design.get("previews") or []
    if not previews:
        raise RuntimeError("Voice Design returned no previews.")

    preview_meta = []
    for i, preview in enumerate(previews):
        audio = base64.b64decode(preview["audio_base_64"])
        p = OUT / f"voice_preview_{i}.mp3"
        p.write_bytes(audio)
        preview_meta.append({
            "index": i,
            "generated_voice_id": preview.get("generated_voice_id"),
            "duration_secs": preview.get("duration_secs", 0),
            "file": p.name,
        })

    chosen_index, chosen_preview = max(
        enumerate(previews),
        key=lambda pair: float(pair[1].get("duration_secs") or 0.0),
    )

    voice = request_json(
        "/text-to-voice",
        {
            "voice_name": "Xziel La Llorona",
            "voice_description": VOICE_DESCRIPTION,
            "generated_voice_id": chosen_preview["generated_voice_id"],
            "labels": {
                "project": "Xziel",
                "character": "La Llorona",
                "language": "es",
                "use_case": "game_character",
            },
        },
    )
    voice_id = voice["voice_id"]

    rendered = {}
    for name, text in VARIANTS.items():
        raw = OUT / f"{name}_raw.mp3"
        request_audio(
            f"/text-to-speech/{urllib.parse.quote(voice_id)}",
            {
                "text": text,
                "model_id": "eleven_v3",
                "voice_settings": {"stability": 0.32},
            },
            raw,
        )
        rendered[name] = {
            "text": text,
            "raw": raw.name,
            "processed": process_audio(name, raw),
        }

    manifest = {
        "voice_id": voice_id,
        "voice_name": voice.get("name", "Xziel La Llorona"),
        "voice_description": VOICE_DESCRIPTION,
        "selection_rule": "longest Voice Design v3 preview",
        "chosen_preview_index": chosen_index,
        "previews": preview_meta,
        "variants": rendered,
        "notes": [
            "Original designed voice; does not clone a specific performer.",
            "Dry 48 kHz WAV retained for engine-side spatialization.",
            "Game WAV/OGG include restrained ghost doubles and long echo.",
        ],
    }
    (OUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
