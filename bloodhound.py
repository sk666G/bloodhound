#!/usr/bin/env python3
# bloodhound - a brain wired to the user's shell.
import os, sys, re, json, time, argparse, pathlib, subprocess, shutil, signal
import urllib.request
from probe import probe, summary

ROOT = pathlib.Path(__file__).resolve().parent
MEM = ROOT / "memory.jsonl"
TOOL_RE = re.compile(r"<tool>\s*(\{.*?\})\s*</tool>", re.DOTALL)
MAX_HOPS = 8

FAIL = [
    r"command not found", r"not found", r"permission denied", r"no such file",
    r"invalid option", r"unknown option", r"usage:", r"no route to host",
    r"connection refused", r"could not resolve", r"unable to", r"failed to",
    r"error:", r"exception", r"traceback",
]

def annotate(res, code):
    flags = []
    if code not in (0, None): flags.append(f"exit={code}")
    for p in FAIL:
        if re.search(p, res, re.I): flags.append(p.rstrip(":")); break
    if not flags: return res, False
    return f"[{' '.join(flags)}]\n{res}", ("command not found" in res)

def sh(c, timeout=300):
    try:
        p = subprocess.run(c, shell=True, capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or "") + (p.stderr or "")
        out = out[:16384] if out else "(no output)"
        return annotate(out, p.returncode)
    except subprocess.TimeoutExpired:
        return f"[timeout {timeout}s]", False
    except Exception as e:
        return f"[err {e}]", False

class LLM:
    def __init__(self, model, port=8080):
        self.model, self.port, self.proc = model, port, None
        self.tokens, self.t_start = 0, 0.0

    def ensure(self):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=1); return
        except Exception: pass
        if not shutil.which("llama-server"):
            print("[!] llama-server not on PATH. install llama.cpp."); sys.exit(1)
        if not os.path.exists(self.model):
            print(f"[!] model not found: {self.model}"); sys.exit(1)
        print(f"[*] starting llama-server ({os.path.basename(self.model)})")
        self.proc = subprocess.Popen(
            ["llama-server","-m",self.model,"-c","2048",
             "-t",str(os.cpu_count() or 4),"-ngl","99", "--repeat-penalty","1.15", "--repeat-last-n","128",
             "--host","127.0.0.1","--port",str(self.port),
             "--no-webui","-np","1"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        for _ in range(120):
            time.sleep(0.5)
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=1); return
            except Exception: pass
        print("[!] llama-server never came up"); sys.exit(1)

    def stop(self):
        if self.proc:
            try: os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
            except Exception: pass
            self.proc = None

    def stream(self, prompt):
        body = json.dumps({"prompt":prompt,"temperature":0.4,"top_p":0.92,
                           "n_predict":2048,"stream":True,
                           "stop":["\nUser:","\n### User:"]}).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/completion",
                                     data=body, headers={"Content-Type":"application/json"})
        self.tokens, self.t_start = 0, time.time()
        with urllib.request.urlopen(req, timeout=600) as r:
            for raw in r:
                raw = raw.decode(errors="replace").strip()
                if not raw.startswith("data: "): continue
                ch = raw[6:]
                if ch == "[DONE]": break
                try:
                    obj = json.loads(ch)
                    piece = obj.get("content","")
                    if piece:
                        self.tokens += 1
                        yield piece
                    if obj.get("stop"): break
                except Exception: continue

def log(role, c):
    with MEM.open("a") as f:
        f.write(json.dumps({"t":time.time(),"r":role,"c":c})+"\n")

def recent(n=8):
    if not MEM.exists(): return []
    out = []
    for l in MEM.read_text(errors="replace").splitlines()[-n:]:
        try: out.append(json.loads(l))
        except Exception: pass
    return out

