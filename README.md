# Distributed Job Queue System

**Project**: Distributed Job Queue (PES College CN Lab - Deliverable 2)  

---

## Quick Start

```bash
# 1. Generate SSL certificates (one-time)
python gen_certs.py

# 2. Start everything (default: 2 servers, 2 workers, GUI)
python startup.py

# 3. Submit jobs via GUI or CLI
python client.py client_1 5    # Submit 5 jobs

# 4. Monitor in GUI Dashboard (auto-opens)
```

Or customize: `python startup.py 3 10  # 3 servers, 10 workers`

---

## Architecture

Multi-server design with direct client/worker connections:

```
Clients/Workers ─SSL/TCP─┬─→ Server 1 (port 9000)
                         └─→ Server 2 (port 9001)
                         
Each server manages independent job queue & results
```

**Files**:
| File | Purpose |
|------|---------|
| `server_multi.py` | Job queue server (configurable port) |
| `client.py` | Job submission client |
| `worker.py` | Job execution worker |
| `workers.py` | Spawns N workers |
| `gui.py` | Tkinter dashboard (4 tabs) |
| `startup.py` | Launches all components |
| `gen_certs.py` | Generates SSL certificates |

---

## Features

✅ SSL/TLS encryption (self-signed certificates)  
✅ Thread-safe job queue  
✅ Automatic job retry on failure (max 3 retries)  
✅ Multiple concurrent clients/workers  
✅ 10s job timeout detection & re-queuing  
✅ Real-time GUI monitoring  
✅ Horizontal scaling (add servers as needed)  

---

## GUI Dashboard

4 tabs:
- **Dashboard**: Queue stats, active workers, job list
- **Submit Job**: Quick or batch job submission
- **Job History**: View submitted jobs and results
- **Settings**: Connection configuration

---

## Running

### Automated
```bash
python startup.py              # 2 servers, 2 workers
python startup.py 5 20        # 5 servers, 20 workers
```

### Manual
```bash
python server_multi.py 9000 &
python server_multi.py 9001 &
python workers.py 4 &
python gui.py &
python client.py test 10
```

---

## Job Submission

### CLI
```bash
python client.py app_name 10    # Submit 10 jobs
python client.py app_name 100   # Submit 100 jobs
```

### GUI
Submit Job tab → Enter job name → Click "Submit Now" + results show instantly

---

## Configuration

**Ports**: Server 1 (9000), Server 2 (9001), etc.

**Change client/worker target**:
```python
# In client.py or worker.py
HOST = 'localhost'
PORT = 9000  # Change port here
```

**Tuning** (in `server_multi.py`):
```python
MAX_RETRIES = 3       # Retry failed jobs N times
RETRY_DELAY = 1.0     # Wait 1s before retry
JOB_TIMEOUT = 10.0    # Timeout after 10s of no activity
```

---

## Protocol (JSON over SSL/TCP)

Messages are newline-terminated JSON:

**Client → Server**:
- `{"type": "register_client"}`
- `{"type": "submit", "payload": "job_description"}`
- `{"type": "status", "job_id": "uuid"}`

**Worker → Server**:
- `{"type": "register_worker"}`
- `{"type": "fetch"}`
- `{"type": "complete", "job_id": "uuid", "result": "output"}`
- `{"type": "failed", "job_id": "uuid", "error": "reason"}`

**Server → Client/Worker**:
- `{"type": "ack", "job_id": "uuid"}`
- `{"type": "result", "job_id": "uuid", "result": "output"}`
- `{"type": "pending", "job_id": "uuid"}`
- `{"type": "job", "job_id": "uuid", "payload": "..."}`
- `{"type": "wait"}`
- `{"type": "stats", ...}` (for GUI monitoring)

---

## Failure Handling

**Worker Crash**: Job times out (10s) → automatically re-queued  
**Network Disconnect**: Job status reverted to PENDING → re-queued  
**Job Failure**: Automatically retried (up to MAX_RETRIES times)  
**Server Crash**: In-memory state lost; restart server or connect to another

---

## Troubleshooting

**"Connection refused"**:
```bash
python server_multi.py 9000 &  # Start server first
python startup.py              # Or use startup script
```

**"Address already in use"**:
```powershell
Get-Process -Id (Get-NetTCPConnection -LocalPort 9000).OwningProcess | Stop-Process -Force
# Or use alternate port: python server_multi.py 9002
```

**Tkinter error (GUI doesn't open)**:
```bash
# Windows: Reinstall Python with Tkinter checked
# Linux: sudo apt-get install python3-tk
# macOS: Included with Python.org installer
```

**SSL Certificate Error**:
```bash
python gen_certs.py  # Regenerate certificates
# Restart server: python server_multi.py 9000
```

**Jobs stuck in PENDING**:
```bash
# Verify workers are running: Get-Process python
# Check server shows active workers in logs
python workers.py 2 &  # Start more workers
```

---

## Performance

**Benchmarks** (2 servers, 50 workers):
- Job submission: ~1ms
- Job fetch: ~100ms (0.5s timeout)
- Status query: ~10ms
- Concurrent connections: 50+/server

---

## Extension Examples

**Custom job processing** (in `worker.py`):
```python
def execute_job(payload, worker_id):
    if payload.startswith("image_"):
        return process_image(payload)
    return process_generic(payload)
```

**Add persistence** (in `server_multi.py`):
```python
import sqlite3
db = sqlite3.connect('jobs.db')
# Save results to database instead of memory
```

---

## Security

- SSL certificates generated: `certs/server.crt`, `certs/server.key`
- Self-signed (development/internal use)
- TLS 1.2+ protocol
- Regenerate anytime: `python gen_certs.py`

For production: Use CA-signed certificates, firewall rules, VPN for remote workers.

---

## Topics Covered

✅ Socket Programming (TCP/IP)  
✅ SSL/TLS Encryption  
✅ Multi-threading & Thread-safe Queues  
✅ Distributed System Design  
✅ Failure Recovery & Retries  
✅ JSON Protocol Design  