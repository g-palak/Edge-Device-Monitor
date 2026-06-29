import asyncio
import json
import random
import httpx
import websockets
from datetime import datetime
import sys

class DeviceSimulator:
    def __init__(self, device_id):
        self.device_id = device_id
        self.base_url = "http://localhost:8000"
        self.ws_url = "ws://localhost:8000/ws"
        self.running = True
        
    async def send_telemetry(self):
        """Send telemetry - THIS MUST RUN"""
        print(f"[{self.device_id}] 📡 Telemetry loop STARTED")
        
        # Use a single client for all requests
        async with httpx.AsyncClient() as client:
            while self.running:
                try:
                    metric = round(random.uniform(20.0, 100.0), 2)
                    payload = {
                        "device_id": self.device_id,
                        "ts": datetime.utcnow().isoformat(),
                        "metric": metric
                    }
                    
                    response = await client.post(
                        f"{self.base_url}/telemetry",
                        json=payload,
                        timeout=5.0
                    )
                    
                    if response.status_code == 200:
                        print(f"[{self.device_id}] 📊 {metric}")
                    else:
                        print(f"[{self.device_id}] HTTP {response.status_code}: {response.text}")
                        
                except httpx.ConnectError:
                    print(f"[{self.device_id}] ❌ Cannot connect to backend")
                except httpx.TimeoutException:
                    print(f"[{self.device_id}] ❌ Request timeout")
                except Exception as e:
                    print(f"[{self.device_id}] ❌ Error: {type(e).__name__}: {e}")
                
                # Wait 2-5 seconds
                await asyncio.sleep(random.uniform(2, 5))
    
    async def handle_config(self, data):
        """Handle config from server"""
        config_id = data["config_id"]
        print(f"[{self.device_id}] 🔧 Config #{config_id}: {data['config_data']}")
        
        # Simulate processing
        await asyncio.sleep(random.uniform(1, 3))
        
        # ACK
        status = "applied" if random.random() < 0.8 else "failed"
        async with httpx.AsyncClient() as client:
            try:
                await client.post(
                    f"{self.base_url}/configs/{config_id}/ack",
                    json={"config_id": config_id, "status": status},
                    timeout=5.0
                )
                print(f"[{self.device_id}] ✅ {status}")
            except Exception as e:
                print(f"[{self.device_id}] ❌ ACK failed: {e}")
    
    async def websocket_listener(self):
        """WebSocket for receiving configs"""
        while self.running:
            try:
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=None,  # Don't auto-ping
                    close_timeout=1
                ) as ws:
                    # Register
                    await ws.send(json.dumps({
                        "type": "device_connect",
                        "device_id": self.device_id
                    }))
                    
                    # Wait for confirmation
                    resp = await ws.recv()
                    data = json.loads(resp)
                    if data.get("type") == "connected":
                        print(f"[{self.device_id}] ✅ WS Connected")
                    
                    # Listen for configs
                    while self.running:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        
                        if data.get("type") == "config" and data.get("device_id") == self.device_id:
                            await self.handle_config(data)
                        # Ignore pong and other messages
                            
            except websockets.ConnectionClosed:
                print(f"[{self.device_id}] WS closed, reconnecting...")
            except Exception as e:
                print(f"[{self.device_id}] WS error: {e}")
            
            await asyncio.sleep(2)
    
    async def run(self):
        """Run both tasks"""
        print(f"\n[{self.device_id}] 🟢 STARTING")
        
        # Run BOTH tasks concurrently
        await asyncio.gather(
            self.send_telemetry(),
            self.websocket_listener()
        )

async def main():
    print("\n" + "="*50)
    print("DEVICE SIMULATOR")
    print("="*50)
    print("Starting 3 devices...\n")
    
    devices = [
        DeviceSimulator("device-001"),
        DeviceSimulator("device-002"),
        DeviceSimulator("device-003")
    ]
    
    # Run all devices
    await asyncio.gather(*[d.run() for d in devices])

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Shutdown")