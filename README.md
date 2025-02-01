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

## Open rtsp-stream within the container

Before everything else please create docker network:
```bash
docker network create -d bridge my-rtsp-network
```

First run container in interactive mode:
```bash
docker run \
  --rm \
  -it \
  --network=my-rtsp-network \
  --name mediamtx \
  -p 8554:8554 \
  bluenviron/mediamtx
```

Then - open rtsp stream (in a separate console):
```bash
docker run \
  --rm \
  -it \
  --network=my-rtsp-network \
  --name ffmpeg \
  -v ./data/videos:/data/videos \
  linuxserver/ffmpeg \
    -re -stream_loop -1 \
      -i /data/videos/meteorite-vertical.mp4 \
      -c copy -f rtsp rtsp://mediamtx:8554/mystream
```

Then - you can connect to the stream via VLC player
```bash
vlc --network-caching=50 rtsp://localhost:8554/mystream
```

You can also check if the gstreamer container is able to capture the stream:
```bash
docker run \
  -it \
  --rm \
  --network=my-rtsp-network \
  --name meteorite-catcher \
  -e GST_DEBUG=3 \
  -v ./data/videos:/data/videos \
  meteorite-catcher:latest \
      gst-launch-1.0 -e \
      rtspsrc location=rtsp://mediamtx:8554/mystream \
      ! rtph264depay ! h264parse \
      ! video/x-h264 \
      ! openh264dec \
      ! encodebin profile="mp4" \
      ! filesink location=/data/videos/camera.mp4
```

To see if you have all the elements needed for gstreamer to work
you can tun container in interactive mode
```bash
docker run \
  -it \
  --rm \
  --network=my-rtsp-network \
  --name meteorite-catcher \
  -e GST_DEBUG=3 \
  -v ./data/videos:/data/videos \
  --entrypoint "/bin/bash" \
  meteorite-catcher:latest
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

### Run script inside of docker container
```bash
docker run \
  -it \
  --rm \
  --name meteorite-catcher \
  -e GST_DEBUG=3 \
  --network=my-rtsp-network \
  -v ./data/videos:/data/videos \
  -v ./src:/code/src \
  meteorite-catcher:latest \
  python -m src.gstreamer.detector_controller
```
