import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import socket
import ssl
import json
import threading
import time
from collections import defaultdict

class JobQueueGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Distributed Job Queue - Monitor & Control")
        self.root.geometry("1000x700")
        self.host = 'localhost'
        self.port = 9000  # Direct server connection (no load balancer)
        self.ssl_context = None
        self._setup_ssl()
        self.jobs = {}
        self.workers_count = 0
        self.queue_size = 0
        self.update_thread = None
        self.running = True
        self._build_ui()
        self._start_update_loop()
    
    def _setup_ssl(self):
        try:
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            self.ssl_context.load_verify_locations('certs/server.crt')
        except Exception as e:
            messagebox.showerror("SSL Error", f"Failed to load certificates: {e}")
    
    def _build_ui(self):
        header = ttk.Frame(self.root)
        header.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(header, text="Distributed Job Queue System", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        self.status_label = ttk.Label(header, text="Status: Connecting...", foreground="orange")
        self.status_label.pack(side=tk.RIGHT)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.dashboard_tab = ttk.Frame(notebook)
        notebook.add(self.dashboard_tab, text="Dashboard")
        self._build_dashboard_tab()
        self.submit_tab = ttk.Frame(notebook)
        notebook.add(self.submit_tab, text="Submit Job")
        self._build_submit_tab()
        self.history_tab = ttk.Frame(notebook)
        notebook.add(self.history_tab, text="Job History")
        self._build_history_tab()
        self.settings_tab = ttk.Frame(notebook)
        notebook.add(self.settings_tab, text="Settings")
        self._build_settings_tab()
    
    def _build_dashboard_tab(self):
        stats_frame = ttk.LabelFrame(self.dashboard_tab, text="System Statistics")
        stats_frame.pack(fill=tk.X, padx=10, pady=10)
        self.queue_label = ttk.Label(stats_frame, text="Queue Size: 0", font=("Arial", 12, "bold"))
        self.queue_label.pack(pady=5)
        self.workers_label = ttk.Label(stats_frame, text="Active Workers: 0", font=("Arial", 12, "bold"))
        self.workers_label.pack(pady=5)
        self.pending_label = ttk.Label(stats_frame, text="Pending Jobs: 0", font=("Arial", 12, "bold"))
        self.pending_label.pack(pady=5)
        self.completed_label = ttk.Label(stats_frame, text="Completed Jobs: 0", font=("Arial", 12, "bold"))
        self.completed_label.pack(pady=5)
        jobs_frame = ttk.LabelFrame(self.dashboard_tab, text="Recent Jobs")
        jobs_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        columns = ("Job ID", "Payload", "Status", "Result")
        self.jobs_tree = ttk.Treeview(jobs_frame, columns=columns, height=15)
        self.jobs_tree.column("#0", width=0, stretch=tk.NO)
        self.jobs_tree.column("Job ID", width=150)
        self.jobs_tree.column("Payload", width=200)
        self.jobs_tree.column("Status", width=100)
        self.jobs_tree.column("Result", width=350)
        self.jobs_tree.heading("#0", text="")
        self.jobs_tree.heading("Job ID", text="Job ID")
        self.jobs_tree.heading("Payload", text="Payload")
        self.jobs_tree.heading("Status", text="Status")
        self.jobs_tree.heading("Result", text="Result")
        scrollbar = ttk.Scrollbar(jobs_frame, orient=tk.VERTICAL, command=self.jobs_tree.yview)
        self.jobs_tree.configure(yscroll=scrollbar.set)
        self.jobs_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _build_submit_tab(self):
        # Quick submit section
        quick_frame = ttk.LabelFrame(self.submit_tab, text="Quick Submit (Single Job)")
        quick_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(quick_frame, text="Job Name/Task:", font=("Arial", 10)).pack(anchor=tk.W, padx=10, pady=5)
        self.quick_payload_entry = ttk.Entry(quick_frame, width=60, font=("Arial", 10))
        self.quick_payload_entry.pack(fill=tk.X, padx=10, pady=5)
        self.quick_payload_entry.insert(0, "task_example")
        
        quick_button_frame = ttk.Frame(quick_frame)
        quick_button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(quick_button_frame, text="✓ Submit Now", command=self._quick_submit_job).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_button_frame, text="Clear", command=lambda: self.quick_payload_entry.delete(0, tk.END)).pack(side=tk.LEFT, padx=5)
        
        self.quick_result = ttk.Label(quick_frame, text="", foreground="green", font=("Arial", 10, "bold"))
        self.quick_result.pack(anchor=tk.W, padx=10, pady=5)
        
        # Batch submit section
        batch_frame = ttk.LabelFrame(self.submit_tab, text="Batch Submit (Multiple Jobs)")
        batch_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        ttk.Label(batch_frame, text="Enter job names (one per line):", font=("Arial", 10)).pack(anchor=tk.W, padx=10, pady=5)
        self.payload_text = tk.Text(batch_frame, height=8, width=60, font=("Courier", 10))
        self.payload_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.payload_text.insert(1.0, "task_1\ntask_2\ntask_3")
        
        batch_button_frame = ttk.Frame(batch_frame)
        batch_button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(batch_button_frame, text="✓ Submit All", command=self._submit_batch_jobs).pack(side=tk.LEFT, padx=5)
        ttk.Button(batch_button_frame, text="Clear", command=lambda: self.payload_text.delete(1.0, tk.END)).pack(side=tk.LEFT, padx=5)
        ttk.Button(batch_button_frame, text="📋 Example", command=self._load_example).pack(side=tk.LEFT, padx=5)
        
        self.submit_result = ttk.Label(batch_frame, text="", foreground="green", font=("Arial", 10, "bold"))
        self.submit_result.pack(anchor=tk.W, padx=10, pady=5)
    
    def _build_history_tab(self):
        history_frame = ttk.Frame(self.history_tab)
        history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        ttk.Label(history_frame, text="Complete Job History", font=("Arial", 12, "bold")).pack()
        self.history_text = scrolledtext.ScrolledText(history_frame, height=25, width=100)
        self.history_text.pack(fill=tk.BOTH, expand=True, pady=10)
        ttk.Button(history_frame, text="Clear History", command=self._clear_history).pack()
    
    def _build_settings_tab(self):
        settings_frame = ttk.LabelFrame(self.settings_tab, text="Connection Settings")
        settings_frame.pack(fill=tk.X, padx=20, pady=20)
        ttk.Label(settings_frame, text="Server Host:").grid(row=0, column=0, pady=5, padx=5)
        self.host_entry = ttk.Entry(settings_frame, width=30)
        self.host_entry.insert(0, self.host)
        self.host_entry.grid(row=0, column=1, pady=5, padx=5)
        ttk.Label(settings_frame, text="Server Port:").grid(row=1, column=0, pady=5, padx=5)
        self.port_entry = ttk.Entry(settings_frame, width=30)
        self.port_entry.insert(0, str(self.port))
        self.port_entry.grid(row=1, column=1, pady=5, padx=5)
        button_frame = ttk.Frame(settings_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        ttk.Button(button_frame, text="Connect", command=self._update_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Test Connection", command=self._test_connection).pack(side=tk.LEFT, padx=5)
    
    def _quick_submit_job(self):
        """Submit a single job quickly"""
        payload = self.quick_payload_entry.get().strip()
        if not payload:
            messagebox.showwarning("Empty", "Please enter a job name")
            return
        
        try:
            sock = socket.create_connection((self.host, self.port), timeout=5)
            with self.ssl_context.wrap_socket(sock, server_hostname='localhost') as ssock:
                # Register as client first
                ssock.sendall(json.dumps({'type': 'register_client'}).encode() + b'\n')
                
                # Submit job
                msg = {'type': 'submit', 'payload': payload}
                ssock.sendall(json.dumps(msg).encode() + b'\n')
                response = self._recv_msg(ssock)
                
                if response and response.get('job_id'):
                    job_id = response['job_id']
                    self.jobs[job_id] = {'payload': payload, 'status': 'pending', 'result': None}
                    self.quick_result.config(text=f"✓ Submitted Job ID: {job_id[:8]}...", foreground="green")
                    
                    # Auto-clear after 3 seconds
                    self.root.after(3000, lambda: self.quick_result.config(text=""))
                    self.quick_payload_entry.delete(0, tk.END)
                    self.quick_payload_entry.insert(0, "task_example")
                else:
                    self.quick_result.config(text="✗ Server error - check connection", foreground="red")
        except Exception as e:
            self.quick_result.config(text=f"✗ Error: {str(e)[:40]}", foreground="red")
    
    def _submit_batch_jobs(self):
        """Submit multiple jobs at once"""
        payloads = [line.strip() for line in self.payload_text.get(1.0, tk.END).split('\n') if line.strip()]
        
        if not payloads:
            messagebox.showwarning("Empty", "Please enter at least one job")
            return
        
        try:
            submitted_count = 0
            failed_count = 0
            job_ids = []
            
            for payload in payloads:
                try:
                    sock = socket.create_connection((self.host, self.port), timeout=5)
                    with self.ssl_context.wrap_socket(sock, server_hostname='localhost') as ssock:
                        # Register as client
                        ssock.sendall(json.dumps({'type': 'register_client'}).encode() + b'\n')
                        
                        # Submit job
                        msg = {'type': 'submit', 'payload': payload}
                        ssock.sendall(json.dumps(msg).encode() + b'\n')
                        response = self._recv_msg(ssock)
                        
                        if response and response.get('job_id'):
                            job_id = response['job_id']
                            self.jobs[job_id] = {'payload': payload, 'status': 'pending', 'result': None}
                            job_ids.append(job_id)
                            submitted_count += 1
                        else:
                            failed_count += 1
                except Exception as e:
                    failed_count += 1
            
            if submitted_count > 0:
                self.submit_result.config(
                    text=f"✓ Submitted {submitted_count} jobs {f'({failed_count} failed)' if failed_count > 0 else ''}",
                    foreground="green"
                )
                self.payload_text.delete(1.0, tk.END)
            else:
                self.submit_result.config(text="✗ Failed to submit any jobs", foreground="red")
                
        except Exception as e:
            self.submit_result.config(text=f"✗ Error: {str(e)[:40]}", foreground="red")
    
    def _load_example(self):
        """Load example jobs"""
        examples = "data_processing_task\ncompute_average\ngenerate_report\nbackup_database\nvalidate_input\nprocess_image\ncalculate_sum\nsorting_task"
        self.payload_text.delete(1.0, tk.END)
        self.payload_text.insert(1.0, examples)
    
    def _submit_job(self):
        """Legacy method - redirects to batch submit"""
        self._submit_batch_jobs()

    def _test_connection(self):
        try:
            sock = socket.create_connection((self.host, self.port), timeout=2)
            sock.close()
            messagebox.showinfo("Success", f"Connected to {self.host}:{self.port}")
        except Exception as e:
            messagebox.showerror("Connection Failed", f"Cannot connect: {e}")
    
    def _update_connection(self):
        self.host = self.host_entry.get() or 'localhost'
        try:
            self.port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Invalid Port", "Port must be a number")
            return
        messagebox.showinfo("Settings Updated", f"Now connecting to {self.host}:{self.port}")
    
    def _clear_history(self):
        self.history_text.delete(1.0, tk.END)
    
    def _update_history(self):
        """Update history tab with completed jobs"""
        completed_jobs = {jid: jdata for jid, jdata in self.jobs.items() if jdata['status'] == 'completed'}
        
        if not completed_jobs:
            return
        
        self.history_text.delete(1.0, tk.END)
        
        for job_id, job_data in sorted(completed_jobs.items(), reverse=True):
            payload = job_data.get('payload', 'N/A')
            result = job_data.get('result', 'N/A')
            
            # Format output
            output = f"Job ID: {job_id}\n"
            output += f"Payload: {payload}\n"
            output += f"Result: {result}\n"
            output += "-" * 80 + "\n\n"
            
            self.history_text.insert(tk.END, output)
    
    def _update_history(self):
        """Update history tab with completed jobs"""
        completed_jobs = {jid: jdata for jid, jdata in self.jobs.items() if jdata['status'] == 'completed'}
        
        if not completed_jobs:
            return
        
        self.history_text.delete(1.0, tk.END)
        
        for job_id, job_data in sorted(completed_jobs.items(), reverse=True):
            payload = job_data.get('payload', 'N/A')
            result = job_data.get('result', 'N/A')
            
            # Format output
            output = f"Job ID: {job_id}\n"
            output += f"Payload: {payload}\n"
            output += f"Result: {result}\n"
            output += "-" * 80 + "\n\n"
            
            self.history_text.insert(tk.END, output)
    
    def _recv_msg(self, conn):
        try:
            buf = b''
            while True:
                byte = conn.recv(1)
                if not byte:
                    return None
                if byte == b'\n':
                    break
                buf += byte
            return json.loads(buf.decode()) if buf else None
        except:
            return None
    
    def _start_update_loop(self):
        def update_loop():
            while self.running:
                try:
                    # Query server for stats
                    self._fetch_server_stats()
                    
                    # Query server for job status updates
                    self._fetch_job_status()
                    
                    completed = sum(1 for j in self.jobs.values() if j['status'] == 'completed')
                    pending = sum(1 for j in self.jobs.values() if j['status'] == 'pending')
                    self.root.after(0, lambda: self.queue_label.config(text=f"Queue Size: {self.queue_size}"))
                    self.root.after(0, lambda: self.pending_label.config(text=f"Pending Jobs: {pending}"))
                    self.root.after(0, lambda: self.completed_label.config(text=f"Completed Jobs: {completed}"))
                    self.root.after(0, lambda: self.workers_label.config(text=f"Active Workers: {self.workers_count}"))
                    self.root.after(0, self._update_jobs_tree)
                    self.root.after(0, self._update_history)
                    self.root.after(0, self._update_history)
                    try:
                        sock = socket.create_connection((self.host, self.port), timeout=2)
                        sock.close()
                        self.root.after(0, lambda: self.status_label.config(text="Status: Connected ✓", foreground="green"))
                    except:
                        self.root.after(0, lambda: self.status_label.config(text="Status: Disconnected ✗", foreground="red"))
                    time.sleep(2)
                except Exception as e:
                    print(f"Update error: {e}")
                    time.sleep(2)
        self.update_thread = threading.Thread(target=update_loop, daemon=True)
        self.update_thread.start()
    
    def _fetch_server_stats(self):
        """Query server for system statistics (active workers, queue size, etc.)"""
        try:
            sock = socket.create_connection((self.host, self.port), timeout=5)
            with self.ssl_context.wrap_socket(sock, server_hostname='localhost') as ssock:
                # Register as client
                ssock.sendall(json.dumps({'type': 'register_client'}).encode() + b'\n')
                
                # Request stats
                msg = {'type': 'stats'}
                ssock.sendall(json.dumps(msg).encode() + b'\n')
                response = self._recv_msg(ssock)
                
                if response and response.get('type') == 'stats':
                    # Update displayed statistics
                    self.queue_size = response.get('queue_size', 0)
                    self.workers_count = response.get('active_workers', 0)
        except Exception as e:
            pass  # Server not available
    
    def _fetch_job_status(self):
        """Query server for status of pending jobs"""
        pending_jobs = [jid for jid, jdata in self.jobs.items() if jdata['status'] == 'pending']
        
        if not pending_jobs:
            return
        
        try:
            sock = socket.create_connection((self.host, self.port), timeout=5)
            with self.ssl_context.wrap_socket(sock, server_hostname='localhost') as ssock:
                # Register as client
                ssock.sendall(json.dumps({'type': 'register_client'}).encode() + b'\n')
                
                # Query each pending job
                for job_id in pending_jobs:
                    try:
                        msg = {'type': 'status', 'job_id': job_id}
                        ssock.sendall(json.dumps(msg).encode() + b'\n')
                        response = self._recv_msg(ssock)
                        
                        if response:
                            if response.get('type') == 'result':
                                # Job completed
                                self.jobs[job_id]['status'] = 'completed'
                                self.jobs[job_id]['result'] = response.get('result', 'N/A')
                            elif response.get('type') == 'pending':
                                # Still pending
                                pass
                            elif response.get('type') == 'error':
                                # Job failed
                                self.jobs[job_id]['status'] = 'failed'
                                self.jobs[job_id]['result'] = response.get('message', 'Unknown error')
                    except Exception as e:
                        pass  # Continue with other jobs
        except Exception as e:
            pass  # Server not available
    
    def _update_jobs_tree(self):
        for item in self.jobs_tree.get_children():
            self.jobs_tree.delete(item)
        for job_id, job_data in sorted(self.jobs.items(), reverse=True)[:20]:
            status = job_data['status']
            payload = job_data['payload'][:40] + "..." if len(job_data['payload']) > 40 else job_data['payload']
            result = job_data.get('result', '')[:50] + "..." if job_data.get('result') and len(job_data['result']) > 50 else job_data.get('result', '')
            tag = 'completed' if status == 'completed' else 'failed' if status == 'failed' else 'pending'
            self.jobs_tree.insert("", 0, 
                values=(
                    job_id[:12] + "...",
                    payload,
                    status.upper(),
                    result if result else "—"
                ),
                tags=(tag,))
        self.jobs_tree.tag_configure('completed', foreground='green')
        self.jobs_tree.tag_configure('pending', foreground='orange')
        self.jobs_tree.tag_configure('failed', foreground='red')
    
    def on_closing(self):
        self.running = False
        if self.update_thread:
            self.update_thread.join(timeout=2)
        self.root.destroy()

def main():
    root = tk.Tk()
    app = JobQueueGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == '__main__':
    main()
