FROM ubuntu:bionic

COPY . .

RUN pip install manowar_server

EXPOSE 5000
