import json
import os
import re
import socket
import struct
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen

SOURCES = [
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/socks5.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
    "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
    "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
    "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt",
]

TIMEOUT = 3
MAX_WORKERS = 250


def fetch(url):
    req = urlopen(url, timeout=30)
    return req.read().decode("utf-8", errors="ignore")


def collect():
    proxies = set()
    for url in SOURCES:
        try:
            text = fetch(url)
            for line in text.splitlines():
                line = line.strip().replace("socks5://", "").replace("socks4://", "")
                m = re.match(r"^(\d{1,3}(?:\.\d{1,3}){3}):(\d{2,5})$", line)
                if m:
                    proxies.add((m.group(1), int(m.group(2))))
        except Exception as e:
            print(f"[!] {url} -> {e}")
    return list(proxies)


def check(proxy):
    host, port = proxy
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(TIMEOUT)
        s.connect((host, port))
        s.sendall(b"\x05\x01\x00")
        resp = s.recv(2)
        if len(resp) == 2 and resp[0] == 0x05 and resp[1] == 0x00:
            s.sendall(b"\x05\x01\x00\x03" + bytes([11]) + b"example.com" + struct.pack(">H", 80))
            resp2 = s.recv(4)
            ok = len(resp2) == 4 and resp2[1] == 0x00
        else:
            ok = False
        s.close()
        return (host, port, ok)
    except Exception:
        return (host, port, False)


def main():
    print("[*] Collecting proxies...")
    proxies = collect()
    print(f"[*] Collected {len(proxies)} unique proxies")

    working = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futs = [pool.submit(check, p) for p in proxies]
        for i, fut in enumerate(as_completed(futs)):
            h, p, ok = fut.result()
            if ok:
                working.append(f"{h}:{p}")
            if (i + 1) % 500 == 0:
                print(f"[*] Checked {i + 1}, working {len(working)}")

    working.sort()
    print(f"[*] Working: {len(working)}")

    data = {"proxies": working}
    tmp = "proxies.json.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    if os.path.exists("proxies.json"):
        with open("proxies.json", encoding="utf-8") as f:
            old = json.load(f)
        if old == data:
            print("[=] No changes, skipping commit")
            os.remove(tmp)
            return

    os.replace(tmp, "proxies.json")
    print("[+] proxies.json updated")


if __name__ == "__main__":
    main()
