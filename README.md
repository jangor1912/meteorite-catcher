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
docker run meteorite-catcher
```