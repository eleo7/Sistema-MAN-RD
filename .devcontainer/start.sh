#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p .runtime
check_health() {
  .venv/bin/python - <<'PY'
import json
import urllib.request
try:
    with urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2) as response:
        assert json.load(response)['status'] == 'ok'
except Exception:
    raise SystemExit(1)
PY
}
if check_health; then
  echo 'Manutenção RD - GYN já está respondendo na porta 5000.'
  exit 0
fi
nohup .venv/bin/python app.py > .runtime/server.log 2>&1 < /dev/null &
server_pid=$!
for attempt in {1..20}; do
  if check_health; then
    echo 'Manutenção RD - GYN iniciado. Abra a porta 5000 na aba Ports.'
    exit 0
  fi
  if ! kill -0 "$server_pid" 2>/dev/null; then
    cat .runtime/server.log
    exit 1
  fi
  sleep 1
done
echo 'O servidor não respondeu. Consulte .runtime/server.log.' >&2
exit 1
