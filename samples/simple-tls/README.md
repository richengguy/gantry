# Simple TLS
This shows how to run services using the Traefik router's self-signed
certificates functionality.  This is done by setting `enable-tls: true` in
`service.yml` and adding an https redirect inside of `traefik.yml`.  Once done,
the following paths are available on `https://<your-domain>`:

* `/` - The 'hello-world' service.
* `/whoami/` - The 'whoami' service.
* `/dashboard/` - The Traefik internal dashboard.
