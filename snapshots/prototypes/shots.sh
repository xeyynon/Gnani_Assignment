#!/usr/bin/env bash
# Usage: bash snapshots/prototypes/shots.sh <look.css> <out-dir>
# Needs the made-up-data preview (python -m dukaan_dost.preview --port 8882, shop PIN 1111) and SNAP_ADMIN_PASSWORD set from what it prints.
# Injects <look.css> as a <style> after the page's own and takes the standard set of pictures.
set -e
CSS="$1"; OUT="$2"; mkdir -p "$OUT"
cd "$(dirname "$0")/../.."
SHOP=$(printf 'shop:1111' | base64); ADM=$(printf 'admin:%s' "$SNAP_ADMIN_PASSWORD" | base64)
INJ=$(node -e 'const fs=require("fs");const css=fs.readFileSync(process.argv[1],"utf8");process.stdout.write("(()=>{const s=document.createElement(\"style\");s.id=\"look\";s.textContent="+JSON.stringify(css)+";document.head.append(s);})()")' "$CSS")
B=http://127.0.0.1:8882
shot() { EVAL="$INJ${4:+;$4}" node --experimental-websocket scripts/ui_check/shot.mjs "$B$1" "$OUT/$2" $3; }
shot "/s/demo_kirana/dashboard"          dash-overview-light-1280.png "1280 900 light $SHOP"
shot "/s/demo_kirana/dashboard"          dash-overview-dark-1280.png  "1280 900 dark $SHOP"
shot "/s/demo_kirana/dashboard#calls"    dash-calls-light-1280.png    "1280 900 light $SHOP"
shot "/s/demo_kirana/dashboard#calls"    dash-calls-dark-390.png      "390 844 dark $SHOP"
shot "/s/demo_kirana/dashboard#orders"   dash-orders-light-390.png    "390 844 light $SHOP"
shot "/s/demo_kirana/"                   call-light-1280.png          "1280 900 light"
shot "/s/demo_kirana/"                   call-dark-390.png            "390 844 dark"
shot "/admin"                            admin-dark-1280.png          "1280 900 dark $ADM"
