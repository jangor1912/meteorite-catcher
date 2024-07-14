# Meteorite Catcher
Project that detects meteorites on videos from CCTV cameras

## Build Docker Image

### For Production
```bash
 docker build --tag meteorite-catcher . --target=prod
```

### For Development
```bash
 docker build --tag meteorite-catcher . --target=dev
```

## Run Docker Image
```bash
docker run --rm --name meteorite-catcher meteorite-catcher
```

### In interactive mode
```bash
docker run \
  -it \
  --entrypoint "/bin/bash" \
  --rm \
  -v ./data:/data \
  --name meteorite-catcher \
  meteorite-catcher
```

## Test if gstreamer is working
```bash
gst-launch-1.0 \
  filesrc location=/data/videos/meteorite-vertical.mp4 \
  ! decodebin \
  ! videoconvert \
  ! jpegenc \
  ! multifilesink location=/data/images/gstreamer-test/%05d.jpg
```

## Useful commands

### Convert video to frames
```bash
ffmpeg -r 1 -i videos/some-video.mp4 -r 1 "images/some-video/$filename%03d.png"
```

### Convert frames to video
```bash
ffmpeg -framerate 25 -pattern_type glob -i '*.png' \
  -c:v libx264 -pix_fmt yuv420p out.mp4
```