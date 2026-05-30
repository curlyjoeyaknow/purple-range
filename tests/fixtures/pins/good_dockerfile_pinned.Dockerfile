# Negative fixture for rule `docker-latest` in a Dockerfile context.
# Version-tagged and digest-pinned bases must NOT be flagged. The `AS build`
# stage-alias form must not confuse the parser into seeing a bare image.
FROM ubuntu:22.04 AS build
FROM alpine:3.20.3
FROM python@sha256:abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789
RUN echo "build"
