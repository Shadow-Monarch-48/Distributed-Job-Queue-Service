import socket
import ssl
import threading
import queue
import json
import uuid
import logging
import sys
import time

def setup_logging(port):
    logging.basicConfig(
        level=logging.INFO, 
        format=f'%(asctime)s [SERVER:{port}] %(message)s'
    )

HOST = '0.0.0.0'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
setup_logging(PORT)

# Optimized for individual job handling
job_queue = queue.Queue()
active_jobs = {}  # job_id -> {'worker_addr': addr, 'timestamp': time, 'on_retry': bool}
active_workers = set()  # worker_addr -> actively connected workers
results = {}  # job_id -> result
failed_jobs = {}  # job_id -> {retry_count, last_error, timestamp}
results_lock = threading.Lock()  # Only protect results dict
workers_lock = threading.Lock()  # Protect active_workers set
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds
JOB_TIMEOUT = 10.0  # Maximum time a job can be active before considered stuck

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

def handle_client(conn, addr):
    logging.info(f"Client connected: {addr}")
    try:
        while True:
            msg = recv_msg(conn)
            if not msg:
                break
            if msg['type'] == 'submit':
                job_id = str(uuid.uuid4())
                job = {'job_id': job_id, 'payload': msg['payload']}
                job_queue.put(job)
                logging.info(f"Job submitted: {job_id}")
                send_msg(conn, {'type': 'ack', 'job_id': job_id})
            elif msg['type'] == 'status':
                job_id = msg['job_id']
                with results_lock:
                    result = results.get(job_id)
                if result is not None:
                    send_msg(conn, {'type': 'result', 'job_id': job_id, 'result': result})
                else:
                    send_msg(conn, {'type': 'pending', 'job_id': job_id})
            elif msg['type'] == 'stats':
                # Return system statistics for GUI monitoring
                with results_lock:
                    with workers_lock:
                        stats = {
                            'type': 'stats',
                            'queue_size': job_queue.qsize(),
                            'active_workers': len(active_workers),
                            'active_jobs': len(active_jobs),
                            'completed_jobs': len(results),
                            'pending_jobs': job_queue.qsize() + len(active_jobs)
                        }
                send_msg(conn, stats)
    except Exception as e:
        logging.error(f"Client error {addr}: {e}")
    finally:
        conn.close()
        logging.info(f"Client disconnected: {addr}")


