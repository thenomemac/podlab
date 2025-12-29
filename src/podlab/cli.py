#!/usr/bin/env python3

import json
import os
import signal
import subprocess
import sys
import time
from functools import cache

import loguru
import pydo
from loguru import logger

log = logger.info

DNS_TOKEN = os.environ.get("DO_AUTH_TOKEN")

CONTAINER_CLI = str(os.environ.get("PODLAB_CONTAINER_CLI", "podman"))
TTL = int(os.environ.get("PODLAB_TTL", "60"))
SLEEP = int(os.environ.get("PODLAB_SLEEP", "10"))
LOG_SHELL = bool(int(os.environ.get("PODLAB_LOG_SHELL", "0")))
IP_STALE_SEC = int(os.environ.get("PODLAB_IP_STALE_SEC", "60"))

G = {
    "FORCEUPDATE_PUBLIC_IP_DOMAINS": [
        x.strip()
        for x in os.environ.get("FORCEUPDATE_PUBLIC_IP_DOMAINS", "").strip().split("|")
        if x.strip() != ""
    ],
    "UPDATE_PUBLIC_IP_DOMAINS": [],
    "GET_PUBLIC_IP_TS": 0.0,
    "LABELS_PROCESSED": [],
}


def public_ip_change():
    global G

    if "PUBLIC_IP" not in G:
        G["PUBLIC_IP"] = get_public_ip()
        return True

    elif get_public_ip() != G["PUBLIC_IP"]:
        G["PUBLIC_IP"] = get_public_ip()
        return True

    else:
        return False


@cache
def get_client() -> pydo.Client:
    log("Creating DNS client...")
    client = pydo.Client(token=DNS_TOKEN)
    return client


def process_fqdn_to_sub_and_domain(fqdn: str) -> tuple[str, str]:
    fqdn_ = fqdn.split(".")

    return (".".join(fqdn_[:-2]), ".".join(fqdn_[-2:]))


def get_public_ip_update_list() -> list[tuple[str, str]]:
    UPDATE_PUBLIC_IP_DOMAINS, FORCEUPDATE_PUBLIC_IP_DOMAINS = (
        G["UPDATE_PUBLIC_IP_DOMAINS"],
        G["FORCEUPDATE_PUBLIC_IP_DOMAINS"],
    )

    return [
        process_fqdn_to_sub_and_domain(x)
        for x in {*FORCEUPDATE_PUBLIC_IP_DOMAINS, *UPDATE_PUBLIC_IP_DOMAINS}
    ]


def signal_handler(sig, frame):
    """Handler for signals like SIGINT or SIGTERM."""
    log(f"\nSignal {signal.Signals(sig).name} received.")
    cleanup()
    sys.exit(0)


def get_records(client, domain_name: str) -> list[dict]:
    recs = []
    for i in range(1, 1000):
        res = client.domains.list_records(domain_name, page=i)
        if len(res["domain_records"]) > 0:
            recs.extend(res["domain_records"])
        else:
            break
    return recs


def update_public_ip():
    client = get_client()
    public_ip = get_public_ip()

    fqdns = get_public_ip_update_list()
    log(f"Running update_public_ip() for: {fqdns}")
    log(f"Running update_public_ip() with public_ip={public_ip}")

    i = 0
    for subdomain, domain_name in fqdns:
        records = get_records(client, domain_name)

        id_ = None
        for rec in records:
            if rec["type"].lower() == "a" and rec["name"].lower() == subdomain.lower():
                id_ = rec["id"]
                break

        if id_ is None:
            raise ValueError(
                f"Not found in DNS to update (subdomain, domain_name)={(subdomain, domain_name)}"
            )

        if id_ and rec["data"] == public_ip:
            break

        req = {
            "type": "A",
            "name": subdomain,
            "data": public_ip,
            "ttl": TTL,
        }

        resp = update_dns_to_providor(req)
        i += 1

        log(f"API Response: {resp}")

    log(f"update_public_ip() updated {i}/{len(fqdns)} dns recs.")


def update_dns_to_providor(req: dict, domain_name: str, id_: int | None = None) -> dict:
    client = get_client()

    if os.environ.get("DEBUG") and id_:
        resp = {"DEBUG ENV VAR SET for req", req}
    elif id_:
        log(f"Updating record id_={id_}: {req}")
        resp = client.domains.update_record(
            domain_name=domain_name, domain_record_id=id_, body=req
        )
    else:
        log(f"Creating record: {req}")
        resp = client.domains.create_record(domain_name=domain_name, body=req)

    return resp


