#!/bin/bash
echo "Starting Supergateway..."
exec npx --yes supergateway --cors true --stdio "uv run run_server.py"
