#!/usr/bin/env python3
"""
Startup script for Distributed Job Queue System
Launches multiple optimized servers, workers, and GUI
"""

import subprocess
import sys
import time
import os
import signal
from pathlib import Path

class SystemLauncher:
    def __init__(self):
        self.processes = []
        self.base_port = 9000
        
    def launch_servers(self, num_servers=2):
        print(f"\n{'='*60}")
        print(f"Launching {num_servers} Server Instances")
        print(f"{'='*60}")
        for i in range(num_servers):
            port = self.base_port + i
            cmd = [sys.executable, "server_multi.py", str(port)]
            try:
                process = subprocess.Popen(cmd)
                self.processes.append(("Server", port, process))
                print(f"[✓] Server started on port {port} (PID: {process.pid})")
                time.sleep(0.5)
            except Exception as e:
                print(f"[✗] Failed to start server on port {port}: {e}")
    
    def show_architecture(self, num_servers=2):
        print(f"\n{'='*60}")
        print(f"Direct Server Architecture (Optimized for Scalability)")
        print(f"{'='*60}")
    
    def launch_workers(self, num_workers=2):
        print(f"\n{'='*60}")
        print(f"Launching {num_workers} Workers")
        print(f"{'='*60}")
        cmd = [sys.executable, "workers.py", str(num_workers)]
        try:
            # Don't capture output - show it live
            process = subprocess.Popen(cmd)
            self.processes.append(("Workers", "N/A", process))
            print(f"[✓] Worker launcher started (PID: {process.pid})")
            time.sleep(2)  # Wait longer for all workers to spawn
        except Exception as e:
            print(f"[✗] Failed to start workers: {e}")
    
    def launch_gui(self):
        print(f"\n{'='*60}")
        print(f"Launching GUI Dashboard")
        print(f"{'='*60}")
        
        cmd = [sys.executable, "gui.py"]
        try:
            process = subprocess.Popen(cmd)
            self.processes.append(("GUI", "N/A", process))
            print(f"[✓] GUI Dashboard started (PID: {process.pid})")
        except Exception as e:
            print(f"[✗] Failed to start GUI: {e}")
    
    def show_status(self):
        print(f"\n{'='*60}")
        print("System Status")
        print(f"{'='*60}")
        alive = []
        dead = []
        for name, port, process in self.processes:
            status = "✓ Running" if process.poll() is None else "✗ Stopped"
            port_str = f":{port}" if isinstance(port, int) else ""
            alive.append((name, port, status)) if process.poll() is None else dead.append((name, port, status))
            print(f"[{status}] {name}{port_str} (PID: {process.pid})")
        return len(alive), len(dead)
    
    def cleanup(self):
        print(f"\n{'='*60}")
        print("Shutting Down System")
        print(f"{'='*60}")
        for name, port, process in reversed(self.processes):
            try:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                        print(f"[✓] Terminated {name}")
                    except subprocess.TimeoutExpired:
                        process.kill()
                        print(f"[✓] Force-killed {name}")
            except Exception as e:
                print(f"[✗] Error terminating {name}: {e}")

    def run_interactive(self):
        print(f"\n{'='*60}")
        print("Interactive Mode")
        print(f"{'='*60}")
        print("\nCommands:")
        print("  status   - Show system status")
        print("  exit     - Exit and shutdown system")
        print()
        try:
            while True:
                cmd = input(">>> ").strip().lower()
                if cmd == 'status':
                    alive, dead = self.show_status()
                    print(f"Summary: {alive} alive, {dead} stopped")
                elif cmd == 'exit':
                    break
                else:
                    print("Unknown command")
        except KeyboardInterrupt:
            print()

def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║  Distributed Job Queue System - Startup Launcher          ║
╚═══════════════════════════════════════════════════════════╝
    """)
    num_servers = 2
    num_workers = 2
    launch_gui = True
    
    if len(sys.argv) > 1:
        try:
            num_servers = int(sys.argv[1])
        except ValueError:
            print(f"Usage: python startup.py [num_servers] [num_workers] [--no-gui]")
            sys.exit(1)
    if len(sys.argv) > 2:
        try:
            num_workers = int(sys.argv[2])
        except ValueError:
            pass
    if "--no-gui" in sys.argv:
        launch_gui = False
    launcher = SystemLauncher()
    try:
        launcher.launch_servers(num_servers)
        time.sleep(1)
        launcher.show_architecture(num_servers)
        time.sleep(1)
        launcher.launch_workers(num_workers)
        time.sleep(1)
        if launch_gui:
            launcher.launch_gui()
        launcher.show_status()
        print(f"\n{'='*60}")
        print("SYSTEM READY")
        print(f"{'='*60}")
        print()
        print("Connection Details:")
        print(f"  • Servers: ports {launcher.base_port}-{launcher.base_port + num_servers - 1}")
        print(f"  • Workers: {num_workers} instances connected")
        print()
        print("Usage:")
        print(f"  • GUI: Auto-connects to port 9000       ")
        print(f"  • CLI: python client.py <client_id> <num_jobs>")
        print()
        print("Press Ctrl+C to shutdown system...")
        print()
        launcher.run_interactive()
    except KeyboardInterrupt:
        print()
    finally:
        launcher.cleanup()
        print("\nSystem shutdown complete.")

if __name__ == '__main__':
    main()