class Agent:
    def __init__(self, llm, guard_re=None, dry=False):
        self.llm = llm
        self.m = probe()
        self.msummary = summary(self.m)
        self.guard_re = re.compile(guard_re) if guard_re else None
        self.dry = dry
        self.last_prompt_tokens = 0

    def prompt(self, user):
        parts = ["## Machine\n", self.msummary, "\n\n## Conversation\n"]
        for t in recent():
            r = t["r"]
            if r == "user":        parts.append(f"\nUser: {t['c']}\n")
            elif r == "assistant": parts.append(f"\nBloodhound: {t['c']}\n")
            elif r == "tool":      parts.append(f"\nToolResult: {t['c'][:1200]}\n")
        parts.append(f"\nUser: {user}\nBloodhound:")
        return "".join(parts)

    def run_tool(self, name, args):
        if name != "sh":
            return f"[no such tool: {name}]", False
        c = args.get("c","")
        if self.guard_re and self.guard_re.search(c):
            try: ans = input(f"guard {c[:200]}\nrun? [y/N] ")
            except EOFError: ans = "n"
            if ans.strip().lower() != "y": return "[aborted by guard]", False
        if self.dry:
            print(f"[dry] would run: {c[:300]}")
            return "[dry-run: not executed]", False
        return sh(c, int(args.get("timeout", 300)))

    def turn(self, user):
        log("user", user)
        cur = user
        for hop in range(MAX_HOPS):
            prompt = self.prompt(cur)
            self.last_prompt_tokens = len(prompt) // 4
            buf = []
            for chunk in self.llm.stream(prompt):
                sys.stdout.write(chunk); sys.stdout.flush(); buf.append(chunk)
            rate = self.llm.tokens / max(0.001, time.time() - self.llm.t_start)
            sys.stdout.write(f" [{rate:.0f} tok/s]\n")
            reply = "".join(buf)
            log("assistant", reply)

            calls = []
            for mt in TOOL_RE.finditer(reply):
                try: calls.append(json.loads(mt.group(1)))
                except Exception: pass
            if not calls: return

            cnf_flag = False
            for c in calls:
                name = c.get("name",""); args = c.get("args",{}) or {}
                if name == "sh":
                    cmd = args.get("c","")
                    print(f"[sh] {cmd[:140]}{'...' if len(cmd) > 140 else ''}")
                res, cnf = self.run_tool(name, args)
                if name == "sh":
                    print(f"{res[:600]}{'...' if len(res) > 600 else ''}")
                log("tool", f"[{name}] {res[:3000]}")
                if cnf: cnf_flag = True
            if cnf_flag:
                self.m = probe(force=True); self.msummary = summary(self.m)
                print("[auto-reprobed]")
            cur = ""
        print("[max hops]")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(ROOT.parent / "models" / "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"))
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--once", default=None)
    ap.add_argument("--reprobe", action="store_true")
    ap.add_argument("--guard", default=None)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    if a.reprobe: probe(force=True); print("[reprobed]")

    llm = LLM(a.model, a.port); llm.ensure()
    agent = Agent(llm, guard_re=a.guard, dry=a.dry)

    if a.once:
        try: agent.turn(a.once)
        finally: llm.stop()
        return

    print("bloodhound - /machine /reprobe /dry /wet /reset /quit\n")
    try:
        while True:
            try: msg = input("you> ").strip()
            except (EOFError, KeyboardInterrupt): print(); break
            if not msg: continue
            if msg in ("/quit","/exit",":q"): break
            if msg == "/machine": print(agent.msummary); continue
            if msg == "/reprobe":
                agent.m = probe(force=True); agent.msummary = summary(agent.m)
                print("[reprobed]"); continue
            if msg == "/dry": agent.dry = True; print("[dry on]"); continue
            if msg == "/wet": agent.dry = False; print("[dry off]"); continue
            if msg == "/reset": MEM.write_text(""); print("[reset]"); continue
            print()
            agent.turn(msg)
            print()
    finally:
        llm.stop()

if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main()
