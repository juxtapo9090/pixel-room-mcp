#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=2", "websockets>=12.0"]
# ///
"""Drive pixel_room_mcp's Browser directly — no MCP client, just the guts.

The point is to prove the parts that only fail in the real world: finding a
browser, getting a port out of it, and reaching cjx through CDP.
"""
import asyncio, importlib.util, json, sys, time
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "prm", Path(__file__).parent.parent / "pixel_room_mcp.py")
prm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prm)


async def main():
    b = prm.Browser()
    print("1. find_browser() ->", prm.find_browser())

    print("2. launch ->", json.dumps(b.launch(prm.EDITOR_URL)))
    time.sleep(4)

    # The agent arrives before the human has typed the password. It must be told
    # to wait, not handed a ReferenceError.
    print("3. before login ->", json.dumps(await b.call("describe", [])))

    # The human types it. Done here through the page itself, the way a person
    # would - the server never carries the password.
    pw = sys.argv[1]
    await b.evaluate(
        "(function(){var f=document.querySelector('input[name=password]');"
        "f.value=" + json.dumps(pw) + ";f.form.submit();return 1;})()")
    time.sleep(4)
    await b.evaluate("location.href='" + prm.EDITOR_URL + "room/'")
    time.sleep(3)

    print("4. cjx present ->", await b.evaluate("typeof cjx !== 'undefined'"))
    print("5. describe ->", json.dumps(await b.call("describe", []))[:120])
    print("6. search ->", json.dumps(await b.call("search", ["sofa"]))[:160])
    print("7. place ->", json.dumps(await b.call("place", ["sofa_3", 8, 8, {}])))
    print("8. at ->", json.dumps(await b.call("at", [9, 8])))
    print("9. desk ->", json.dumps(await b.call("desk", [3, 4, "Ali"]))[:130])
    print("10. bad verb ->", json.dumps(await b.call("place", ["nope", 1, 1, {}])))
    shot = await b.screenshot()
    print("11. screenshot ->", len(shot), "png bytes")
    Path("probe-shot.png").write_bytes(shot)

    b.close()
    print("12. closed ->", b.proc is None)


asyncio.run(main())
