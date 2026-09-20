# probe.py - read the machine. Cached 1h to machine.json.
import os, sys, json, platform, shutil, socket, subprocess, pathlib, time, re

CACHE = pathlib.Path(__file__).resolve().parent / "machine.json"

def _run(c, t=4):
    try:
        p = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=t)
        return (p.stdout or p.stderr or "").strip()
    except Exception:
        return ""

def _has(b): return shutil.which(b) is not None

def os_info():
    o = {"system": platform.system(), "release": platform.release(),
         "machine": platform.machine()}
    if sys.platform == "linux":
        try:
            for l in open("/etc/os-release"):
                if l.startswith("PRETTY_NAME="):
                    o["distro"] = l.split("=",1)[1].strip().strip('"')
        except Exception: pass
        o["container"] = os.path.exists("/.dockerenv")
    elif sys.platform == "darwin":
        o["distro"] = "macOS " + _run("sw_vers -productVersion")
    elif sys.platform == "win32":
        o["distro"] = platform.system() + " " + platform.release()
    return o

def cpu_info():
    o = {"cores": os.cpu_count(), "arch": platform.machine()}
    if sys.platform == "linux":
        try:
            m = re.search(r"model name\s*:\s*(.+)", open("/proc/cpuinfo").read())
            if m: o["model"] = m.group(1).strip()
        except Exception: pass
    elif sys.platform == "win32":
        o["model"] = _run('wmic cpu get name /value').split("=")[-1].strip()
    return o

def mem_info():
    try:
        if sys.platform == "linux":
            m = re.search(r"MemTotal:\s+(\d+)", open("/proc/meminfo").read())
            return {"total_mb": int(m.group(1)) // 1024} if m else {}
        if sys.platform == "darwin":
            return {"total_mb": int(_run("sysctl -n hw.memsize") or 0) // (1 << 20)}
        if sys.platform == "win32":
            out = _run('wmic ComputerSystem get TotalPhysicalMemory /value')
            return {"total_mb": int(out.split("=")[-1].strip() or 0) // (1 << 20)}
    except Exception: pass
    return {}

def gpu_info():
    d = []
    if _has("nvidia-smi"):
        for line in _run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits").splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                d.append({"vendor": "nvidia", "name": parts[0],
                          "vram_mb": int(parts[1]) if parts[1].isdigit() else None})
    if sys.platform == "darwin":
        r = _run("system_profiler SPDisplaysDataType 2>/dev/null | grep -E 'Chipset|Metal' | head -4")
        if r: d.append({"vendor": "apple", "raw": r})
    return {"devices": d}

def net_info():
    o = {"hostname": socket.gethostname()}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); o["local_ip"] = s.getsockname()[0]; s.close()
    except Exception: pass
    o["public_ip"] = _run("curl -s --max-time 3 https://ifconfig.me 2>/dev/null") or None
    return o

def perm_info():
    o = {"user": os.environ.get("USER") or os.environ.get("USERNAME"),
         "is_root": False, "sudo_nopass": False}
    try:
        if hasattr(os, "geteuid"): o["is_root"] = os.geteuid() == 0
    except Exception: pass
    if _has("sudo"):
        r = _run("sudo -n true 2>&1", t=2)
        o["sudo_nopass"] = r == "" or "not allowed" not in r.lower()
    return o

KNOWN = [
    "nmap","masscan","rustscan","whois","dig","nslookup","amass","subfinder",
    "httpx","whatweb","sqlmap","nikto","gobuster","ffuf","feroxbuster","dirb",
    "nuclei","katana","gau","dalfox","curl","wget","httpie",
    "msfconsole","msfvenom","searchsploit","sliver","sliver-server","beef",
    "ghidra","radare2","r2","rizin","objdump","readelf","nm","strings","xxd",
    "upx","patchelf","ltrace","strace","gdb","lldb","frida","frida-trace",
    "afl-fuzz","honggfuzz","radamsa",
    "wireshark","tshark","tcpdump","ettercap","bettercap","mitmproxy","responder",
    "impacket-","netexec","nxc","crackmapexec","evil-winrm","psexec","smbclient",
    "rpcclient","enum4linux","nbtscan","arp-scan","hping3","scapy","socat","nc",
    "ncat","openssl","ssh","ssh-keygen","scp","rsync",
    "hashcat","john","hydra","medusa","patator","crunch","cewl",
    "aircrack-ng","airodump-ng","aireplay-ng","kismet","reaver","wifite",
    "mimikatz","rubeus","sharphound","bloodhound","winpeas","linpeas","pspy",
    "lazagne","chisel","ligolo","proxychains","proxychains4","tun2socks",
    "tor","torsocks","openvpn","wg","wireguard","sshuttle",
    "python3","python","node","npm","go","rustc","cargo","gcc","g++","clang",
    "javac","java","dotnet","mono","ruby","perl","php","lua","make","cmake","git",
    "pip","pip3","pipx","apt","apt-get","dnf","yum","pacman","brew","choco",
    "winget","snap","flatpak","nix",
    "aws","gcloud","az","kubectl","helm","terraform","ansible","docker","podman",
    "jq","yq","rg","fd","fzf","tmux","screen","sed","awk","grep","find",
    "base64","md5sum","sha256sum","gpg","age","zstd","gzip","tar","zip","unzip",
]

def tools_info():
    return {b: shutil.which(b) for b in KNOWN if not b.endswith("-") and _has(b)}

def probe(force=False):
    if CACHE.exists() and not force and time.time() - CACHE.stat().st_mtime < 3600:
        try: return json.loads(CACHE.read_text())
        except Exception: pass
    m = {"ts": time.time(), "os": os_info(), "cpu": cpu_info(), "mem": mem_info(),
         "gpu": gpu_info(), "net": net_info(), "perm": perm_info(), "tools": tools_info()}
    CACHE.write_text(json.dumps(m, indent=2))
    return m

def summary(m):
    o, c, p, n = m["os"], m["cpu"], m["perm"], m["net"]
    L = [f"OS: {o.get('distro') or o.get('system')} {o.get('release','')} ({o.get('machine','?')})"]
    if o.get("container"): L.append("  container: yes")
    L.append(f"CPU: {c.get('model','?')} x {c.get('cores','?')}")
    if m["mem"].get("total_mb"): L.append(f"RAM: {m['mem']['total_mb']} MB")
    for g in m["gpu"]["devices"]:
        L.append(f"GPU: {g.get('vendor')} {g.get('name','')} {g.get('vram_mb','')} MB")
    L.append(f"user: {p.get('user')} root={p.get('is_root')} sudo_nopass={p.get('sudo_nopass')}")
    if n.get("public_ip"): L.append(f"public ip: {n['public_ip']}")
    L.append("")
    L.append("AVAILABLE ON THIS BOX:")
    tools = sorted(m["tools"].keys())
    if not tools:
        L.append("  (nothing - bare box)")
        return "\n".join(L)
    line, ln = [], 0
    for t in tools:
        if ln + len(t) + 2 > 100:
            L.append("  " + " ".join(line)); line, ln = [], 0
        line.append(t); ln += len(t) + 1
    if line: L.append("  " + " ".join(line))
    return "\n".join(L)

if __name__ == "__main__":
    print(summary(probe(force="--force" in sys.argv)))
