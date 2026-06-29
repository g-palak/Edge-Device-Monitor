# Edge Device Monitor

A real-time telemetry monitoring system demonstrating cloud↔edge device communication patterns. Built with FastAPI, React, and WebSockets.

## Problem Statement

- Backend in Python/FastAPI: a POST endpoint that ingests telemetry from simulated edge devices (JSON: device_id, ts, metric), stores it (SQLite or Postgres is fine), and streams live updates to the frontend (WebSocket or SSE). Plus POST /devices/{id}/config that "pushes" a config to a device and tracks its applied state (pending -> applied). 
- Frontend in React: a small dashboard showing live telemetry from 2-3 devices, plus a form to push a config change and show the round-trip. 
- A short script that simulates the devices sending telemetry and ack-ing the config. 

---
## Architecture:
```METRICS FLOW (one-way stream)
═══════════════════════════════════════════════════════════════
  SIMULATOR ──HTTP POST /telemetry──► BACKEND ──WS broadcast──► FRONTEND
  (every 2-5s)                       (store in      (live chart
                                     SQLite)        updates)


CONFIG FLOW (round-trip with state tracking)
═══════════════════════════════════════════════════════════════
  FRONTEND ──HTTP POST /config──► BACKEND ──WS send──► SIMULATOR
  (user pushes                   (save as        (receives config,
   config form)                   PENDING)        processes 1-3s)
       ▲                                           │
       │          WS broadcast                    │ HTTP POST /ack
       └────────── (status update) ◄──────────────┘ (applied/failed)


CONFIG STATES
═══════════════════════════════════════════════════════════════
  User pushes config ──► PENDING ──80%──► APPLIED
                          │
                          └──20%──► FAILED
```
---
## Images of the running app:
<img width="937" height="415" alt="image" src="https://github.com/user-attachments/assets/85e2e4d0-85b9-4d04-942c-d378f22eafda" />
<img width="928" height="404" alt="image" src="https://github.com/user-attachments/assets/8c8af0ce-22e1-405e-aab1-d0bb5d6ea666" />

---

## Design Decisions

### Database: SQLite
Chose SQLite over PostgreSQL for this prototype because it mirrors the embedded nature of edge systems — no separate server process, zero configuration, and the database is a single portable file. In production, this would be TimescaleDB or QuestDB for time-series optimization, but SQLite demonstrates the pattern without infrastructure overhead. The schema uses JSON strings for config data rather than typed columns, since different device types have different configuration schemas.

### Real-time Communication: WebSockets
WebSockets provide bidirectional (as compared to SSE), persistent connections — critical for edge systems where the cloud needs to push configs to devices without polling. The backend maintains separate channels: frontend clients receive all telemetry broadcasts, while each device gets its own channel and only receives configs addressed to it. This mirrors the security boundary between monitoring dashboards and device command-and-control.

### Single main.py for Backend
All endpoints live in one file deliberately — this is a focused prototype demonstrating the core pattern, not a production microservice. In a real deployment, routes would be split into routers (telemetry, config, websocket), database operations into repositories, and WebSocket management into a separate service. The current structure makes the entire cloud↔device flow traceable in a single file, which is the point of this exercise.

### Separate Model and Schema Layers
SQLAlchemy models define the database structure (tables, columns, relationships), while Pydantic schemas define API contracts (request/response validation). This separation means the database can evolve independently of the API — we could add columns to the telemetry table without breaking existing clients. The schemas also auto-generate OpenAPI documentation via FastAPI.

### Async Config Flow (Pending → Applied/Failed)
Config push is not synchronous request-response. When a user pushes a config, the backend immediately persists it as "pending" and sends it via WebSocket to the device. The device processes it (potentially seconds later) and acknowledges via a separate HTTP endpoint. This models real edge deployments where devices may be offline or slow to respond. The server tracks state transitions, and the frontend observes them via WebSocket broadcasts.

### Device Simulator as Separate Process
The simulator has no database access and communicates only via HTTP POST (telemetry) and WebSocket (receiving configs). This is identical to how a real edge device would interact with cloud services — it's a client, not part of the server. It simulates realistic behavior: random telemetry intervals (2-5s), config processing delays (1-3s), and an 80% success rate for config application.

### Endpoint
POST /telemetry + GET /telemetry
Write and read separation. Devices need to send data (POST). The frontend needs to fetch historical data on page load (GET) — WebSocket only streams live updates, it doesn't replay past data. Without GET, refreshing the browser shows an empty dashboard.

POST /devices/{id}/config
The command channel. This is how the cloud tells a device to change its behavior (sampling rate, thresholds, firmware settings). It creates a config record with status "pending" and pushes to the device via WebSocket. Without this, there's no way to control devices remotely — which is the entire point of an edge management platform.

GET /devices/{id}/configs
Audit trail. Shows the history of every config ever pushed to a device — what was changed, when, and whether it succeeded or failed. Critical for debugging ("why is device-001 behaving differently?") and compliance. Without this, config changes are invisible.

POST /configs/{id}/ack
Closes the loop. The device calls this after processing a config to report "applied" or "failed." This is what moves configs from pending → applied/failed. It's a separate endpoint (not part of /telemetry) because config acknowledgment is a different concern than sensor data — different priority, different reliability requirements, different consumers.

WS /ws
Real-time channel. HTTP is request-response; WebSocket is persistent push. Telemetry is broadcast to all dashboards instantly. Configs are pushed to specific devices without polling. Without this, the frontend would need to refresh every few seconds to see new data — not "live monitoring."

---

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- npm

### Option 1: Automated Scripts
```bash
./setup.sh    # Installs all dependencies
./run.sh      # Starts backend, simulator, and frontend
```


### Option 2: 
- Terminal 1 - Backend
```cd backend && pip install -r requirements.txt && python3 main.py```

- Terminal 2 - Device Simulator
```cd simulator && pip install httpx websockets && python3 device_simulator.py```

- Terminal 3 - Frontend
```cd frontend && npm install && npm start```

## Issues faced:
### WebSocket Connections Closing Immediately
Problem: Devices connected successfully but disconnected within seconds, preventing config delivery and acknowledgment. The backend log showed "WebSocket connection closed" immediately after "Connected."

Root Cause: The websockets library version (15.x) had API changes from earlier versions. Additionally, the backend's ConnectionManager.connect() was calling websocket.accept() which FastAPI had already called internally, causing a "Expected ASGI message 'websocket.send' but got 'websocket.accept'" error.

Solution:
- Moved websocket.accept() to the endpoint level (FastAPI requirement)
- Changed default connection type to "frontend" since browsers don't send identification messages
- Device connections are identified when they send {"type": "device_connect"}
- Added ping/pong keepalive to prevent timeout disconnections

### Config ACK Not Changing Status
Problem: Configs stayed in "pending" state indefinitely. The simulator wasn't receiving configs because the WebSocket routing was broken.

Solution: Implemented device-specific WebSocket channels. When a device connects, it sends its device_id, and the backend adds it to a named channel. Config pushes target specific device channels rather than broadcasting to all connections.


## Learnings:
- Edge-cloud communication patterns: Devices push telemetry via HTTP, cloud pushes commands via WebSocket. State is tracked asynchronously (pending→applied/failed) because edge devices are inherently unreliable and may be offline or slow to respond. This decoupling is the foundation of IoT command-and-control systems. Found it similar to my arduino experience in college.
- WebSocket connection management.
- FastAPI's type-driven development.
