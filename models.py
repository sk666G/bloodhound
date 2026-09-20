# models.py - model zoo: list, download, pick.
import json, os, sys, shutil, subprocess, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
MODELS = ROOT / "models"
CATALOG = ROOT / "models.json"
MODELS.mkdir(exist_ok=True)

def load():
    if not CATALOG.exists(): return []
    try: return json.loads(CATALOG.read_text())["models"]
    except Exception: return []

def listing():
    rows = load()
    if not rows: return "(no catalog)"
    out = []
    out.append(f"{'name':<28} {'size':>7} {'ram':>5} {'quality':<10} note")
    out.append("-" * 100)
    for m in rows:
        present = " *" if (MODELS / m["file"]).exists() else ""
        out.append(f"{m['name']:<28} {m['size_gb']:>6.1f}G {m['min_ram_gb']:>4}G "
                   f"{m['quality']:<10} {m['note']}{present}")
    out.append("")
    out.append("  * = already downloaded")
    return "\n".join(out)

def find(name):
    for m in load():
        if m["name"] == name: return m
    return None

def download(name):
    m = find(name)
    if not m: return f"[models] unknown: {name}"
    dst = MODELS / m["file"]
    if dst.exists():
        return f"[models] {name} already present ({dst.stat().st_size // (1<<20)}MB)"
    url = m["url"]
    print(f"[models] downloading {name} ({m['size_gb']}G) -> {dst}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=300) as r, dst.open("wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            got = 0
            while True:
                chunk = r.read(1 << 20)
                if not chunk: break
                f.write(chunk); got += len(chunk)
                if total:
                    pct = got * 100 // total
                    sys.stdout.write(f"\r[models] {name} {pct}% "
                                     f"({got//(1<<20)}M/{total//(1<<20)}M)")
                    sys.stdout.flush()
        print()
        return f"[models] {name} ready ({dst.stat().st_size // (1<<20)}MB)"
    except Exception as e:
        try: dst.unlink()
        except Exception: pass
        return f"[models] download failed: {e}"

def path_for(name):
    m = find(name)
    if not m: return None
    return str(MODELS / m["file"])

def recommend():
    """Pick the best model for this box."""
    ram = 0
    vram = 0
    try:
        if sys.platform == "win32":
            import subprocess as sp
            out = sp.run('wmic ComputerSystem get TotalPhysicalMemory /value',
                         shell=True, capture_output=True, text=True).stdout
            ram = int(out.split("=")[-1].strip() or 0) // (1 << 30)
            out = sp.run('wmic path win32_VideoController get AdapterRAM /value',
                         shell=True, capture_output=True, text=True).stdout
            vram_list = [int(x.split("=")[-1].strip() or 0)
                         for x in out.splitlines() if "AdapterRAM=" in x]
            vram = max(vram_list or [0]) // (1 << 30)
        else:
            with open("/proc/meminfo") as f:
                for l in f:
                    if "MemTotal" in l:
                        ram = int(l.split()[1]) // (1 << 20); break
    except Exception:
        pass
    # score by biggest that fits with headroom
    fit = [m for m in load()
           if m["min_ram_gb"] <= max(2, ram - 2)
           and m["vram_gb"] <= max(0, vram)]
    if not fit:
        fit = [load()[0]] if load() else []
    best = max(fit, key=lambda x: x["size_gb"]) if fit else None
    if not best: return "(no models available)"
    return (f"recommended: {best['name']}\n"
            f"  size: {best['size_gb']}G, needs {best['min_ram_gb']}G RAM, "
            f"{best['vram_gb']}G VRAM\n"
            f"  quality: {best['quality']}  speed on CPU: {best['speed_cpu']}\n"
            f"  detected: {ram}G RAM, {vram}G VRAM\n"
            f"  download: python models.py get {best['name']}")

if __name__ == "__main__":
    if len(sys.argv) == 1: print(listing()); sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "list": print(listing())
    elif cmd == "rec": print(recommend())
    elif cmd == "get" and len(sys.argv) > 2: print(download(sys.argv[2]))
    elif cmd == "path" and len(sys.argv) > 2:
        p = path_for(sys.argv[2]); print(p or "(unknown)")
    else:
        print("usage: python models.py [list|rec|get <name>|path <name>]")
