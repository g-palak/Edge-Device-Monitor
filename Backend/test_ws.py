from fastapi import FastAPI, WebSocket
import uvicorn

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✅ Connected")
    try:
        while True:
            data = await websocket.receive_text()
            print(f"📨 Received: {data}")
            await websocket.send_text(f"Echo: {data}")
    except Exception as e:
        print(f"❌ Disconnected: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)