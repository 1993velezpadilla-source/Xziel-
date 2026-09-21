#!/usr/bin/env bash
set -euo pipefail

INPUT="${1:-Padre_Nuestro_La_Llorona_ENCHANTED_V3_DARKER_MASTER.wav}"
OUT_WAV="${2:-Padre_Nuestro_La_Llorona_ENCHANTED_V4_HORROR_MASTER.wav}"
OUT_OGG="${3:-Padre_Nuestro_La_Llorona_ENCHANTED_V4_HORROR_GAME.ogg}"

ffmpeg -y -hide_banner -loglevel warning -i "$INPUT" -filter_complex '
[0:a]aresample=48000,afftdn=nr=11:nf=-44:tn=1,highpass=f=65,lowpass=f=9400,asplit=7[main0][w1][w2][pre0][chap0][low0][choir0];
[main0]volume=1.0[main];
[w1]highpass=f=1550,lowpass=f=7600,acompressor=threshold=0.07:ratio=3.2:attack=5:release=130,rubberband=pitch=1.025,adelay=95|155,tremolo=f=0.19:d=0.30,volume=0.105[whisper1];
[w2]highpass=f=900,lowpass=f=5200,acompressor=threshold=0.08:ratio=2.7:attack=8:release=160,rubberband=pitch=0.955,adelay=230|315,tremolo=f=0.11:d=0.20,volume=0.075[whisper2];
[pre0]areverse,aecho=0.78:0.66:150|390|780:0.28|0.17|0.095,lowpass=f=6100,volume=0.11,areverse[pre];
[chap0]aecho=0.82:0.72:470|1010|2080|3720:0.22|0.14|0.085|0.04,highpass=f=170,lowpass=f=7600,volume=0.22[chapel];
[low0]highpass=f=50,lowpass=f=330,rubberband=pitch=0.875,adelay=65|105,volume=0.045[shadow];
[choir0]highpass=f=260,lowpass=f=1650,rubberband=pitch=0.76,adelay=510|640,tremolo=f=0.10:d=0.22,volume=0.028[choir];
[main][whisper1][whisper2][pre][chapel][shadow][choir]amix=inputs=7:normalize=0,loudnorm=I=-14.5:TP=-1.0:LRA=10,atrim=0:81.944,afade=t=out:st=80.65:d=1.294,alimiter=limit=0.94[out]
' -map '[out]' -ar 48000 -ac 2 -c:a pcm_s24le "$OUT_WAV"

ffmpeg -y -hide_banner -loglevel warning -i "$OUT_WAV"   -c:a libopus -b:a 96k -vbr on -application audio "$OUT_OGG"

echo "V4 rendered:"
ffprobe -v error -show_entries format=duration,size -of json "$OUT_WAV"
