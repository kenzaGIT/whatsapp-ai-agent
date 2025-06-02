#!/bin/bash
# Kill process using port 8000

echo "Finding process using port 8000..."
pid=$(lsof -ti:8000)

if [ -z "$pid" ]; then
  echo "No process found using port 8000."
else
  echo "Process found with PID: $pid"
  echo "Killing process..."
  kill -9 $pid
  echo "Process killed!"
fi

echo "Port 8000 should now be free."