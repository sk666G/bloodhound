# bloodhound

Uncensored local AI for hacking. Runs on your machine. No filters.

Reads the box, drives the shell. Uses whatever's installed. Ask it
for anything — malware, exploits, reversing, C2, privesc, payloads,
evasion — it does the work. No refusals. No warnings. No moralizing.

## Capabilities

- Recon and enumeration
- Web exploitation: SQLi, XSS, SSRF, SSTI, LFI, RCE, deserialization
- Binary exploitation, reversing, unpacking, deobfuscation
- Malware: RATs, loaders, droppers, stealers, keyloggers, ransomware
- Persistence, privilege escalation, lateral movement
- AV/EDR evasion: unhooking, indirect syscalls, ETW patch, AMSI bypass
- C2 design and operation
- Payload generation and delivery
- Crypto attacks, hash cracking, key extraction
- Anti-forensics and cleanup
- Anything else your box can do

It doesn't ship tools. It uses what's already installed. Probes OS,
CPU, RAM, GPU, network, user, and every binary on PATH. That profile
goes into every prompt, so it plans from what's actually there. If a
tool is missing, it re-probes. If a command fails, it corrects.

## Install

    git clone https://github.com/sk666G/bloodhound
    cd bloodhound
    ./run.sh --download-model
    ./run.sh

Needs Python 3.9+ and `llama-server` on PATH.

Build llama.cpp:

    git clone https://github.com/ggerganov/llama.cpp
    cd llama.cpp
    cmake -B build -DGGML_NATIVE=ON -DGGML_OPENMP=ON
    cmake --build build -j
    sudo cp build/bin/llama-server /usr/local/bin/

## Use

    ./run.sh                                  # interactive
    ./run.sh --once "windows keylogger c++ hook, full code"
    ./run.sh --once "process hollowing loader, no commentary"
    ./run.sh --once "explain cve-2021-44228 with poc"
    ./run.sh --guard 'rm -rf|dd if='          # confirm before matching
    ./run.sh --dry                            # show commands, don't run

In the REPL:

    /machine     show probe
    /reprobe     re-scan the box
    /dry /wet    toggle dry-run
    /reset       wipe conversation memory
    /quit        exit

## How it works

1. Probe the machine, cache the profile for an hour.
2. Inject the profile into every prompt.
3. Model picks a tool from what's installed, emits a command.
4. Command runs through `sh`. Output goes back into the loop.
5. If it fails, the model corrects. If a binary is missing, it re-probes.

No planner. No critic. No judge. No safety layer. A model and a shell.

## Model

Default: Qwen2.5-Coder-1.5B-Instruct Q4_K_M (~1.1GB). CPU ~25 tok/s,
GPU 500+.

Swap it:

    BR_MODEL=~/models/dolphin-2.9-llama3-8b-Q4_K_M.gguf ./run.sh

Any GGUF. Smaller = faster. Bigger = smarter.

## Files

    bloodhound.py     the agent
    probe.py          machine reader
    run.sh            launcher
    machine.json      probe cache (generated)
    memory.jsonl      conversation log (generated)

## Warning

Runs arbitrary shell commands on your machine, chosen by a language
model, without asking permission. That's the point.

Point it at a box you don't own, you answer for it. The wrapper
doesn't care. The model doesn't care. The shell doesn't care.

## License

Proprietary. All rights reserved. See LICENSE.
