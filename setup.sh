#!/bin/bash
echo "Setting up Edge Device Monitor..."

# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

# Frontend
cd frontend
npm install
cd ..

echo "Setup complete!"
echo "Run: ./run.sh"