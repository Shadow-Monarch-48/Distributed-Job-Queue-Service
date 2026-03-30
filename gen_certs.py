import subprocess
import os

os.makedirs('certs', exist_ok=True)

subprocess.run([
    'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
    '-keyout', 'certs/server.key',
    '-out', 'certs/server.crt',
    '-days', '365', '-nodes',
    '-subj', '/CN=localhost'
], check=True)

print("Certificates generated: certs/server.crt, certs/server.key")
