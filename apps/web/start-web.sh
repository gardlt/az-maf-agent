#!/bin/sh
set -eu
: "${AGENT_API_HOST:?AGENT_API_HOST must be the approved agent API hostname}"
case "$AGENT_API_HOST" in
    *[!a-zA-Z0-9.-]*|.*|-*) echo 'AGENT_API_HOST must be a hostname without a URL, port, or path' >&2; exit 2 ;;
esac
mkdir -p /tmp/nginx/client_body /tmp/nginx/proxy /tmp/nginx/fastcgi /tmp/nginx/uwsgi /tmp/nginx/scgi
# Substitute only the trusted upstream host, leaving nginx request variables intact.
envsubst '${AGENT_API_HOST}' < /etc/nginx/web.conf.template > /tmp/nginx/nginx.conf
case "${1:-}" in
    --check) exec nginx -t -c /tmp/nginx/nginx.conf ;;
    '') exec nginx -c /tmp/nginx/nginx.conf -g 'daemon off;' ;;
    *) echo 'Unsupported argument' >&2; exit 2 ;;
esac
