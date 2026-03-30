import socket
import ssl
import json
import time
import sys

# Connect to server directly (no load balancer)
HOST = 'localhost'
PORT = 9000  # Direct server connection


def send_msg(conn, data):
    conn.sendall(json.dumps(data).encode() + b'\n')


def recv_msg(conn):
    buf = b''
    while True:
        byte = conn.recv(1)
        if not byte:
            return None
        if byte == b'\n':
            break
        buf += byte
    return json.loads(buf.decode()) if buf else None


def main():
    client_id = sys.argv[1] if len(sys.argv) > 1 else 'client_1'
    num_jobs = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_verify_locations('certs/server.crt')

    with socket.create_connection((HOST, PORT)) as sock:
        with ctx.wrap_socket(sock, server_hostname='localhost') as ssock:
            send_msg(ssock, {'type': 'register_client'})
            print(f"[{client_id}] Connected (SSL)")

            job_ids = []
            for i in range(num_jobs):
                payload = f"{client_id}_task_{i}"
                send_msg(ssock, {'type': 'submit', 'payload': payload})
                resp = recv_msg(ssock)
                print(f"[{client_id}] Submitted -> job_id: {resp['job_id']}")
                job_ids.append(resp['job_id'])

            print(f"[{client_id}] Waiting for jobs to complete...")
            time.sleep(6)  # Increased wait to allow retries

            print(f"\n{'='*70}")
            print(f"[{client_id}] FINAL RESULTS:")
            print(f"{'='*70}")
            for i, job_id in enumerate(job_ids, 1):
                send_msg(ssock, {'type': 'status', 'job_id': job_id})
                resp = recv_msg(ssock)
                status = resp['type']
                result = resp.get('result', 'N/A')
                
                # Format output
                status_symbol = '✓' if status == 'result' and 'done::' in str(result) else '✗' if 'FAILED' in str(result) else '⏳'
                print(f"[{i}] {job_id[:12]}... => {status_symbol} {status:10} | {result}")
            print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
