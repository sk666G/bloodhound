#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
MODEL="${BR_MODEL:-$(cd .. && pwd)/models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf}"

if [[ "$1" == "--download-model" ]]; then
  mkdir -p "$(dirname "$MODEL")"
  [[ -f "$MODEL" ]] || curl -L -o "$MODEL" \
    "https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
  echo "[+] $MODEL"; exit 0
fi

exec python3 bloodhound.py --model "$MODEL" "$@"
