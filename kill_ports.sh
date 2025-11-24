#!/bin/bash

echo "🔍 Finding processes using ports..."

# Find all processes listening on ports
PIDS=$(lsof -ti:5001,5432,8000,8080,3000,4000,9000 | sort | uniq)

if [ -z "$PIDS" ]; then
    echo "✅ No processes found using common ports"
    exit 0
fi

echo "📋 Found processes: $PIDS"
echo "🛑 Killing processes..."

# Kill each process
for PID in $PIDS; do
    if kill -9 $PID 2>/dev/null; then
        echo "✅ Killed process $PID"
    else
        echo "❌ Could not kill process $PID"
    fi
done

echo "🧹 Cleaning up..."
sleep 2

echo "✅ Port cleanup complete!"
