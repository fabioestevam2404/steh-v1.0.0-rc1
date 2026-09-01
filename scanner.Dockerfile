FROM python:3.12-slim

ARG GITLEAKS_VERSION=8.28.0
ARG TRIVY_VERSION=0.69.3

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl; \
    pip install --no-cache-dir "setuptools<81" semgrep==1.136.0; \
    gitleaks_archive="gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"; \
    curl -fsSL \
        "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/${gitleaks_archive}" \
        -o "/tmp/${gitleaks_archive}"; \
    curl -fsSL \
        "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_checksums.txt" \
        -o /tmp/gitleaks_checksums.txt; \
    gitleaks_sha256="$(grep " ${gitleaks_archive}$" /tmp/gitleaks_checksums.txt | cut -d ' ' -f 1)"; \
    test -n "${gitleaks_sha256}"; \
    echo "${gitleaks_sha256}  /tmp/${gitleaks_archive}" | sha256sum -c -; \
    tar -xzf "/tmp/${gitleaks_archive}" -C /usr/local/bin gitleaks; \
    \
    trivy_archive="trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz"; \
    curl -fsSL \
        "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/${trivy_archive}" \
        -o "/tmp/${trivy_archive}"; \
    curl -fsSL \
        "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_checksums.txt" \
        -o /tmp/trivy_checksums.txt; \
    trivy_sha256="$(grep " ${trivy_archive}$" /tmp/trivy_checksums.txt | cut -d ' ' -f 1)"; \
    test -n "${trivy_sha256}"; \
    echo "${trivy_sha256}  /tmp/${trivy_archive}" | sha256sum -c -; \
    tar -xzf "/tmp/${trivy_archive}" -C /usr/local/bin trivy; \
    \
    gitleaks version; \
    trivy --version; \
    semgrep --version; \
    \
    apt-get purge -y curl; \
    apt-get autoremove -y; \
    rm -rf /var/lib/apt/lists/* /tmp/*

WORKDIR /workspace

ENTRYPOINT []