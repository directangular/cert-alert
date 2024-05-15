import datetime
import logging
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
            logging.warning(f"No peer cert from {hostname}")
            return
        return datetime.datetime.strptime(ssl_info["notAfter"], ssl_date_fmt)
    except Exception as e:
        logging.warning("Could not connect to %s. Exception: %s", hostname, e)
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
            logging.info("Couldn't connect to %s. Skipping.", host)
            continue
        days_to_expiry = (exp - now).days
        logging.info("%s expires in %s days", host, days_to_expiry)
        ddog.statsd.gauge(
            "ssl_expiries.days_to_expiry", days_to_expiry, tags=["host:" + host]
        )


# Initialize Datadog configuration
def init_ddog():
    hostname_url = "http://169.254.169.254/latest/meta-data/hostname"
    try:
        hostname_aws = requests.get(hostname_url, timeout=3).text
    except Exception as e:
        logging.error("Failed to get hostname from AWS: %s", e)
        hostname_aws = "localhost"

    ddog.initialize(statsd_host=hostname_aws)


# Main function to handle workflow
def main():
    if len(sys.argv) != 2:
        logging.error("Usage: cert_alert.py <hostsfile>")
        sys.exit(1)

    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
    init_ddog()

    hfname = sys.argv[1]
    logging.info("Checking expiration dates on certs for hosts listed in %s", hfname)

    while True:
        check_hosts(hfname)
        time.sleep(60)


if __name__ == "__main__":
    main()