def update_dns(dns_label: str):
    """log examples:
    2025-12-14 03:29:36.962 | INFO     | podlab.cli:main:81 - Processing record: 'olsonsky.com a mc1 auto'
    2025-12-14 03:29:36.962 | INFO     | podlab.cli:main:81 - Processing record: 'olsonsky.com srv _minecraft._tcp.mc1 mc1 25565'
    """
    UPDATE_PUBLIC_IP_DOMAINS = G["UPDATE_PUBLIC_IP_DOMAINS"]

    client = get_client()

    domain_name, dns_type, *dns_list = dns_label.lower().split(" ")

    if dns_type == "a":
        if len(dns_list) == 2 and dns_list[1] == "auto":
            public_ip = get_public_ip()
        else:
            raise ValueError(f"Invalid DNS label: '{dns_label}'")

        subdomain = dns_list[0]

        req = {
            "type": "A",
            "name": subdomain,
            "data": public_ip,
            "ttl": TTL,
        }

        fqdn = f"{subdomain}.{domain_name}"
        if fqdn not in UPDATE_PUBLIC_IP_DOMAINS:
            UPDATE_PUBLIC_IP_DOMAINS.append(fqdn)

    elif dns_type == "srv":

        if len(dns_list) == 3:
            pass
        else:
            raise ValueError(f"Invalid DNS label: '{dns_label}'")

        req = {
            "type": "SRV",
            "name": dns_list[0],
            "data": dns_list[1],
            "port": dns_list[2],
            "priority": 10,
            "weight": 100,
            "ttl": TTL,
        }

    else:
        raise ValueError(f"Invalid DNS label: '{dns_label}'")

    records = get_records(client, domain_name)

    id_ = None
    for rec in records:
        if (
            rec["type"].lower() == req["type"].lower()
            and rec["name"].lower() == req["name"].lower()
        ):
            id_ = rec["id"]
            break

    resp = update_dns_to_providor(req, domain_name, id_)

    return resp


def get_public_ip():
    global G

    if (
        time.time() - G["GET_PUBLIC_IP_TS"] < IP_STALE_SEC
        and "GET_PUBLIC_IP_CACHE" in G
    ):
        return G["GET_PUBLIC_IP_CACHE"]
    else:

        public_ip = subprocess.run(
            "dig +short myip.opendns.com @resolver1.opendns.com",
            shell=True,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        G["GET_PUBLIC_IP_CACHE"] = public_ip
        G["GET_PUBLIC_IP_TS"] = time.time()

        return public_ip


def cleanup():
    log("Running cleanup...")


def pull_labels_by_container(label: str) -> dict[str, list[str]]:
    labels_by_container = {}

    if LOG_SHELL:
        log("Pulling containers and labels...")
    cmd = CONTAINER_CLI + r""" ps --filter "label=${label}" --format '{{.Names}}'"""
    if LOG_SHELL:
        log(f"Running cmd $ {cmd}")
    containers = (
        subprocess.run(
            cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            env={"label": label},
        )
        .stdout.strip()
        .split()
    )
    if LOG_SHELL:
        log(f"containers: {containers}")

    for container in containers:
        if LOG_SHELL:
            log(f"Getting labels for container: '{container}'")

        cmd = (
            CONTAINER_CLI
            + r''' inspect --format "{{ index .Config.Labels \"${label}\" }}" "${container}"'''
        )
        if LOG_SHELL:
            log(f"Running cmd $ {cmd}")
        labels = (
            subprocess.run(
                cmd,
                shell=True,
                check=True,
                capture_output=True,
                text=True,
                env={"label": label, "container": container},
            )
            .stdout.strip()
            .split("|")
        )

        labels_by_container[container] = labels

    return labels_by_container


def main():

    # Register the signal handlers
    # SIGINT is typically generated by Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    # SIGTERM is a general termination request sent by the OS (e.g., when stopping a service)
    signal.signal(signal.SIGTERM, signal_handler)

    log("Program running. Press Ctrl+C or send SIGTERM to stop gracefully.")

    if DNS_TOKEN is None:
        raise ValueError("ENV VAR DO_AUTH_TOKEN is not set.")
    log(f"DNS_TOKEN='{DNS_TOKEN[:5]}<...>{DNS_TOKEN[-5:]}'")

    public_ip = get_public_ip()
    log(f"public_ip={public_ip}")

    while True:
        try:

            labels_by_container = pull_labels_by_container(label="podlab.dns.update")

            containers = [*labels_by_container]
            i = 0
            for container in containers:
                labels = labels_by_container[container]

                for label in labels:
                    if (container, label) not in G["LABELS_PROCESSED"]:

                        log(f"Processing container {container} with record: '{label}'")
                        resp = update_dns(label)
                        i += 1
                        G["LABELS_PROCESSED"].append((container, label))
                        log(f"API Response: {resp}")

            log(f"DNS processed for {i} new container labels.")

            if public_ip_change():
                update_public_ip()
            else:
                log("No ip change...")

            log(f"sleeping...")
            time.sleep(SLEEP)
        except KeyboardInterrupt:
            # This catch is a fallback if the signal handler doesn't fire immediately
            # or for direct Ctrl+C behavior
            log("KeyboardInterrupt caught in loop. Exiting...")
            cleanup()


if __name__ == "__main__":
    main()
