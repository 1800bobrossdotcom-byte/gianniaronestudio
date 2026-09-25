set -e
read -a B < bounds.txt
for k in 0 1 2 3; do OPENCV_FOR_THREADS_NUM=1 python3 render_sem.py ${B[$k]} ${B[$((k+1))]} part$k.mp4 > log$k.txt 2>&1 & done
wait
printf "file 'part0.mp4'\nfile 'part1.mp4'\nfile 'part2.mp4'\nfile 'part3.mp4'\n" > parts.txt
ffmpeg -v error -y -f concat -safe 0 -i parts.txt -i song.mp3 -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest master.mp4
V="-vf hqdn3d=2:2:4:4 -c:v libx264 -preset slow -profile:v high -b:v 2450k -maxrate 5000k -bufsize 8000k -pix_fmt yuv420p -g 60"
ffmpeg -v error -y -i master.mp4 $V -pass 1 -passlogfile p2 -an -f mp4 /dev/null
ffmpeg -v error -y -i master.mp4 $V -pass 2 -passlogfile p2 -c:a aac -b:a 160k -movflags +faststart web.mp4
ffmpeg -v error -y -i web.mp4 -vf "select=not(mod(n\,286)),scale=320:-1,tile=6x5" -frames:v 1 fullsheet.png
echo END
