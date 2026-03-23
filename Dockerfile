FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONWARNINGS=ignore::SyntaxWarning \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_SYSTEM_PYTHON=1 \
    USING_LIBSUMO=true \
    FLASK_APP=main_complete_integration.py \
    FLASK_HOST=0.0.0.0 \
    PORT=5000 \
    SUMO_HOME=/usr/local/lib/python3.12/site-packages/sumo

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libatomic1 \
    libgl1 \
    libx11-6 \
    libxext6 \
    libxrender1 \
    libsm6 \
    libstdc++6 \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

COPY requirements.lock.txt requirements.txt pyproject.toml ./
RUN uv pip install --system -r requirements.lock.txt

COPY . .

RUN if [ -f .env.example ] && [ ! -f .env ]; then cp .env.example .env; fi

EXPOSE 5000

CMD ["python", "main_complete_integration.py"]
