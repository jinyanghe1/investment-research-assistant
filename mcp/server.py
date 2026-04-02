#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Server wrapper for investment-research tools.

This is a lightweight stdio MCP server that exposes the scripts in ../tools/
as callable MCP tools.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path


TOOLS = {
    "fetch_index_data": {
        "description": "抓取A股主要指数日线数据并保存为CSV",
        "inputSchema": {
            "type": "object",
            "properties": {
                "index": {"type": "string", "default": "hs300,cy,sz"},
                "output": {"type": "string", "default": "data"},
                "days": {"type": "integer", "default": 365}
            }
        }
    },
    "init_report": {
        "description": "初始化新研报项目，生成基于模板的HTML文件夹",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "author": {"type": "string", "default": "投研AI中枢"},
                "template": {"type": "string", "default": "templates/report-template.html"},
                "output_dir": {"type": "string", "default": "reports"}
            },
            "required": ["title"]
        }
    },
    "update_index_json": {
        "description": "将新研报元数据注册到 index.json",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "title": {"type": "string"},
                "author": {"type": "string", "default": "投研AI中枢"},
                "date": {"type": "string"},
                "category": {"type": "string", "enum": ["宏观", "微观"], "default": "微观"},
                "tags": {"type": "string"},
                "filepath": {"type": "string"},
                "index": {"type": "string", "default": "index.json"}
            },
            "required": ["id", "title", "tags", "filepath"]
        }
    }
}


def send_message(msg: dict):
    data = json.dumps(msg, ensure_ascii=False)
    sys.stdout.write(f"Content-Length: {len(data)}\r\n\r\n{data}")
    sys.stdout.flush()


async def handle_request(req: dict):
    method = req.get("method")
    req_id = req.get("id")

    if method == "initialize":
        send_message({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "serverInfo": {"name": "investment-research", "version": "0.1.0"}
            }
        })
    elif method == "tools/list":
        send_message({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": [{"name": k, **v} for k, v in TOOLS.items()]}
        })
    elif method == "tools/call":
        name = req["params"]["name"]
        args = req["params"]["arguments"]
        result = await run_tool(name, args)
        send_message({
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": result}]
            }
        })
    else:
        send_message({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        })


async def run_tool(name: str, args: dict) -> str:
    root = Path(__file__).parent.parent
    if name == "fetch_index_data":
        cmd = [
            sys.executable, str(root / "tools" / "fetch_index_data.py"),
            "--index", args.get("index", "hs300,cy,sz"),
            "--output", args.get("output", "data"),
            "--days", str(args.get("days", 365))
        ]
    elif name == "init_report":
        cmd = [
            sys.executable, str(root / "tools" / "init_report.py"),
            "--title", args["title"],
            "--author", args.get("author", "投研AI中枢"),
            "--template", args.get("template", "templates/report-template.html"),
            "--output-dir", args.get("output_dir", "reports")
        ]
    elif name == "update_index_json":
        cmd = [
            sys.executable, str(root / "tools" / "update_index_json.py"),
            "--id", args["id"],
            "--title", args["title"],
            "--author", args.get("author", "投研AI中枢"),
            "--category", args.get("category", "微观"),
            "--tags", args["tags"],
            "--filepath", args["filepath"],
            "--index", args.get("index", "index.json")
        ]
        if "date" in args:
            cmd.extend(["--date", args["date"]])
    else:
        return f"[ERROR] Unknown tool: {name}"

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(root)
    )
    stdout, stderr = await proc.communicate()
    output = stdout.decode("utf-8", errors="replace")
    if stderr:
        output += "\n[stderr] " + stderr.decode("utf-8", errors="replace")
    return output.strip()


async def main():
    while True:
        raw_length = sys.stdin.readline()
        if not raw_length:
            break
        if not raw_length.startswith("Content-Length: "):
            continue
        length = int(raw_length.split(": ")[1].strip())
        sys.stdin.readline()  # empty line
        body = sys.stdin.read(length)
        req = json.loads(body)
        await handle_request(req)


if __name__ == "__main__":
    asyncio.run(main())
