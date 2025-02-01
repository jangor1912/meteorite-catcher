FROM nvcr.io/nvidia/deepstream:7.0-samples-multiarch as base

LABEL authors="jan.gorazda"

RUN apt-get update && apt-get -y --no-install-recommends install \
    sudo \
    vim \
    wget \
    build-essential \
    pkg-config \
    python3.10 \
    python3-pip \
    python3.10-dev \
    python3.10-venv

RUN apt-get -y --no-install-recommends install \
    git \
    cmake \
    autoconf \
    automake \
    libtool \
    gstreamer-1.0 \
    gstreamer1.0-dev \
    libgstreamer1.0-0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-tools \
    gstreamer1.0-x \
    gstreamer1.0-alsa \
    gstreamer1.0-gl \
    gstreamer1.0-gtk3 \
    gstreamer1.0-qt5 \
    gstreamer1.0-pulseaudio \
    libglib2.0-dev \
    libglib2.0-dev-bin \
    python-gi-dev \
    python3-gi \
    python3-gst-1.0 \
    libgirepository1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libcairo2-dev \
    gir1.2-gstreamer-1.0 \
    gobject-introspection \
    gir1.2-gtk-3.0

# RTSP server for testing purposes
RUN apt-get install -y --no-install-recommends \
    libgstrtspserver-1.0-0 \
    gstreamer1.0-rtsp \
    libgirepository1.0-dev \
    gobject-introspection \
    gir1.2-gst-rtsp-server-1.0

# FFmpeg for software decoding libraries
RUN apt-get install -y --no-install-recommends \
    ffmpeg


ARG gstreamer_python_version=c8d4e04e1cdeb3b284641b981afcf304f50480db
RUN mkdir /github_tmp
RUN git clone https://github.com/jackersson/gstreamer-python.git /github_tmp/gstreamer-python &&\
    cd /github_tmp/gstreamer-python  &&\
    git checkout $gstreamer_python_version && \
    git submodule update --init --progress --depth=1

RUN pip3 install \
    --no-input \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --trusted-host github.com \
    -r /github_tmp/gstreamer-python/requirements.txt
RUN pip3 install \
    --no-input \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    --trusted-host github.com \
    /github_tmp/gstreamer-python/.


ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    # Poetry's configuration:
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR='/var/cache/pypoetry' \
    POETRY_HOME='/usr/local' \
    POETRY_VERSION=1.8.3

# System deps:
RUN curl -sSL https://install.python-poetry.org | python3 -

# Install Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy only requirements to cache them in docker layer
WORKDIR /code
COPY poetry.lock pyproject.toml /code/

FROM base as prod

# Project initialization with only main packages:
RUN poetry install --only=main --no-interaction --no-ansi

# Creating folders, and files for a project:
COPY ./src /code/src

CMD ["python", "-m", "src"]

FROM prod as dev

# Project initialization with all dependencies:
RUN poetry install --no-interaction --no-ansi

# Creating folders, and files for a project:
COPY ./dev /code/dev
COPY ./tests /code/tests

CMD ["pytest"]
