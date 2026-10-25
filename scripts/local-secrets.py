#!/usr/bin/env python3
"""Create new local-only credentials over stdin. Refuse to rotate existing data credentials."""
import base64
import json
import secrets
import subprocess

command = ['kubectl', '--context', 'kind-voyage-infra', '-n', 'voyage-dev']
for name in ['voyage-runtime', 'voyage-postgres']:
    result = subprocess.run(command + ['get', 'secret', name, '--ignore-not-found', '-o', 'name'],
                            capture_output=True, text=True, check=True)
    if result.stdout.strip():
        raise SystemExit('Existing credentials found. Reuse them; do not rotate a database password blindly.')
password = secrets.token_urlsafe(32)
def secret(name, values):
    return {'apiVersion': 'v1', 'kind': 'Secret', 'metadata': {'name': name, 'namespace': 'voyage-dev'},
            'type': 'Opaque', 'data': {key: base64.b64encode(value.encode()).decode() for key, value in values.items()}}
items = [secret('voyage-postgres', {'POSTGRES_PASSWORD': password}),
         secret('voyage-runtime', {'DATABASE_URL': f'postgresql+psycopg://voyage:{password}@postgres:5432/voyage'})]
subprocess.run(command + ['apply', '-f', '-'], input=json.dumps({'apiVersion': 'v1', 'kind': 'List', 'items': items}),
               text=True, check=True)
