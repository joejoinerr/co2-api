FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 POETRY_HOME="/opt/poetry"

RUN apt update && apt install -y curl build-essential
RUN curl -sSL https://install.python-poetry.org | python3 - --version 1.7.1
ENV PATH="${PATH}:${POETRY_HOME}/bin"

WORKDIR /code
COPY poetry.lock pyproject.toml /code/

RUN poetry config virtualenvs.in-project true \
    && poetry install --no-root --no-dev --no-interaction --no-ansi

COPY ./src /code/src
WORKDIR /code/src

ENTRYPOINT poetry run uvicorn main:app --host 0.0.0.0 --port ${PORT:-80}
