FROM ubuntu:24.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       bash curl git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

CMD ["sleep", "infinity"]
