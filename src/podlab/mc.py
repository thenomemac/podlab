from loguru import logger

log = logger.info


def mc(
    name: str,
    port: int,
    compose_filepath: str = "~/work/mycloud/mc/compose.yml",
    strict_naming: bool = True,
) -> str:
    """A tool for generating docker compose yaml for a new minecraft server on the homelab.

    Ex:
        $ podlab mc --name mc2 --port 25566
    """

    log("Running with (kwarg, var, type):")
    log(("name", name, type(name)))
    log(("port", port, type(port)))

    log(f"Append the config to the compose.yml file, ex:")
    log(f"$ nano {compose_filepath}")

    if strict_naming and not (
        len(name) >= 3
        and name[:2] == "mc"
        and name[2:].isdigit()
        and int(name[2:]) >= 1
    ):
        raise ValueError(
            f"Parameter name='{name}' doesn't match pattern `mc<int>` where int >= 1"
        )

    if strict_naming and port != int(name[2:]) - 1 + 25565:
        raise ValueError(
            f"Parameter port={port} doesn't match pattern the suffix number in `name` - 1 + 25565"
        )

    template_str = f"""
  {name}:
    container_name: {name}
    image: docker.io/itzg/minecraft-server:latest
    restart: always
    tty: true
    stdin_open: true
    ports:
      - "25566:25565"
    environment:
      EULA: "TRUE"
      # TYPE: FABRIC
      # VERSION: 1.21.1
      # CF_API_KEY: ${{CF_API_KEY}}
      # TYPE: AUTO_CURSEFORGE
      # CF_PAGE_URL: https://www.curseforge.com/minecraft/modpacks/fantasy-minecraft-fabric/files/7269069
      # CF_FORCE_INCLUDE_MODS: |
      #   oracle-index
    volumes:
      - ${{VOLUME_DIR}}/{name}:/data
      - ${{VOLUME_DIR}}/{name}_downloads:/downloads:rw
    labels:
      - 'portical.upnp.forward={port}:{port}/tcp'
      - 'podlab.dns.update=olsonsky.com a {name} auto|olsonsky.com srv _minecraft._tcp.{name} {name} {port}'
"""

    return template_str
