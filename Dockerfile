# Build spark image to run on Kubernetes
# See https://levelup.gitconnected.com/spark-on-kubernetes-3d822969f85b
# https://hub.docker.com/r/datamechanics/spark
# Currently is: 3.2.1-hadoop-3.3.1-java-8-scala-2.12-python-3.8-dm17
FROM datamechanics/spark:3.2-latest

# Run installation tasks as root
USER 0

# Ensure current patches (standard security practice)
# https://serverfault.com/questions/906972/the-following-signatures-couldnt-be-verified-because-the-public-key-is-not-avai
RUN curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add -\
    && apt update \
    && apt --yes upgrade

# Specify the official Spark User, working directory, and entry point
WORKDIR /opt/spark/work-dir

# Offical UID for spark process
ARG spark_uid=185

# Specify the user info for spark_uid
RUN useradd -d /home/sparkuser -ms /bin/bash -u ${spark_uid} sparkuser \
    && chown -R sparkuser /opt/spark/work-dir \
    && mkdir /tmp/spark-events \
    && chown -R sparkuser /tmp/spark-events

# app dependencies AND path to openjdk11
ENV APP_DIR=/opt/spark/work-dir \
    PYTHON=python3 \
    PIP=pip3

# Preinstall dependencies
COPY requirements.txt ${APP_DIR}

# Install dependencies (conda is too slow)
RUN ${PIP}  install --upgrade pip \
    && ${PIP} install --no-cache-dir -r ${APP_DIR}/requirements.txt \
    && rm -f ${APP_DIR}/requirements.txt

USER ${spark_uid}

# Copy local files to image (ordered so that more likely to change is copied later)
# Python script to start the program
COPY --chown=sparkuser ./run.py ${APP_DIR}
COPY --chown=sparkuser ./runpi.py ${APP_DIR}
COPY --chown=sparkuser ./runjupyter.py ${APP_DIR}
# data will be local to image
COPY --chown=sparkuser ./data ${APP_DIR}/data
# Python code (using module name for directory)
COPY --chown=sparkuser k8spark ${APP_DIR}/k8spark

# Ensure owned by Spark
RUN chown -R sparkuser:sparkuser ${APP_DIR}/*

# https://stackoverflow.com/questions/41694329/docker-run-override-entrypoint-with-shell-script-which-accepts-arguments
# Example override for docker run: docker run --entrypoint bash -ti --rm IMAGE_NAME
# Example override for docker run: docker run --entrypoint python -p 8888:8888 --rm IMAGE_NAME runpi.py
# DO OVERRIDE entrypoint defined in datamechanics/spark when running command Docker
# DO NOT OVERRIDE entrypoint when running on kubernetes cluster (comment out)
#ENTRYPOINT ["python", "run.py"]
