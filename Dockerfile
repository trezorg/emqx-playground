FROM python:3.9.10-slim

ENV USER=mqtt \
    USER_ID=1000 \
    PROJECT_PATH="/var/app" \
    LANG="C.UTF-8" \
    LANGUAGE="C.UTF-8" \
    LC_ALL="C.UTF-8" \
    BUILD_PACKAGES="build-essential python-dev libtool automake" \
    PACKAGES="curl python-setuptools" \
    PYTHONPATH=src:${PYTHONPATH}

RUN echo "Installing and updating system packages..." && \
    apt update -y && \
    apt upgrade -y && \
    apt install -y --no-install-recommends ${BUILD_PACKAGES} ${PACKAGES} && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m -o -u ${USER_ID} -d ${PROJECT_PATH} ${USER}

WORKDIR ${PROJECT_PATH}

ADD requirements.txt ${PROJECT_PATH}/requirements.txt

RUN cd ${PROJECT_PATH} && \
    python -m pip install -U -r requirements.txt && \
    apt purge -y ${BUILD_PACKAGES} && \
    apt autoremove -y

ADD . ${PROJECT_PATH}

RUN chown -R ${USER_ID}:${USER_ID} ${PROJECT_PATH}

USER ${USER_ID}
