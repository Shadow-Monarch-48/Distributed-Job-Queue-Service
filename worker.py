import socket
import ssl
import json
import time
import sys
import random


HOST = 'localhost'
PORT = 9000  # Connect directly to server (no load balancer)
SIMULATE_FAILURES = False  # Set to True to demonstrate failure/retry scenarios
FAILURE_PROBABILITY = 0.3  # 30% of jobs fail (only when SIMULATE_FAILURES=True)

# Different types of simulated failures
FAILURE_TYPES = [
    "Logic Error: Invalid input detected",
    "Timeout: Operation exceeded max duration",
    "Resource Error: Insufficient memory",
    "Data Error: Corrupted payload received",
    "State Error: Invalid operation for current state"
]

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


def execute_job(payload, worker_id):
    """Execute a job with optional failure simulation"""
    time.sleep(0.5)  # Job processing
    
    # Simulate occasional failures if enabled
    if SIMULATE_FAILURES and random.random() < FAILURE_PROBABILITY:
        # Pick a random failure type
        failure_type = random.choice(FAILURE_TYPES)
        raise Exception(failure_type)
    
    return f"done::{payload}"


def main():
    worker_id = sys.argv[1] if len(sys.argv) > 1 else 'worker_1'
    
    # Check for failure simulation flag
    global SIMULATE_FAILURES
    if len(sys.argv) > 2 and sys.argv[2] == '--simulate-failures':
        SIMULATE_FAILURES = True
        print(f"[{worker_id}] **FAILURE SIMULATION ENABLED** ({int(FAILURE_PROBABILITY*100)}% failure rate)")
    
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_verify_locations('certs/server.crt')
    print(f"[{worker_id}] Connecting...")
    try:
        with socket.create_connection((HOST, PORT)) as sock:
            with ctx.wrap_socket(sock, server_hostname='localhost') as ssock:
                send_msg(ssock, {'type': 'register_worker', 'worker_id': worker_id})
                print(f"[{worker_id}] Registered (SSL)")
                while True:
                    send_msg(ssock, {'type': 'fetch'})
                    msg = recv_msg(ssock)
                    if not msg:
                        print(f"[{worker_id}] Server closed connection.")
                        break
                    if msg['type'] == 'job':
                        job_id = msg['job_id']
                        print(f"[{worker_id}] Executing {job_id[:8]}... payload={msg['payload']}")
                        try:
                            result = execute_job(msg['payload'], worker_id)
                            send_msg(ssock, {'type': 'complete', 'job_id': job_id, 'result': result})
                            ack = recv_msg(ssock)
                            print(f"[{worker_id}] {job_id[:8]}... ✓ completed")
                        except Exception as e:
                            # Send failure message
                            error_msg = str(e)
                            print(f"[{worker_id}] {job_id[:8]}... ✗ FAILED: {error_msg}")
                            send_msg(ssock, {'type': 'failed', 'job_id': job_id, 'error': error_msg})
                            ack = recv_msg(ssock)
                            print(f"[{worker_id}] {job_id[:8]}... queued for retry")
                    elif msg['type'] == 'wait':
                        time.sleep(0.5)
    except KeyboardInterrupt:
        print(f"[{worker_id}] Shutting down...")
    except Exception as e:
        print(f"[{worker_id}] Error: {e}")


if __name__ == '__main__':
    main()
