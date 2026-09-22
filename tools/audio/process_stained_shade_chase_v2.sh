#!/usr/bin/env bash
set -euo pipefail

INPUT="${1:-stained_shade_chase_scream_AUDIO_ONLY.ogg}"
OUT_WAV="${2:-Stained_Shade_CHASE_SCREAM_V2_DARK_HORROR_MASTER.wav}"
OUT_OGG="${3:-Stained_Shade_CHASE_SCREAM_V2_DARK_HORROR_GAME.ogg}"

ffmpeg -y -hide_banner -loglevel warning -i "$INPUT" -filter_complex '
[0:a]aresample=48000,highpass=f=85,lowpass=f=9300,asplit=7[m0][d0][d1][pre0][chap0][air0][bite0];
[m0]acompressor=threshold=0.11:ratio=2.2:attack=3:release=120,volume=1.00[main];
[d0]asetrate=35520,aresample=48000,lowpass=f=2400,highpass=f=90,adelay=70|105,tremolo=f=0.18:d=0.18,volume=0.20[demonlow];
[d1]asetrate=43200,aresample=48000,highpass=f=500,lowpass=f=5200,adelay=145|215,chorus=0.42:0.55:24|37:0.16|0.12:0.20|0.28:0.18|0.24,volume=0.115[demonmid];
[pre0]areverse,aecho=0.82:0.70:120|310|690:0.32|0.18|0.09,highpass=f=240,lowpass=f=6000,volume=0.16,areverse[pre];
[chap0]aecho=0.84:0.74:420|910|1710|3200:0.26|0.16|0.09|0.045,highpass=f=150,lowpass=f=7300,volume=0.24[chapel];
[air0]highpass=f=1800,lowpass=f=6800,adelay=260|340,tremolo=f=0.13:d=0.30,volume=0.055[air];
[bite0]highpass=f=2200,lowpass=f=9000,acompressor=threshold=0.06:ratio=4:attack=1:release=70,volume=0.14[bite];
[main][demonlow][demonmid][pre][chapel][air][bite]amix=inputs=7:normalize=0,
acompressor=threshold=0.86:ratio=1.3:attack=4:release=160,
alimiter=limit=0.93,
apad=pad_dur=2.3,
afade=t=out:st=6.4:d=1.2[out]
' -map '[out]' -ar 48000 -ac 2 -c:a pcm_s24le "$OUT_WAV"

ffmpeg -y -hide_banner -loglevel warning -i "$OUT_WAV" -c:a libopus -b:a 112k -vbr on -application audio "$OUT_OGG"
