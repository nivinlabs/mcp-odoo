#!/bin/bash
echo "Starting Supergateway..."
exec npx --yes supergateway --stdio "uv run run_server.py"
