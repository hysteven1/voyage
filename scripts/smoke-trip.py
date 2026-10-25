#!/usr/bin/env python3
"""No-key integration test: real API, database and Temporal; explicit synthetic providers."""
import argparse
import json
import time
import urllib.request
from datetime import date, timedelta

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--base-url', default='http://127.0.0.1:3000')
parser.add_argument('--timeout', type=int, default=180)
args = parser.parse_args()

def request(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(args.base_url.rstrip('/') + path, data=data,
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)

assert request('/api/v1/health/ready')['status'] == 'ready'
start = date.today() + timedelta(days=30)
trip = request('/api/v1/trips', {
    'origin': 'London, UK', 'destination': 'Paris, France',
    'start_date': str(start), 'end_date': str(start + timedelta(days=3)),
    'travelers': 2, 'budget': '10000.00', 'preferences': ['culture'],
})
trip_id = trip['id']
print('Created synthetic-provider smoke trip:', trip_id)
request(f'/api/v1/trips/{trip_id}/plan', {})
deadline = time.monotonic() + args.timeout
while time.monotonic() < deadline:
    current = request(f'/api/v1/trips/{trip_id}')
    if current['status'] == 'failed':
        raise SystemExit('Planning failed: ' + str(current.get('planning_error')))
    if current['status'] == 'completed':
        break
    time.sleep(2)
else:
    raise SystemExit('Timed out; inspect API/worker logs and Temporal workflow plan-trip-' + trip_id)
plan = request(f'/api/v1/trips/{trip_id}/itinerary')
assert plan['trip_id'] == trip_id and plan['days'], plan
assert plan['flight']['provider'] in ['Synthetic Airways', 'Demo Air'], plan['flight']
# Planning twice must reuse persisted results, not incur another planning run.
assert request(f'/api/v1/trips/{trip_id}/plan', {})['status'] == 'completed'
assert request(f'/api/v1/trips/{trip_id}/itinerary') == plan
print('PASS: persisted itinerary, synthetic provider, idempotent completed-plan request')
