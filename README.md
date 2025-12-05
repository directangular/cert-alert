# Cert Alert!

This repo contains a Docker image and kubernetes deployment to monitor the
expiration date of SSL certificates.  Expiration dates are logged to stdout
as well as DataDog.  `Cert Alert` might be a bit of a misnomer since it's
assumed that the user will set up alerting on the DataDog side.  There is
currently no built-in alerting.

# Installation

## Step 1: Create kustomize and hosts.txt files

Create `./overlay/kustomization.yaml` in this repo with content:

```
resources:
  - ../deploy

configMapGenerator:
  - name: cert-alert-config
    files:
      - hosts.txt
```

and `./overlay/hosts.txt` with your hosts listed, one per line:

```
example.com
mydomain.example.com
```

## Step 2: Customize dogstatsd hostname

`cert_alert` sends metrics to DataDog. The metric is named
`ssl_expiries.days_to_expiry` and is tagged with the hostname being checked. This
metric can be used to set up a monitor so that you be alerted when you have a
certificate approaching its expiration date.

The dogstatsd hostname can either be provided manually, or can be auto-discovered
from the [AWS instance metadata
API](http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html#instancedata-data-retrieval).

### Manually set dogstatsd hostname

You can manually specify the dogstatsd hostname by adding the following item to
`configMapGenerator` in `./overlay/kustomization.yaml`:

```
configMapGenerator:
  ...
  - name: cert-alert-env
    literals:
      - DOGSTATSD_HOST=statsd-exporter.monitoring.svc.cluster.local
```

The above example assumes `prom/statsd-exporter` is running as a service named
`statsd-exporter` in the `monitoring` namespace.

### AWS DaemonSet

You can also set `DOGSTATSD_HOST` to the special value `"AWS_AUTODISCOVER_INSTANCE"`,
which will cause `cert_alert` to discover the hostname of the node where the workload
is running. This works when you have DataDog running as a `DaemonSet` in your cluster
(i.e. it's available on every node).

Example using AWS auto-discovery:

```
configMapGenerator:
  ...
  - name: cert-alert-env
    literals:
      - DOGSTATSD_HOST=AWS_AUTODISCOVER_INSTANCE
```

## Step 3: Deploy

Once you've created `overlay/kustomization.yaml` as per the above instructions, you
can deploy `cert_alert` with:

```
kubectl apply -k overlay/
```
