#!/usr/bin/env python3
from pathlib import Path
import json, subprocess

OUT = Path("dist/llorona-search")
OUT.mkdir(parents=True, exist_ok=True)

TEXT = (
    "Mis hijos... ¿dónde están mis hijos? "
    "Mis hijos... yo los escucho. "
    "¿Dónde están? "
    "No se escondan de mí... "
    "Mis hijos... ¿dónde están mis hijos?"
)

from melo.api import TTS
model = TTS(language="ES", device="cpu")
speaker_ids = model.hps.data.spk2id

raw = OUT / "llorona_mis_hijos_raw.wav"
model.tts_to_file(TEXT, speaker_ids["ES"], str(raw), speed=0.72)

# Build three distinct passes from the same performance so repetition feels intentional,
# not like a simple hard loop.
p1 = OUT / "pass1.wav"
p2 = OUT / "pass2.wav"
p3 = OUT / "pass3.wav"

subprocess.run([
    "ffmpeg","-y","-hide_banner","-loglevel","warning","-i",str(raw),
    "-af","aresample=48000,highpass=f=95,lowpass=f=9000,acompressor=threshold=0.12:ratio=2.3:attack=8:release=180,aecho=0.80:0.66:430|980|1820:0.26|0.16|0.09",
    "-ar","48000","-ac","2",str(p1)
], check=True)

subprocess.run([
    "ffmpeg","-y","-hide_banner","-loglevel","warning","-i",str(raw),
    "-af","aresample=48000,highpass=f=120,lowpass=f=7200,rubberband=pitch=0.965,adelay=180|260,aecho=0.82:0.70:560|1230|2400:0.28|0.17|0.08,volume=0.92",
    "-ar","48000","-ac","2",str(p2)
], check=True)

subprocess.run([
    "ffmpeg","-y","-hide_banner","-loglevel","warning","-i",str(raw),
    "-af","aresample=48000,highpass=f=180,lowpass=f=6500,rubberband=pitch=1.03,adelay=95|150,aecho=0.78:0.64:350|780|1600:0.24|0.14|0.07,volume=0.86",
    "-ar","48000","-ac","2",str(p3)
], check=True)

# Concatenate with breathing room so the manifestation has time to move/search.
sil = OUT / "silence.wav"
subprocess.run([
    "ffmpeg","-y","-hide_banner","-loglevel","warning",
    "-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-t","2.2","-c:a","pcm_s16le",str(sil)
], check=True)

lst = OUT / "concat.txt"
lst.write_text(
    "\n".join([
        f"file '{p1.resolve()}'",
        f"file '{sil.resolve()}'",
        f"file '{p2.resolve()}'",
        f"file '{sil.resolve()}'",
        f"file '{p3.resolve()}'",
    ]) + "\n",
    encoding="utf-8"
)

looped = OUT / "llorona_mis_hijos_SEARCH_LOOP_48k.wav"
subprocess.run([
    "ffmpeg","-y","-hide_banner","-loglevel","warning","-f","concat","-safe","0","-i",str(lst),
    "-af","highpass=f=75,lowpass=f=9200,alimiter=limit=0.94",
    "-ar","48000","-ac","2","-c:a","pcm_s24le",str(looped)
], check=True)

ogg = OUT / "llorona_mis_hijos_SEARCH_LOOP_48k.ogg"
subprocess.run([
    "ffmpeg","-y","-hide_banner","-loglevel","warning","-i",str(looped),
    "-c:a","libopus","-b:a","96k","-vbr","on",str(ogg)
], check=True)

probe = subprocess.check_output([
    "ffprobe","-v","error","-show_entries","format=duration",
    "-of","default=nw=1:nk=1",str(looped)
], text=True).strip()

manifest = {
    "engine":"MeloTTS",
    "language":"ES",
    "speed":0.72,
    "source_model":"myshell-ai/MeloTTS@209145371cff8fc3bd60d7be902ea69cbdb7965a",
    "text":TEXT,
    "duration_s":float(probe),
    "wav":looped.name,
    "ogg":ogg.name,
    "role":"La Llorona SEARCHING/WAILING manifestation; prayer moved to Stained Shade.",
    "notes":[
        "Three differently processed passes from the same original performance.",
        "Manifestation lifetime should follow actual audio EOF.",
        "Interrupt immediately on dead-child discovery or other explicit rage trigger."
    ]
}
(OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(manifest,ensure_ascii=False,indent=2))
