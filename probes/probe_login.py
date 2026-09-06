#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=2", "websockets>=12.0"]
# ///
"""Prove the login tool end to end: wrong password, then the real one."""
import asyncio, importlib.util, json, sys, time
from pathlib import Path
spec = importlib.util.spec_from_file_location("prm", Path(__file__).parent.parent / "pixel_room_mcp.py")
prm = importlib.util.module_from_spec(spec); spec.loader.exec_module(prm)

async def main():
    print("1. open ->", json.dumps(prm.open_editor())[:90])
    time.sleep(4)
    print("2. ready before ->", json.dumps(json.loads(await prm.ready()))[:110])
    print("3. login WRONG ->", (await prm.login("nasilemak"))[:150].replace("\n"," "))
    print("4. login RIGHT ->", (await prm.login(sys.argv[1]))[:120].replace("\n"," "))
    print("5. login again ->", (await prm.login(sys.argv[1]))[:110].replace("\n"," "))
    await prm.browser.evaluate("location.href='" + prm.EDITOR_URL + "room/'")
    time.sleep(3)
    print("6. describe ->", (await prm.describe())[:100].replace("\n"," "))
    print("7. place ->", (await prm.place("plant_palm", 11, 12))[:110].replace("\n"," "))
    prm.browser.close()
    print("8. closed ->", prm.browser.proc is None)

asyncio.run(main())
