FROM ubuntu:24.04
LABEL maintainer="maxmilio@kiv.zcu.cz" \
      org.opencontainers.image.source="https://github.com/maxotta/iac-dev-docker"

ARG SRC_WORKDIR=/usr/src
# ARG SRC_GITREPO

ARG KUBECTL_VERSION=v1.37.2

ENV PATH="/opt/ansible-venv/bin:${PATH}"

ENV DEBIAN_FRONTEND noninteractive

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        gnupg \
        software-properties-common \
        wget \
        apt-transport-https; \
    wget -O- https://apt.releases.hashicorp.com/gpg | \
        gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg; \
    gpg --no-default-keyring \
        --keyring /usr/share/keyrings/hashicorp-archive-keyring.gpg \
        --fingerprint; \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com noble main" \
        > /etc/apt/sources.list.d/hashicorp.list; \
    apt-get update

RUN apt-get -y install git

RUN wget -q "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
      -O /tmp/kubectl && \
    wget -q "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl.sha256" \
      -O /tmp/kubectl.sha256 && \
    echo "$(cat /tmp/kubectl.sha256)  /tmp/kubectl" | sha256sum --check && \
    install -o root -g root -m 0755 /tmp/kubectl /usr/local/bin/kubectl && \
    rm /tmp/kubectl /tmp/kubectl.sha256

RUN apt-get -y install terraform

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-full \
        python3-venv; \
    python3 -m venv /opt/ansible-venv; \
    /opt/ansible-venv/bin/pip install --no-cache-dir ansible==9.2.0

RUN apt-get -y install mc

WORKDIR ${SRC_WORKDIR}
# RUN git clone ${SRC_GITREPO}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV SHELL /bin/bash

CMD [ "sh", "-c", "while :; do cd ${SRC_WORKDIR}; bash -i; echo '==> NOPE ! Exiting the shell would also stop the Docker container! Please close the terminal window instead.'; done" ]
