#!/bin/sh

python -m src \
  --rtsp-url $RTSP_URL \
  --data-dir $DATA_DIR \
  --bbox-th $BBOX_THRESHOLD \
  --nms-th $NMS_THRESHOLD \
  --min-hits $MIN_HITS \
  --max-age $MAX_AGE
