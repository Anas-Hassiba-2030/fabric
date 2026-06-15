#!/usr/bin/env python3
"""Minimal, dependency-free MCP stdio server framework for WRATH.

Implements just enough of the Model Context Protocol stdio transport to expose read-only tools to
Claude Code without pulling in the `mcp` SDK (keeps the WRATH tree runnable with stock python3, the
same posture as the hooks). Transport: newline-delimited JSON-RPC 2.0 on stdin/stdout. All logging
goes to stderr — stdout carries protocol messages only.

Supported methods: initialize, notifications/initialized, ping, tools/list, tools/call.

Register tools with .tool(name, description, input_schema)(handler). A handler takes the arguments
dict and returns a string (rendered as a single text content block) or raises to signal a tool error.
"""
import json
import sys
import traceback

PROTOCOL_VERSION = "2024-11-05"


def log(*a):
    print(*a, file=sys.stderr, flush=True)


class MCPServer:
    def __init__(self, name, version="0.1.0"):
        self.name = name
        self.version = version
        self._tools = {}  # name -> (description, input_schema, handler)

    def tool(self, name, description, input_schema):
        def register(handler):
            self._tools[name] = (description, input_schema, handler)
            return handler
        return register

    # --- protocol handlers ---------------------------------------------------------------
    def _handle(self, req):
        method = req.get("method")
        params = req.get("params") or {}
        if method == "initialize":
            client_proto = params.get("protocolVersion") or PROTOCOL_VERSION
            return {
                "protocolVersion": client_proto,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": self.name, "version": self.version},
            }
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": [
                {"name": n, "description": d, "inputSchema": s}
                for n, (d, s, _) in self._tools.items()
            ]}
        if method == "tools/call":
            tname = params.get("name")
            args = params.get("arguments") or {}
            entry = self._tools.get(tname)
            if not entry:
                return {"content": [{"type": "text", "text": f"unknown tool: {tname}"}], "isError": True}
            _, _, handler = entry
            try:
                text = handler(args)
            except Exception as e:  # tool-level error -> isError result, not a transport error
                return {"content": [{"type": "text", "text": f"tool error: {e}"}], "isError": True}
            return {"content": [{"type": "text", "text": text if isinstance(text, str) else json.dumps(text)}]}
        raise _MethodNotFound(method)

    def run(self):
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except Exception:
                continue  # not parseable JSON-RPC; ignore
            rid = req.get("id")
            method = req.get("method", "")
            # notifications have no id and expect no response
            if rid is None and method.startswith("notifications/"):
                continue
            try:
                result = self._handle(req)
                resp = {"jsonrpc": "2.0", "id": rid, "result": result}
            except _MethodNotFound as e:
                resp = {"jsonrpc": "2.0", "id": rid,
                        "error": {"code": -32601, "message": f"method not found: {e}"}}
            except Exception as e:
                log("internal error:", traceback.format_exc())
                resp = {"jsonrpc": "2.0", "id": rid,
                        "error": {"code": -32603, "message": f"internal error: {e}"}}
            if rid is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()


class _MethodNotFound(Exception):
    pass
