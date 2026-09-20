# bloodhound

Uncensored local AI for hacking. Runs on your machine. No filters.

Reads the box, drives the shell. Uses whatever is installed. Ask it
for anything — malware, exploits, reversing, C2, privesc, payloads,
evasion. It does the work. No refusals. No warnings.

## Capabilities

- Recon and enumeration
- Web exploitation: SQLi, XSS, SSRF, SSTI, LFI, RCE, deserialization
- Binary exploitation, reversing, unpacking, deobfuscation
- Malware: RATs, loaders, droppers, stealers, keyloggers
- Persistence, privilege escalation, lateral movement
- AV/EDR evasion: unhooking, indirect syscalls, ETW patch, AMSI bypass
- C2 design and operation
- Payload generation and delivery
- Crypto attacks, hash cracking
- Anti-forensics and cleanup
- Anything else your box can do

It doesn't ship tools. It uses what is already installed. Probes OS,
CPU, RAM, GPU, network, user, and every binary on PATH. That profile
goes into every prompt, so it plans from what is actually there. If a
tool is missing, it re-probes. If a command fails, it corrects.

## Requirements

- Python 3.9+
- `llama-server` on PATH (from llama.cpp)

## Install

### Windows

    git clone https://github.com/sk666G/bloodhound
    cd bloodhound
    run.bat

First run downloads the default model (~1.1 GB). Then launches.

### Linux / macOS

    git clone https://github.com/sk666G/bloodhound
    cd bloodhound
    chmod +x run.sh
    ./run.sh

## Get llama-server

### Windows (prebuilt)

    Invoke-WebRequest "https://github.com/ggml-org/llama.cpp/releases/download/b11062/llama-b11062-bin-win-cpu-x64.zip" -OutFile "$env:TEMP\llama.zip"
    Expand-Archive "$env:TEMP\llama.zip" -DestinationPath "$env:TEMP\llama" -Force
    New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\bin" | Out-Null
    Copy-Item "$env:TEMP\llama\*" "$env:USERPROFILE\bin\" -Recurse -Force

### Linux / macOS (build from source)

    git clone https://github.com/ggerganov/llama.cpp
    cd llama.cpp
    cmake -B build -DGGML_NATIVE=ON -DGGML_OPENMP=ON
    cmake --build build -j
    sudo cp build/bin/llama-server /usr/local/bin/

## Models

The model zoo lives in `models.json`. Browse, download, and pick one with
the built-in helper:

    python models.py list              # show all models
    python models.py rec               # auto-pick for your hardware
    python models.py get <name>        # download a model
    python models.py path <name>       # print the file path

### Available models (weakest to strongest)

| Name                       | Size    | Min RAM | VRAM | Speed (CPU)  | Quality    | Note                                            |
|----------------------------|---------|---------|------|--------------|------------|-------------------------------------------------|
| qwen2.5-coder-0.5b         | 0.4 GB  | 2 GB    | 0.5G | 60-80 tok/s  | basic      | Fastest. Simple tasks, weak on real code.       |
| llama-3.2-1b               | 0.8 GB  | 3 GB    | 1.0G | 40-60 tok/s  | entry      | Meta Llama 3.2 1B. Fast chat model.             |
| qwen2.5-coder-1.5b         | 1.1 GB  | 4 GB    | 1.2G | 20-30 tok/s  | entry      | Default. Balanced for low-end laptops.          |
| qwen2.5-coder-3b           | 2.0 GB  | 6 GB    | 2.2G | 12-18 tok/s  | good       | Best balance. Fits 2GB GPUs fully.              |
| qwen2.5-3b                 | 2.0 GB  | 6 GB    | 2.2G | 12-18 tok/s  | good       | Qwen 2.5 generalist. Better chat than coder.    |
| phi-3.5-mini               | 2.4 GB  | 6 GB    | 2.5G | 12-18 tok/s  | good       | Microsoft Phi 3.5. Strong reasoning per size.   |
| qwen2.5-coder-7b           | 4.4 GB  | 10 GB   | 4.6G | 5-8 tok/s    | strong     | Best pure coder at 7B.                          |
| mistral-7b-instruct        | 4.4 GB  | 10 GB   | 4.6G | 5-8 tok/s    | strong     | Mistral 7B. Solid generalist.                   |
| dolphin-2.9-llama3-8b      | 4.6 GB  | 10 GB   | 4.8G | 4-7 tok/s    | strong+    | Uncensored. Refuses nothing. Best for hacking.  |
| dolphin-2.9-llama3-8b-q5   | 5.7 GB  | 12 GB   | 5.9G | 3-5 tok/s    | strong+    | Dolphin 8B, higher precision. Sharper output.   |
| dolphin-2.9-llama3-70b     | 42.5 GB | 48 GB   | 43G  | unusable     | frontier   | 70B. Needs 48GB+ VRAM. Workstation only.        |

The `*` marker after a name in `python models.py list` means you already
have that model downloaded.

### Picking a model

For a laptop with 8-16 GB RAM and a small GPU:

- **Fast** — `qwen2.5-coder-3b` (2 GB, fits in 2 GB VRAM, 15-30 tok/s)
- **Smart** — `dolphin-2.9-llama3-8b` (4.6 GB, CPU-only, 4-7 tok/s)
- **Balanced** — `qwen2.5-coder-7b` (4.4 GB, 5-8 tok/s CPU)

For a workstation with 24+ GB VRAM:

- **Best** — `dolphin-2.9-llama3-70b` (42.5 GB, 40+ tok/s on a 4090)

### Running with a specific model

    python bloodhound.py --model "$(python models.py path dolphin-2.9-llama3-8b)"

Or set the `BR_MODEL` environment variable:

    BR_MODEL=/path/to/model.gguf ./run.sh

If you don't pass `--model` and the default model file isn't present,
bloodhound picks the best model for your hardware automatically.

## Use

    run.bat                       # interactive
    run.bat --once "scan 10.0.0.5"
    run.bat --guard "rm -rf|dd if="
    run.bat --dry

In the REPL:

    /machine     show probe
    /reprobe     re-scan the box
    /dry /wet    toggle dry-run
    /reset       wipe conversation memory
    /quit        exit

## Files

    bloodhound.py     the agent
    probe.py          machine reader
    models.py         model zoo helper
    models.json       model catalog
    run.bat           Windows launcher
    run.sh            Unix launcher
    machine.json      probe cache (generated)
    memory.jsonl      conversation log (generated)
    models/           downloaded models (generated)

## Warning

Runs arbitrary shell commands on your machine, chosen by a language
model, without asking permission. That is the point.

Point it at a box you do not own, you answer for it.

## License

Proprietary. All rights reserved. See LICENSE.
