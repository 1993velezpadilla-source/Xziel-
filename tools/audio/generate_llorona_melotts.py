#!/usr/bin/env python3
from pathlib import Path
import json
import subprocess

OUT = Path("dist/llorona-melotts")
OUT.mkdir(parents=True, exist_ok=True)

PRAYER = (
    "Padre nuestro, que estás en el cielo... "
    "Santificado sea tu nombre. "
    "Venga a nosotros tu reino. "
    "Hágase tu voluntad, en la tierra como en el cielo. "
    "Danos hoy nuestro pan de cada día. "
    "Perdona nuestras ofensas, como también nosotros perdonamos a los que nos ofenden. "
    "No nos dejes caer en la tentación... "
    "y líbranos del mal. "
    "Amén."
)

from melo.api import TTS

model = TTS(language="ES", device="cpu")
speaker_ids = model.hps.data.spk2id

raw = OUT / "llorona_prayer_melo_raw.wav"
model.tts_to_file(PRAYER, speaker_ids["ES"], str(raw), speed=0.86)

selected = OUT / "llorona_prayer_SELECTED_48k.wav"
ogg = OUT / "llorona_prayer_SELECTED_48k.ogg"

graph = (
    "[0:a]aresample=48000,highpass=f=90,lowpass=f=9500,"
    "acompressor=threshold=0.18:ratio=2.1:attack=10:release=150,"
    "asplit=4[m][g1][g2][rev];"
    "[m]volume=1.00[main];"
    "[g1]asetrate=46800,aresample=48000,adelay=145|205,"
    "lowpass=f=5200,volume=0.11[ghostlow];"
    "[g2]asetrate=49350,aresample=48000,adelay=95|130,"
    "highpass=f=260,lowpass=f=7600,volume=0.065[ghosthigh];"
    "[rev]aecho=0.80:0.68:380|830|1550|2700:0.30|0.20|0.12|0.07,"
    "lowpass=f=7200,volume=0.52[space];"
    "[main][ghostlow][ghosthigh][space]amix=inputs=4:normalize=0,"
    "alimiter=limit=0.94,afade=t=in:st=0:d=0.35[out]"
)

subprocess.run([
    "ffmpeg","-y","-hide_banner","-loglevel","warning",
    "-i",str(raw),
    "-filter_complex",graph,
    "-map","[out]","-ar","48000","-ac","2","-c:a","pcm_s24le",
    str(selected)
], check=True)

subprocess.run([
    "ffmpeg","-y","-hide_banner","-loglevel","warning",
    "-i",str(selected),"-c:a","libopus","-b:a","96k","-vbr","on",str(ogg)
], check=True)

manifest = {
    "engine": "MeloTTS",
    "language": "ES",
    "speed": 0.86,
    "source_model": "myshell-ai/MeloTTS@209145371cff8fc3bd60d7be902ea69cbdb7965a",
    "text": PRAYER,
    "selected_wav": selected.name,
    "selected_ogg": ogg.name,
    "notes": [
        "Original Spanish TTS base, not a clone of the viral La Llorona performer.",
        "Horror treatment uses restrained delayed pitch doubles and long echoes.",
        "48 kHz stereo / 24-bit WAV master plus Opus OGG game asset."
    ]
}
(OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(manifest,ensure_ascii=False,indent=2))
