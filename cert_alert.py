import datetime
import signal
import socket
import ssl
import sys
import time

import datadog as ddog
import requests


# from https://serverlesscode.com/post/ssl-expiration-alerts-with-lambda/
def ssl_expiry_datetime(hostname):
    ssl_date_fmt = r'%b %d %H:%M:%S %Y %Z'

    context = ssl.create_default_context()
    conn = context.wrap_socket(
        socket.socket(socket.AF_INET),
        server_hostname=hostname,
    )
    # 3 second timeout because Lambda has runtime limitations
    conn.settimeout(3.0)

    try:
        conn.connect((hostname, 443))
    except socket.gaierror:
        return None
    ssl_info = conn.getpeercert()
    # parse the string from the certificate into a Python datetime object
    return datetime.datetime.strptime(ssl_info['notAfter'], ssl_date_fmt)


def check_hosts(hostsfilename):
    with open(hostsfilename) as hostsfile:
        hosts = [line.strip() for line in hostsfile.readlines()]

    now = datetime.datetime.now()
    for host in hosts:
        exp = ssl_expiry_datetime(host)
        if exp is None:
            print "Couldn't connect to {}. Skipping.".format(host)
            continue
        days_to_expiry = (exp - now).days
        print '{} expires in {} days'.format(host, days_to_expiry)
        ddog.statsd.gauge('ssl_expiries.days_to_expiry',
                          days_to_expiry,
                          tags=["host:" + host])


def init_ddog():
    hostname_url = 'http://169.254.169.254/latest/meta-data/hostname'

    try:
        hostname_aws = requests.get(hostname_url).text
    except Exception as e:
        hostname_aws = 'localhost'

    ddog.initialize(statsd_host=hostname_aws)


def main():
    if len(sys.argv) != 2:
        print 'Usage: cert_alert.py hostsfile'
        sys.exit(1)

    signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
    init_ddog()

    hfname = sys.argv[1]
    print 'checking expiration dates on certs for hosts listed in ', hfname

    while True:
        check_hosts(hfname)
        time.sleep(60)


if __name__ == "__main__":
    main()
