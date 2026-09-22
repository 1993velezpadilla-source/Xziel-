#!/usr/bin/env bash
set -euo pipefail
# Rebuild Stained Shade V5 from the preserved V4 prayer master.
INPUT="${1:-Padre_Nuestro_La_Llorona_ENCHANTED_V4_HORROR_MASTER.wav}"
OUT_WAV="${2:-Stained_Shade_PRAYER_V5_ENCHANTED_HORROR_MASTER.wav}"
OUT_OGG="${3:-Stained_Shade_PRAYER_V5_ENCHANTED_HORROR_GAME.ogg}"

ffmpeg -y -hide_banner -loglevel warning -i "$INPUT" \
  -f lavfi -t 81.944 -i "sine=frequency=196:sample_rate=48000" \
  -f lavfi -t 81.944 -i "sine=frequency=293.665:sample_rate=48000" \
  -f lavfi -t 81.944 -i "sine=frequency=415.305:sample_rate=48000" \
  -filter_complex '
[0:a]aresample=48000,afftdn=nr=7:nf=-48:tn=1,highpass=f=60,lowpass=f=9300,asplit=7[m0][w1][w2][pre0][chap0][shade0][glassvoice0];
[m0]volume=0.98[main];
[w1]highpass=f=1350,lowpass=f=6500,acompressor=threshold=0.055:ratio=3.6:attack=4:release=140,rubberband=pitch=1.035,adelay=80|145,tremolo=f=0.17:d=0.24,volume=0.085[whisp_hi];
[w2]highpass=f=420,lowpass=f=3900,acompressor=threshold=0.065:ratio=3.1:attack=7:release=175,rubberband=pitch=0.935,adelay=185|275,chorus=0.45:0.55:28|41:0.18|0.12:0.22|0.31:0.20|0.27,volume=0.07[whisp_low];
[pre0]areverse,aecho=0.78:0.67:170|460|960:0.24|0.14|0.075,highpass=f=220,lowpass=f=5400,volume=0.085,areverse[pre];
[chap0]aecho=0.84:0.74:520|1120|2360|4210:0.20|0.13|0.07|0.035,highpass=f=150,lowpass=f=7200,volume=0.18[chapel];
[shade0]lowpass=f=310,rubberband=pitch=0.84,adelay=95|135,tremolo=f=0.10:d=0.16,volume=0.036[shade];
[glassvoice0]highpass=f=900,lowpass=f=2500,rubberband=pitch=1.19,adelay=330|470,volume=0.026[glassvoice];
[1:a]volume=0.0045,tremolo=f=0.10:d=0.78,aecho=0.75:0.62:850|1760:0.18|0.09[g1];
[2:a]volume=0.0032,tremolo=f=0.10:d=0.82,aecho=0.74:0.61:1030|2190:0.16|0.08[g2];
[3:a]volume=0.0024,tremolo=f=0.10:d=0.85,aecho=0.73:0.60:1270|2680:0.14|0.07[g3];
[main][whisp_hi][whisp_low][pre][chapel][shade][glassvoice][g1][g2][g3]amix=inputs=10:normalize=0,
acompressor=threshold=0.82:ratio=1.25:attack=12:release=220,
loudnorm=I=-14.8:TP=-1.0:LRA=11,
atrim=0:81.944,afade=t=out:st=80.55:d=1.394,alimiter=limit=0.94[out]
' -map '[out]' -ar 48000 -ac 2 -c:a pcm_s24le "$OUT_WAV"

ffmpeg -y -hide_banner -loglevel warning -i "$OUT_WAV" -c:a libopus -b:a 96k -vbr on -application audio "$OUT_OGG"
