FROM golang:alpine as builder

RUN apk add --no-cache git make

WORKDIR /build
ENV GOTOOLCHAIN=auto
RUN git clone https://github.com/amnezia-vpn/amneziawg-go.git . && \
    go mod download && \
    go mod verify && \
    make

FROM alpine:3.19

ARG AWGTOOLS_RELEASE="1.0.20250901"

RUN apk --no-cache add \
    iproute2 \
    iptables \
    ip6tables \
    bash \
    python3 \
    py3-pip \
    wget \
    unzip \
    openresolv && \
    pip3 install --break-system-packages --no-cache-dir qrcode && \
    cd /usr/bin/ && \
    wget https://github.com/amnezia-vpn/amneziawg-tools/releases/download/v${AWGTOOLS_RELEASE}/alpine-3.19-amneziawg-tools.zip && \
    unzip -j alpine-3.19-amneziawg-tools.zip && \
    chmod +x /usr/bin/awg /usr/bin/awg-quick && \
    ln -s /usr/bin/awg /usr/bin/wg && \
    ln -s /usr/bin/awg-quick /usr/bin/wg-quick && \
    rm -f alpine-3.19-amneziawg-tools.zip

COPY --from=builder /build/amneziawg-go /usr/bin/amneziawg-go

RUN mkdir -p /etc/amnezia/amneziawg

WORKDIR /etc/amnezia/amneziawg

COPY scripts ./scripts
RUN chmod +x ./scripts/*.py

COPY scripts/entrypoint.py /entrypoint.py
RUN chmod +x /entrypoint.py

ENTRYPOINT ["/entrypoint.py"]
