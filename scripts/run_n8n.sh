#!/usr/bin/env bash
# Start n8n with Execute Command nodes enabled (required for pentest pipeline in n8n v2).
set -euo pipefail
export NODES_EXCLUDE='[]'
export NODE_FUNCTION_ALLOW_BUILTIN='fs,path,os,crypto,util'
echo "Starting n8n (Execute Command on; Code nodes may use fs via NODE_FUNCTION_ALLOW_BUILTIN)"
echo "Editor: http://localhost:5678"
exec n8n start
