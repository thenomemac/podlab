FROM docker.io/python:3.13-alpine
# build ex: podman build -t thenomemac/podlab .
# run ex: podman run -e DO_AUTH_TOKEN="${DO_AUTH_TOKEN}" -e PODLAB_LOG_SHELL=1 --rm -v /run/user/1000/podman/podman.sock:/var/run/docker.sock:ro thenomemac/podlab

RUN apk add --update docker bind-tools miniupnpc

RUN pip install --no-cache-dir poetry

WORKDIR /app

COPY . .

RUN poetry install --no-cache --without=dev

ENV PODLAB_CONTAINER_CLI=docker

CMD [ "python", "-m", "poetry", "run", "podlab", "app"]