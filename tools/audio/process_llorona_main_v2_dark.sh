#!/usr/bin/env bash
set -euo pipefail
INPUT="${1:-llorona_main_user_selected_v1.ogg}"
OUT_WAV="${2:-La_Llorona_MAIN_V2_DARK_HORROR_MASTER.wav}"
OUT_OGG="${3:-La_Llorona_MAIN_V2_DARK_HORROR_GAME.ogg}"

ffmpeg -y -hide_banner -loglevel warning -i "$INPUT" -filter_complex '
[0:a]aresample=48000,afftdn=nr=5:nf=-48:tn=1,highpass=f=75,lowpass=f=9200,asplit=7[m0][low0][mid0][pre0][far0][air0][cry0];
[m0]acompressor=threshold=0.10:ratio=2.1:attack=5:release=150,volume=1.0[main];
[low0]asetrate=38400,aresample=48000,lowpass=f=2500,highpass=f=90,adelay=85|125,tremolo=f=0.13:d=0.18,volume=0.16[low];
[mid0]asetrate=44640,aresample=48000,highpass=f=450,lowpass=f=5200,adelay=190|260,chorus=0.4:0.5:25|38:0.16|0.11:0.2|0.28:0.17|0.23,volume=0.09[mid];
[pre0]areverse,aecho=0.80:0.68:160|430|920:0.26|0.15|0.08,highpass=f=220,lowpass=f=6100,volume=0.11,areverse[pre];
[far0]aecho=0.84:0.74:520|1180|2450|4100:0.20|0.12|0.065|0.032,highpass=f=140,lowpass=f=6900,volume=0.18[far];
[air0]highpass=f=1800,lowpass=f=7000,adelay=310|430,tremolo=f=0.11:d=0.24,volume=0.04[air];
[cry0]asetrate=47040,aresample=48000,highpass=f=900,lowpass=f=4200,adelay=620|760,aecho=0.76:0.62:980|2100:0.17|0.08,volume=0.055[cry];
[main][low][mid][pre][far][air][cry]amix=inputs=7:normalize=0,acompressor=threshold=0.86:ratio=1.25:attack=7:release=180,alimiter=limit=0.93,atrim=0:83.987,afade=t=out:st=82.7:d=1.287[out]
' -map '[out]' -ar 48000 -ac 2 -c:a pcm_s24le "$OUT_WAV"

ffmpeg -y -hide_banner -loglevel warning -i "$OUT_WAV" -c:a libopus -b:a 112k -vbr on -application audio "$OUT_OGG"
