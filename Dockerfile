FROM python:3.12 as base

LABEL authors="jan.gorazda"

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

# Copy only requirements to cache them in docker layer
WORKDIR /code
COPY poetry.lock pyproject.toml /code/

FROM base as prod

# Project initialization with only main packages:
RUN poetry install --only=main --no-interaction --no-ansi

# Creating folders, and files for a project:
COPY ./src /code/src

ENTRYPOINT ["python", "-m", "src"]

FROM prod as dev

# Project initialization with all dependencies:
RUN poetry install --no-interaction --no-ansi

# Creating folders, and files for a project:
COPY . /code

ENTRYPOINT ["pytest"]
