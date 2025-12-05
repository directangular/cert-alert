import datetime
import logging
import os
import signal
import socket
import ssl
import sys
import time

import datadog as ddog
import requests


# Ensure all timestamps are in UTC
logging.Formatter.converter = time.gmtime


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)sZ - %(levelname)-8s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


logger = logging.getLogger(__name__)


# Check the SSL certificate expiration for a given hostname
def ssl_expiry_datetime(hostname):
    ssl_date_fmt = r"%b %d %H:%M:%S %Y %Z"

    context = ssl.create_default_context()
    conn = context.wrap_socket(
        socket.socket(socket.AF_INET),
        server_hostname=hostname,
    )
    conn.settimeout(3.0)  # Set timeout to 3 seconds

    try:
        conn.connect((hostname, 443))
        ssl_info = conn.getpeercert()
        if ssl_info is None:
            logger.warning(f"No peer cert from {hostname}")
            return
        return datetime.datetime.strptime(ssl_info["notAfter"], ssl_date_fmt)
    except Exception as e:
        logger.warning("Could not connect to %s. Exception: %s", hostname, e)
        return None
    finally:
        conn.close()


# Check SSL expiration dates for all hosts listed in the file
def check_hosts(hostsfilename):
    with open(hostsfilename) as hostsfile:
        hosts = [line.strip() for line in hostsfile if line.strip()]

    now = datetime.datetime.now()
    for host in hosts:
        exp = ssl_expiry_datetime(host)
        if exp is None:
            logger.info("Couldn't connect to %s. Skipping.", host)
            continue
        days_to_expiry = (exp - now).days
        logger.info("%s expires in %s days", host, days_to_expiry)
        ddog.statsd.gauge(
            "ssl_expiries.days_to_expiry", days_to_expiry, tags=["host:" + host]
        )


def get_hostname_aws() -> str:
    token_url = "http://169.254.169.254/latest/api/token"
    hostname_url = "http://169.254.169.254/latest/meta-data/hostname"
    try:
        token_headers = {"X-aws-ec2-metadata-token-ttl-seconds": "600"}
        token_response = requests.put(token_url, headers=token_headers, timeout=3)
        token_response.raise_for_status()

        hostname_headers = {"X-aws-ec2-metadata-token": token_response.text}
        hostname_response = requests.get(hostname_url, headers=hostname_headers, timeout=3)
        hostname_response.raise_for_status()

        return hostname_response.text
    except Exception as e:
        raise RuntimeError("Failed to get hostname from AWS: %s", e)


# Initialize Datadog configuration
def init_ddog():
    doghost = os.getenv("DOGSTATSD_HOST")
    if not doghost:
        raise RuntimeError("Missing required env var: DOGSTATSD_HOST")

    if doghost == "AWS_AUTODISCOVER_INSTANCE":
        logger.info("Attempting AWS hostname auto-discovery")
        statsd_host = get_hostname_aws()
    else:
        statsd_host = doghost

    kwargs = {
        "statsd_host": statsd_host,
    }
    logger.info(f"Initializing ddog with {kwargs}")
    ddog.initialize(**kwargs)


# Main function to handle workflow
def main():
    if len(sys.argv) != 2:
        logger.error("Usage: cert_alert.py <hostsfile>")
        sys.exit(1)

    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
    init_ddog()

    hfname = sys.argv[1]
    logger.info("Checking expiration dates on certs for hosts listed in %s", hfname)

    while True:
        check_hosts(hfname)
        time.sleep(60)


if __name__ == "__main__":
    main()
