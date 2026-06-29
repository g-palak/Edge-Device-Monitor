#!/bin/bash
echo "Starting Edge Device Monitor..."

# Start backend
cd backend
source venv/bin/activate
python3 main.py &
BACKEND_PID=$!

# Start simulator
cd ../simulator
python3 device_simulator.py &
SIMULATOR_PID=$!

# Start frontend
cd ../frontend
npm start &
FRONTEND_PID=$!

echo "All services running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop"

trap "kill $BACKEND_PID $SIMULATOR_PID $FRONTEND_PID" EXIT
wait