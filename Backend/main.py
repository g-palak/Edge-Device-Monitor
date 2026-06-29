from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from datetime import datetime

from database import engine, get_db, Base, init_db
from model import Telemetry, DeviceConfig, ConfigStatus
from schema import TelemetryCreate, TelemetryResponse, ConfigCreate, ConfigResponse, ConfigAck

init_db()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global WebSocket storage
device_ws = {}       # device_id -> websocket
frontend_ws = []     # list of frontend websockets

@app.get("/")
async def root():
    return {"status": "ok", "devices": list(device_ws.keys()), "frontends": len(frontend_ws)}

@app.post("/telemetry", response_model=TelemetryResponse)
async def ingest_telemetry(telemetry: TelemetryCreate, db: Session = Depends(get_db)):
    # Store in database
    t = Telemetry(device_id=telemetry.device_id, ts=telemetry.ts, metric=telemetry.metric)
    db.add(t)
    db.commit()
    db.refresh(t)
    
    # Broadcast to ALL frontend connections
    msg = {
        "id": t.id,
        "device_id": t.device_id,
        "ts": t.ts.isoformat(),
        "metric": t.metric,
        "type": "telemetry"
    }
    
    # Send to frontends
    disconnected = []
    for ws in frontend_ws:
        try:
            await ws.send_json(msg)
        except:
            disconnected.append(ws)
    
    # Clean up disconnected frontends
    for ws in disconnected:
        if ws in frontend_ws:
            frontend_ws.remove(ws)
    
    return t

@app.get("/telemetry", response_model=List[TelemetryResponse])
async def get_telemetry(device_id: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(Telemetry)
    if device_id:
        query = query.filter(Telemetry.device_id == device_id)
    return query.order_by(Telemetry.ts.desc()).limit(limit).all()

@app.get("/devices")
async def get_devices(db: Session = Depends(get_db)):
    devices = db.query(Telemetry.device_id).distinct().all()
    return [d[0] for d in devices]

@app.post("/devices/{device_id}/config", response_model=ConfigResponse)
async def push_config(device_id: str, config: ConfigCreate, db: Session = Depends(get_db)):
    print(f"\n🔧 CONFIG -> {device_id}: {config.config_data}")
    
    c = DeviceConfig(
        device_id=device_id,
        config_data=json.dumps(config.config_data),
        status=ConfigStatus.PENDING
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    
    msg = {
        "type": "config",
        "config_id": c.id,
        "device_id": device_id,
        "config_data": config.config_data
    }
    
    if device_id in device_ws:
        try:
            await device_ws[device_id].send_json(msg)
            print(f"  ✅ Sent to {device_id}")
        except:
            del device_ws[device_id]
            print(f"  ❌ Failed, removed {device_id}")
    else:
        print(f"  ❌ {device_id} not connected. Online: {list(device_ws.keys())}")
    
    return c

@app.get("/devices/{device_id}/configs", response_model=List[ConfigResponse])
async def get_device_configs(device_id: str, db: Session = Depends(get_db)):
    return db.query(DeviceConfig).filter(
        DeviceConfig.device_id == device_id
    ).order_by(DeviceConfig.created_at.desc()).all()

@app.post("/configs/{config_id}/ack")
async def acknowledge_config(config_id: int, ack: ConfigAck, db: Session = Depends(get_db)):
    print(f"\n📥 ACK #{config_id}: {ack.status}")
    
    c = db.query(DeviceConfig).filter(DeviceConfig.id == config_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Config not found")
    
    c.status = ack.status
    if ack.status == ConfigStatus.APPLIED:
        c.applied_at = datetime.utcnow()
    db.commit()
    db.refresh(c)
    print(f"  Status: {c.status}")
    
    # Notify frontends
    msg = {
        "type": "config_update",
        "config_id": c.id,
        "device_id": c.device_id,
        "status": c.status,
        "applied_at": c.applied_at.isoformat() if c.applied_at else None
    }
    
    disconnected = []
    for ws in frontend_ws:
        try:
            await ws.send_json(msg)
        except:
            disconnected.append(ws)
    
    for ws in disconnected:
        if ws in frontend_ws:
            frontend_ws.remove(ws)
    
    return {"status": "success"}

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Default: treat as frontend
    role = "frontend"
    dev_id = None
    
    # Add to frontend list immediately
    frontend_ws.append(websocket)
    print(f"👤 Frontend connected. Total frontends: {len(frontend_ws)}", flush=True)
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg.get("type") == "device_connect":
                # Switch from frontend to device
                if websocket in frontend_ws:
                    frontend_ws.remove(websocket)
                role = "device"
                dev_id = msg["device_id"]
                device_ws[dev_id] = websocket
                await websocket.send_json({"type": "connected"})
                print(f"📝 Device registered: {dev_id}. Devices: {list(device_ws.keys())}", flush=True)
            
            elif msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
    except WebSocketDisconnect:
        print(f"🔌 {role} disconnected: {dev_id or ''}", flush=True)
    except Exception as e:
        print(f"❌ Error: {e}", flush=True)
    finally:
        if role == "device" and dev_id in device_ws:
            del device_ws[dev_id]
        elif websocket in frontend_ws:
            frontend_ws.remove(websocket)
        print(f"Cleanup done. Frontends: {len(frontend_ws)}, Devices: {list(device_ws.keys())}", flush=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)