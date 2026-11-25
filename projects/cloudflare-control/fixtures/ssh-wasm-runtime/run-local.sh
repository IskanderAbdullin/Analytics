#!/usr/bin/env bash
set -euo pipefail
log="$(mktemp)"
./node_modules/.bin/wrangler dev --local --ip 127.0.0.1 --port 18765 >"$log" 2>&1 &
pid=$!
trap 'kill "$pid" 2>/dev/null || true; wait "$pid" 2>/dev/null || true; cat "$log"; rm -f "$log"' EXIT
for i in $(seq 1 20); do
  if ! kill -0 "$pid" 2>/dev/null; then exit 1; fi
  if code=$(curl --max-time 3 -s -o result.json -w '%{http_code}' http://127.0.0.1:18765/); then
    if [ "$code" != "000" ]; then
      node --input-type=module -e 'import fs from "node:fs"; import assert from "node:assert/strict"; const raw=fs.readFileSync("result.json","utf8"); console.log(raw.slice(0,800)); const body=JSON.parse(raw); assert.equal(body.ok,true); assert.deepEqual(body.stages,["exports","wasm_init"]); console.log("PASS local WASM library initialization");'
      exit 0
    fi
  fi
  sleep 1
done
exit 1
