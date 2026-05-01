

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Устанавливаем всё необходимое
RUN apt-get update && apt-get install -y \
    g++ \
    python3 \
    python3-pip \
    nodejs \
    npm \
    default-jdk \
    && rm -rf /var/lib/apt/lists/*

# Создаём непривилегированного пользователя
RUN groupadd -r sandbox && useradd -r -g sandbox -m sandbox

WORKDIR /sandbox