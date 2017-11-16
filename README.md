# Cert Alert!

This repo contains a Docker image and kubernetes deployment to monitor the
expiration date of SSL certificates.  Expiration dates are logged to stdout
as well as DataDog.  `Cert Alert` might be a bit of a misnomer since it's
assumed that the user will set up alerting on the DataDog side.  There is
currently no built-in alerting.

# Installation

## Step 1: Create a ConfigMap with your hosts

The list of hosts to check is controlled by a `ConfigMap`, which you'll
need to create first with the following command:

```shell
kubectl create configmap cert-alert-config --from-file=hosts.txt
```

Your `hosts.txt` file should be a flat list of hostnames.  For example:

```
beta.popitup.com
popitup.com
scaryphotobooth.com
stopandpayus.com
www.popitup.com
www.scaryphotobooth.com
www.stopandpayus.com
```

## Step 2: Create the deployment

Once your `ConfigMap` is created you can create the deployment:

```
kubectl apply -f deployment.yaml
```

And that's it!  Logging will start immediately.

# Updating host configuration

If you need to update the list of hosts in the future you can just delete
and re-create the `ConfigMap` and deployment:

```shell
kubectl delete deployment cert-alert-deployment
kubectl delete configmap cert-alert-config
kubectl create configmap cert-alert-config --from-file=hosts.txt
kubectl apply -f deployment.yaml
```

# DataDog integration

By default, `cert_alert.py` tries to send metrics to DataDog.  The metric
is named `ssl_expiries.days_to_expiry` and is tagged with the hostname
being checked.  This metric can be used to set up a monitor so that you be
alerted when you have a certificate approaching its expiration date.

Currently it's assumed that DataDog is running as a `DaemonSet` in your
cluster.  That way, the endpoint can be auto-discovered by querying the
[AWS instance metadata
API](http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html#instancedata-data-retrieval).
If that doesn't work, it will use `localhost`.

PRs welcome if this approach doesn't work in your environment :).
