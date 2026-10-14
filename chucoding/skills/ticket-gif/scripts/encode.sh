#!/usr/bin/env bash
# 녹화 프레임 폴더를 확인용 프레임 시트와 GIF로 변환
# 사용법: encode.sh <ffmpeg 경로> <프레임 폴더> <출력 GIF 경로>
set -euo pipefail

FF="$1"
OUT="$2"
GIF="$3"

# 첫 프레임 크기 확인(1440×900 기대)
sips -g pixelWidth -g pixelHeight "$OUT/f0000.jpg" | tail -2

# 장면 확인용 프레임 시트(4×3)
"$FF" -y -loglevel error -start_number 1 -i "$OUT/f%04d.jpg" -frames:v 12 \
  -vf "scale=360:-1,tile=4x3" "$OUT/sheet.png"
echo "sheet: $OUT/sheet.png"

# GIF 인코딩. concat 목록의 duration으로 실제 속도 유지, 960×600, 무한 반복
(cd "$OUT" && "$FF" -y -loglevel error -f concat -safe 0 -i list.txt \
  -vf "fps=25,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle" \
  -loop 0 "$GIF")
ls -l "$GIF"
