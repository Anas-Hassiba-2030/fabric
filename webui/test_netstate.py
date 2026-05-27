#!/usr/bin/env python3
"""Proof that the read-only state loader normalizes formats + stays read-only — no live source.

Run:  python webui/test_netstate.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import netstate  # noqa: E402

fails = 0


def check(desc, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + desc)
    if not cond:
        fails += 1


print("=== 1. Native WRATH snapshot passes through ===")
nat = {"devices": {"PE1": {"role": "pe", "interfaces": [{"name": "Gi0", "oper": "up", "mtu": 9216, "desc": "to:P1"}],
                           "bgp_neighbors": [{"neighbor": "10.0.0.1", "afi": "vpnv4", "state": "Established", "prefixes": 5}]}}}
n = netstate.normalize(nat)
check("device kept", "PE1" in n["devices"])
check("interface normalized", n["devices"]["PE1"]["interfaces"][0]["oper"] == "up")
check("bgp normalized", n["devices"]["PE1"]["bgp_neighbors"][0]["state"] == "Established")

print("=== 2. Foreign (NetBox/gNMI-ish) shape is adapted to WRATH schema ===")
foreign = {"devices": [
    {"hostname": "R1",
     "interfaces": [{"interface": "Eth1", "oper-status": "LOWER_LAYER_DOWN", "description": "to:CE", "ipv4": "192.0.2.1/30"}],
     "bgp": [{"peer": "192.0.2.2", "session-state": "established", "address-family": "ipv4", "prefixes-received": 12}]}]}
f = netstate.normalize(foreign)
check("list-of-devices -> keyed by hostname", "R1" in f["devices"])
check("oper-status LOWER_LAYER_DOWN -> down", f["devices"]["R1"]["interfaces"][0]["oper"] == "down")
check("description -> desc", f["devices"]["R1"]["interfaces"][0]["desc"] == "to:CE")
check("peer -> neighbor", f["devices"]["R1"]["bgp_neighbors"][0]["neighbor"] == "192.0.2.2")
check("session-state established -> Established", f["devices"]["R1"]["bgp_neighbors"][0]["state"] == "Established")
check("prefixes-received -> prefixes", f["devices"]["R1"]["bgp_neighbors"][0]["prefixes"] == 12)

print("=== 3. Loads the committed snapshot directory ===")
st = netstate.load(netstate.DEFAULT_DIR)
check("default dir loads devices", st and len(st["devices"]) >= 1)
check("known device present (PE1)", st and "PE1" in st["devices"])

print("=== 4. URL source is a read-only GET, normalized (mocked — no network) ===")
captured = {}


class FakeResp:
    def __init__(self, data): self._d = json.dumps(data).encode()
    def read(self, *a): return self._d
    def __enter__(self): return self
    def __exit__(self, *a): return False


def fake_urlopen(req, timeout=10):
    captured["method"] = req.get_method()
    return FakeResp({"devices": [{"name": "RTR9", "bgp": [{"peer": "1.1.1.1", "session-state": "idle"}]}]})


netstate.urllib.request.urlopen = fake_urlopen
os.environ["WRATH_NETSTATE_URL"] = "http://netbox.example/api/state"
st2 = netstate.load()
check("URL source fetched + normalized", st2 and "RTR9" in st2["devices"])
check("request method is GET (read-only)", captured.get("method") == "GET")
check("idle session normalized (not Established)", st2["devices"]["RTR9"]["bgp_neighbors"][0]["state"] != "Established")
del os.environ["WRATH_NETSTATE_URL"]

print("=== 5. Graceful failure (no crash) on a bad dir ===")
check("missing dir -> None, no exception", netstate.load("/no/such/dir/xyz") is None)

print()
print("RESULT:", "ALL GREEN — read-only state loader normalizes + stays read-only." if not fails else f"{fails} FAILURE(S).")
sys.exit(1 if fails else 0)
