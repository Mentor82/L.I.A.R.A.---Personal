# SearXNG config

`settings.yml` in this directory is git-ignored (it contains a generated
secret_key) - set it up once per host:

```bash
cp searxng/settings.yml.example searxng/settings.yml
python3 -c "import secrets; print(secrets.token_hex(32))"
# paste the output in as server.secret_key in settings.yml
docker-compose up -d searxng
```

Bound to `127.0.0.1:8080` only in `docker-compose.yml` - never expose this
port on the LAN or internet. It's only ever called by `app/services/
search_broker.py` from the Liara backend on the same host.
