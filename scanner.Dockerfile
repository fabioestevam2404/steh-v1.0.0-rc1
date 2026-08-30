FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git ca-certificates \
    && pip install --no-cache-dir semgrep==1.136.0 \
    && curl -sSfL https://raw.githubusercontent.com/gitleaks/gitleaks/master/scripts/install.sh \
       | sh -s -- -b /usr/local/bin v8.28.0 \
    && curl -sSfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
       | sh -s -- -b /usr/local/bin v0.66.0 \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
ENTRYPOINT []
