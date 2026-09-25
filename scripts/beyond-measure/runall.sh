set -e
read -a B < bounds.txt
for k in 0 1 2 3; do OPENCV_FOR_THREADS_NUM=1 python3 render.py ${B[$k]} ${B[$((k+1))]} part$k.mp4 > log$k.txt 2>&1 & done
wait
printf "file 'part0.mp4'\nfile 'part1.mp4'\nfile 'part2.mp4'\nfile 'part3.mp4'\n" > parts.txt
ffmpeg -v error -y -f concat -safe 0 -i parts.txt -i song.mp3 -map 0:v -map 1:a -c:v copy -c:a aac -b:a 256k -shortest master.mp4
echo DONE
