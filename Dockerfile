# Build spark image to run on Kubernetes
# See https://levelup.gitconnected.com/spark-on-kubernetes-3d822969f85b
# https://hub.docker.com/r/apache/spark

FROM apache/spark:4.1.1-scala2.13-java21-python3-r-ubuntu

# Run installation tasks as root
USER 0

# Ensure current patches
# Use minimal apt installs, add cloud GPG key securely, and clean caches
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl ca-certificates gnupg; \
    curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | gpg --dearmour -o /usr/share/keyrings/cloud.google.gpg; \
    apt-get update; \
    apt-get -y autoremove; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*;

# Specify the official Spark User, working directory, and entry point
WORKDIR /opt/spark/work-dir
ENV HOME=/opt/spark/work-dir

RUN chown -R spark ${APP_DIR}; \
    mkdir -p /tmp/spark-events; \
    chown -R spark /tmp/spark-events

ENV APP_DIR=/opt/spark/work-dir \
    PYTHON=python3 \
    PIP="python3 -m pip" \
    PIP_NO_CACHE_DIR=1

# Ensure `python` points to `python3` inside the image for scripts that expect `python`
RUN set -eux; \
    if command -v python >/dev/null 2>&1; then \
        echo "python already exists at $(command -v python)"; \
    elif command -v python3 >/dev/null 2>&1; then \
        ln -sf "$(command -v python3)" /usr/local/bin/python; \
    else \
        echo "python3 not found; please ensure Python 3 is available" >&2; \
        exit 1; \
    fi

# Preinstall dependencies
COPY requirements.txt ${APP_DIR}

# Install dependencies (simple, unpinned for this non-production build)
RUN set -eux; \
    ${PIP} install --upgrade pip; \
    ${PIP} install --no-cache-dir -r ${APP_DIR}/requirements.txt; \
    rm -f ${APP_DIR}/requirements.txt

# Copy local files to image (ordered so that more likely to change is copied later)
# Python script to start the program
COPY --chown=spark ./run.py ${APP_DIR}
COPY --chown=spark ./runpi.py ${APP_DIR}
COPY --chown=spark ./runjupyter.py ${APP_DIR}

# data will be local to image
COPY --chown=spark ./data ${APP_DIR}/data
# Python code (using module name for directory)
COPY --chown=spark k8spark ${APP_DIR}/k8spark

# Ensure owned by Spark
RUN chown -R spark:spark ${APP_DIR}

# Keep the image ENTRYPOINT configurable. For local runs override with `--entrypoint`.
# Examples:
#  docker run --entrypoint bash -ti --rm IMAGE_NAME
#  docker run --entrypoint python -p 8888:8888 --rm IMAGE_NAME runpi.py
# Also, yaml file driver.command can override ENTRYPOINT.

# Ensure the final image runs as the unprivileged Spark
USER spark
