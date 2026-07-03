FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_VERSION=2.4.1

WORKDIR /app

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

ARG POETRY_INSTALL_FLAGS="--only main"

COPY pyproject.toml poetry.lock* ./
RUN poetry install $POETRY_INSTALL_FLAGS --no-root

COPY assets ./assets
COPY notebooks ./notebooks
COPY reports ./reports
COPY src ./src
COPY scripts ./scripts
COPY README.md LICENSE ./

RUN poetry install $POETRY_INSTALL_FLAGS

EXPOSE 8050 8888

CMD ["gunicorn", "--bind", "0.0.0.0:8050", "revenue_forecast_dashboard.app:server"]
