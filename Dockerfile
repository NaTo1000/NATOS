# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 – dependency builder
#   Install only production packages into a dedicated prefix so the final
#   image contains no build tooling.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Copy dependency manifest first (maximises Docker layer cache hit rate)
COPY requirements.txt .

# Install into a custom location so it is trivially copied in the next stage
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 – runtime image
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Keep the image up-to-date and remove the apt cache in one layer
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user so the process does not run as root
RUN useradd --create-home --shell /bin/bash natos

WORKDIR /app

# Copy pre-built packages from the builder stage
COPY --from=builder /install /usr/local

# Copy application source
COPY --chown=natos:natos . .

# ── Credentials & configuration ───────────────────────────────────────────────
# NEVER hard-code passwords or secrets here.
# Supply runtime values through:
#   • a .env file loaded by docker-compose  (see docker-compose.yml)
#   • explicit -e / --env-file flags on `docker run`
#   • Docker Swarm / Kubernetes secrets mounted as environment variables
#
# The variables below show the expected names with safe, empty defaults.
# Override every variable that matters for your deployment.
ENV NATOS_SECRET_KEY="" \
    NATOS_USERNAME="" \
    NATOS_PASSWORD="" \
    NATOS_USE_SSL="false" \
    NATOS_ACCEPT_EULA="false" \
    ANTHROPIC_API_KEY=""

EXPOSE 5000

USER natos

CMD ["python", "app.py"]
