# Positive fixture for the docker pin rule in a Dockerfile context.
# Two offending bases below: one explicit latest tag, one untagged base.
FROM ubuntu:latest
FROM alpine
RUN echo "build"
