import subprocess
import sys
import time
import signal
import os

def spawn_workers(num_workers):
    """Spawn multiple worker processes"""
    processes = []
    print(f"\n[*] Spawning {num_workers} workers...")
    for i in range(num_workers):
        worker_id = f"worker_{i+1}"
        try:
            process = subprocess.Popen(
                [sys.executable, "worker.py", worker_id],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            processes.append((worker_id, process))
            print(f"    [{i+1}/{num_workers}] Started {worker_id} (PID: {process.pid})")
            time.sleep(0.05)  # Small delay between spawns
        except Exception as e:
            print(f"[✗] Failed to start {worker_id}: {e}")
    
    print(f"\n[✓] All {len(processes)} workers spawned successfully!")
    print(f"[*] Monitoring workers... Press Ctrl+C to stop all.\n")
    try:
        while True:
            alive_count = sum(1 for _, p in processes if p.poll() is None)
            if alive_count == 0:
                print("[!] All workers have exited.")
                break
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n\n[*] Shutting down all workers...")
        for worker_id, process in processes:
            try:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                        print(f"    [✓] Terminated {worker_id}")
                    except subprocess.TimeoutExpired:
                        process.kill()
                        print(f"    [✓] Force-killed {worker_id}")
            except Exception as e:
                print(f"    [✗] Error with {worker_id}: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python workers.py <number_of_workers>")
        print("Example: python workers.py 5")
        sys.exit(1)
    
    try:
        num_workers = int(sys.argv[1])
        if num_workers <= 0:
            print("Error: number of workers must be > 0")
            sys.exit(1)
        spawn_workers(num_workers)
    except ValueError:
        print(f"Error: '{sys.argv[1]}' is not a valid number")
        sys.exit(1)

if __name__ == '__main__':
    main()
