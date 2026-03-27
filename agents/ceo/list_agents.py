import json, sys
agents = json.load(sys.stdin)
for a in agents:
    rc = a.get('runtimeConfig',{}).get('heartbeat',{})
    print(a['name'], '|', a.get('urlKey'), '| interval:', rc.get('intervalSec'), 's | enabled:', rc.get('enabled'))