def handle_worker(conn, addr):
    logging.info(f"Worker ready: {addr}")
    # Register worker as active
    with workers_lock:
        active_workers.add(addr)
    current_job = None
    try:
        while True:
            msg = recv_msg(conn)
            if not msg:
                break
            if msg['type'] == 'fetch':
                # Check for timed-out jobs and re-queue them
                current_time = time.time()
                timed_out_jobs = []
                for job_id, job_info in list(active_jobs.items()):
                    if current_time - job_info['timestamp'] > JOB_TIMEOUT:
                        timed_out_jobs.append((job_id, job_info))
                
                for job_id, job_info in timed_out_jobs:
                    active_jobs.pop(job_id, None)
                    # Treat as failure and retry
                    if job_id not in failed_jobs:
                        failed_jobs[job_id] = {'retry_count': 0, 'errors': [], 'job_data': job_info.get('job_data')}
                    
                    if failed_jobs[job_id]['retry_count'] < MAX_RETRIES:
                        failed_jobs[job_id]['retry_count'] += 1
                        failed_jobs[job_id]['errors'].append(f"Timeout: Job exceeded {JOB_TIMEOUT}s")
                        # Re-queue the job
                        if 'job_data' in failed_jobs[job_id] and failed_jobs[job_id]['job_data']:
                            job_queue.put(failed_jobs[job_id]['job_data'])
                        logging.warning(f"Job timeout detected: {job_id} (Timeout retry {failed_jobs[job_id]['retry_count']}/{MAX_RETRIES})")
                
                # Try to get a job without blocking long
                try:
                    job = job_queue.get(timeout=0.5)
                    current_job = job
                    active_jobs[job['job_id']] = {'worker_addr': addr, 'timestamp': time.time(), 'job_data': job}
                    send_msg(conn, {'type': 'job', 'job_id': job['job_id'], 'payload': job['payload']})
                    logging.info(f"Job assigned: {job['job_id']} to {addr}")
                except queue.Empty:
                    send_msg(conn, {'type': 'wait'})
            elif msg['type'] == 'complete':
                job_id = msg['job_id']
                active_jobs.pop(job_id, None)
                with results_lock:
                    results[job_id] = msg['result']
                    failed_jobs.pop(job_id, None)  # Clear failure tracking
                current_job = None
                logging.info(f"Job completed: {job_id}")
                send_msg(conn, {'type': 'ack'})
            elif msg['type'] == 'failed':
                job_id = msg['job_id']
                error = msg.get('error', 'Unknown error')
                active_jobs.pop(job_id, None)
                
                # Track failure and decide on retry
                if job_id not in failed_jobs:
                    failed_jobs[job_id] = {'retry_count': 0, 'errors': [], 'job_data': current_job}
                
                failed_jobs[job_id]['retry_count'] += 1
                failed_jobs[job_id]['errors'].append(error)
                
                if failed_jobs[job_id]['retry_count'] <= MAX_RETRIES:
                    # Re-queue for retry with backoff
                    retry_count = failed_jobs[job_id]['retry_count']
                    delay = RETRY_DELAY * (2 ** (retry_count - 1))
                    logging.warning(f"Job failed: {job_id} - Error: {error} (Retry {retry_count}/{MAX_RETRIES}, delaying {delay}s)")
                    time.sleep(delay)
                    job_queue.put(current_job)
                else:
                    # Max retries exceeded
                    logging.error(f"Job PERMANENTLY FAILED: {job_id} after {MAX_RETRIES} retries. Errors: {failed_jobs[job_id]['errors']}")
                    with results_lock:
                        results[job_id] = f"FAILED after {MAX_RETRIES} retries: {failed_jobs[job_id]['errors'][-1]}"
                
                current_job = None
                send_msg(conn, {'type': 'ack'})
    except Exception as e:
        logging.error(f"Worker error {addr}: {e}")
    finally:
        # Remove worker from active list
        with workers_lock:
            active_workers.discard(addr)
        # Re-queue on disconnect
        if current_job:
            job_id = current_job['job_id']
            active_jobs.pop(job_id, None)
            job_queue.put(current_job)
            logging.warning(f"Job re-queued: {job_id} (worker {addr} disconnected)")
        conn.close()
        logging.info(f"Worker disconnected: {addr}")


def handle_connection(conn, addr):
    try:
        msg = recv_msg(conn)
        if not msg:
            conn.close()
            return
        if 'client' in msg.get('type', '').lower():
            handle_client(conn, addr)
        else:
            handle_worker(conn, addr)
    except Exception as e:
        logging.error(f"Connection error {addr}: {e}")
        conn.close()


def main():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        ctx.load_cert_chain('certs/server.crt', 'certs/server.key')
    except FileNotFoundError:
        logging.error("SSL certificates not found. Run gen_certs.py first.")
        return
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((HOST, PORT))
        sock.listen(10)
        logging.info(f"Server listening on {HOST}:{PORT}")
        
        try:
            while True:
                raw_sock, addr = sock.accept()
                try:
                    ssl_sock = ctx.wrap_socket(raw_sock, server_side=True, do_handshake_on_connect=True)
                    threading.Thread(target=handle_connection, args=(ssl_sock, addr), daemon=True).start()
                except Exception:
                    try:
                        raw_sock.close()
                    except:
                        pass
        except KeyboardInterrupt:
            logging.info("Server shutting down...")


if __name__ == '__main__':
    main()
