#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=2", "websockets>=12.0"]
# ///
"""
pixel-room — decorate a room together with your agent.

It opens a browser on the editor, waits for *you* to type the password, and then
forwards your agent's requests to `window.cjx` inside the page. Everything that
crosses that boundary is a tile coordinate or a piece name, never a pixel — so
your agent is a collaborator with verbs, not a mouse on a leash.

Run it with `uv run pixel_room_mcp.py`. The dependencies install themselves;
there is no virtualenv to make and nothing to pip install.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

import websockets
from mcp.server.mcpserver import MCPServer

EDITOR_URL = os.environ.get("PIXEL_ROOM_URL", "https://celestjux-editors.vercel.app/")

# A profile of our own, never the one you browse with. A debug port on your
# everyday profile hands any process on this machine every tab you are signed
# into — mail, bank, chat. This one starts empty and knows nothing.
PROFILE_DIR = Path(os.environ.get(
    "PIXEL_ROOM_PROFILE", Path(tempfile.gettempdir()) / "pixel-room-profile"))

BROWSERS = [
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
    "brave-browser", "brave", "microsoft-edge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]

# Where cjx actually lives.
#
# The landing page is a shell with the two editors in iframes, so `cjx` is NOT on
# the top window — evaluating `typeof cjx` there says undefined forever, and the
# agent waits for a login that already happened. The frame is same-origin, so the
# parent can reach straight into it. Opening /room/ directly is also supported,
# and then cjx is on the window as usual; this handles both.
CJX_HANDLE = (
    "(function(){"
    "  if (typeof cjx !== 'undefined') return cjx;"
    "  try {"
    "    var f = document.getElementById('frame-room');"
    "    return (f && f.contentWindow && f.contentWindow.cjx) || null;"
    "  } catch (e) { return null; }"
    "})()"
)


def find_browser() -> str | None:
    override = os.environ.get("PIXEL_ROOM_BROWSER")
    if override:
        return override if (shutil.which(override) or Path(override).exists()) else None
    for name in BROWSERS:
        found = shutil.which(name) or (name if Path(name).exists() else None)
        if found:
            return found
    return None


class Browser:
    """One browser, one page, one CDP conversation."""

    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None
        self.port: int | None = None
        self._msg_id = 0

    def launch(self, url: str) -> dict[str, Any]:
        if self.proc and self.proc.poll() is None:
            return {"already_open": True, "port": self.port}

        binary = find_browser()
        if not binary:
            raise RuntimeError(
                "No Chrome, Chromium, Brave or Edge found on this machine. Install "
                "one, or set PIXEL_ROOM_BROWSER to the full path of the binary.")

        PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        port_file = PROFILE_DIR / "DevToolsActivePort"
        port_file.unlink(missing_ok=True)

        # Port 0 means "pick a free one". A fixed port collides with whatever is
        # already debugging on this machine, and that failure reads like a bug
        # in here rather than a busy port.
        # Chrome's stderr is kept, not sent to /dev/null. When it refuses to
        # start it says exactly why on there, and swallowing that leaves you
        # holding "it exited" with nowhere to go.
        self._log = tempfile.NamedTemporaryFile(
            prefix="pixel-room-browser-", suffix=".log", delete=False)
        self.proc = subprocess.Popen(
            [binary, "--remote-debugging-port=0", f"--user-data-dir={PROFILE_DIR}",
             "--no-first-run", "--no-default-browser-check", url],
            stdout=subprocess.DEVNULL, stderr=self._log)

        for _ in range(100):  # 10 seconds
            if port_file.exists():
                first = port_file.read_text().splitlines()[0].strip()
                if first.isdigit():
                    self.port = int(first)
                    return {"browser": Path(binary).name, "port": self.port, "url": url}
            if self.proc.poll() is not None:
                raise RuntimeError(
                    f"{Path(binary).name} exited before opening a port. "
                    f"It said: {self._why()}")
            time.sleep(0.1)
        raise RuntimeError(
            f"{Path(binary).name} started but never wrote a debugging port. If it was "
            "already running on this profile, close that window and try again.")

    def _why(self) -> str:
        """Whatever the browser printed on its way out, plus the two causes that
        account for nearly all of it."""
        try:
            self._log.flush()
            said = Path(self._log.name).read_text(errors="replace").strip()
        except Exception:
            said = ""
        tail = " | ".join(said.splitlines()[-3:]) if said else "(nothing)"
        if "root" in said and "sandbox" in said:
            tail += ("  — Chrome will not run as root. Run this server as your "
                     "normal user, which is how it is meant to be used anyway.")
        elif "cannot open display" in said.lower() or "DISPLAY" in said:
            tail += ("  — no desktop to open a window on. This needs the machine "
                     "you are actually sitting at.")
        return tail

    def _page_ws(self) -> str:
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json", timeout=5) as r:
            targets = json.load(r)
        pages = [t for t in targets
                 if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
        if not pages:
            raise RuntimeError("The browser is open but has no page to talk to.")
        for t in pages:
            if "celestjux" in t.get("url", "") or "pixel-room" in t.get("url", ""):
                return t["webSocketDebuggerUrl"]
        return pages[0]["webSocketDebuggerUrl"]

    async def _send(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.port:
            raise RuntimeError("Nothing is open yet — call `open` first.")
        self._msg_id += 1
        want = self._msg_id
        async with websockets.connect(self._page_ws(), max_size=64 * 1024 * 1024) as ws:
            await ws.send(json.dumps({"id": want, "method": method, "params": params}))
            while True:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
                if msg.get("id") == want:
                    return msg.get("result", {})

    async def evaluate(self, expression: str) -> Any:
        result = await self._send("Runtime.evaluate", {
            "expression": expression, "returnByValue": True, "awaitPromise": True})
        if "exceptionDetails" in result:
            d = result["exceptionDetails"]
            raise RuntimeError(
                f"{d.get('text', '')} {(d.get('exception') or {}).get('description', '')}".strip())
        return result.get("result", {}).get("value")

    async def call(self, verb: str, args: list[Any]) -> Any:
        # cjx never throws; it returns {error, hint}. The one thing that can go
        # wrong here is cjx being absent, which means the page is still on the
        # password screen — say that, rather than leaking a ReferenceError.
        inner = json.dumps(args)[1:-1]
        out = await self.evaluate(
            f"(function(){{var c={CJX_HANDLE};"
            f"return c ? c.{verb}({inner}) : null;}})()")
        if out is None:
            return {"error": "the editor is not open yet",
                    "hint": "the page is still on the password screen — ask the human "
                            "to type it, then call `ready`. Do not retry in a loop."}
        return out

    async def has_cjx(self) -> bool:
        return bool(await self.evaluate(f"!!({CJX_HANDLE})"))

    async def screenshot(self) -> bytes:
        r = await self._send("Page.captureScreenshot", {"format": "png"})
        return base64.b64decode(r.get("data", ""))

    def close(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None
        self.port = None


browser = Browser()
server = MCPServer(
    "pixelroom",
    instructions=(
        "Decorate a pixel room alongside the human at the keyboard.\n\n"
        "Start with `open_editor`. If the human gives you the password, `login` "
        "types it in for them; if they do not offer it, do not ask — say you will "
        "wait, and let them type it in the browser window. Either way `ready` "
        "tells you when you are through.\n\n"
        "Then call `help` before anything else: the editor is deployed separately "
        "from this server, so the page is the source of truth for what it can do, "
        "not this tool list.\n\n"
        "Work in tile coordinates. The human has a live x/y readout under their "
        "canvas, so a coordinate they say out loud is one you can pass straight in. "
        "Place one thing and stop — they are looking at the same screen and will "
        "move it if you were wrong."),
)


def j(value: Any) -> str:
    return json.dumps(value, indent=2)


@server.tool()
def open_editor(url: str = "") -> str:
    """Open the editor in a browser, using a dedicated profile — never the human's
    everyday one. It lands on a password screen: use `login` if the human gave you
    the password, otherwise wait for them to type it and call `ready`."""
    try:
        return j(browser.launch(url or EDITOR_URL))
    except Exception as exc:
        return j({"error": str(exc)})


@server.tool()
async def ready() -> str:
    """Is the editor open and past the password screen? `waiting: true` means the
    human is still logging in. That is not an error — wait for them, do not retry
    in a loop."""
    try:
        if not browser.port:
            return j({"open": False, "hint": "call `open_editor` first"})
        if not await browser.has_cjx():
            return j({"open": True, "waiting": True,
                      "hint": "the human has not typed the password yet"})
        return j({"open": True, "waiting": False,
                  "room": await browser.call("describe", [])})
    except Exception as exc:
        return j({"error": str(exc)})


@server.tool()
async def help() -> str:
    """The live list of verbs the page supports, straight from the page itself.
    Call this first — it, not this tool list, is the contract."""
    return j(await browser.call("help", []))


@server.tool()
async def describe() -> str:
    """The whole room as objects, with counts and the agent names living in it."""
    return j(await browser.call("describe", []))


@server.tool()
async def at(x: int, y: int) -> str:
    """What is on one tile, and the floor under it."""
    return j(await browser.call("at", [x, y]))


@server.tool()
async def search(q: str, limit: int = 40) -> str:
    """Find pieces by name across the whole pack. Most pack pieces are numbered
    rather than named (`bedroom/136`), so when a word finds nothing that is the
    pack, not a bug — browse a theme instead."""
    return j(await browser.call("search", [q, limit]))


@server.tool()
async def themes() -> str:
    """The built-in types, and every pack theme with how many pieces it holds."""
    return j(await browser.call("themes", []))


@server.tool()
async def place(piece: str, x: int, y: int, owner: str = "", blockers: bool = True) -> str:
    """Place a piece at a tile. Wide furniture gets its collision tiles laid for
    you. Pass `owner` to make it an agent's machine; `blockers=false` to leave it
    walk-through. Returns the new id."""
    opts: dict[str, Any] = {}
    if owner:
        opts["owner"] = owner
    if not blockers:
        opts["blockers"] = False
    return j(await browser.call("place", [piece, x, y, opts]))


@server.tool()
async def move(id: str, x: int, y: int) -> str:
    """Move a piece to another tile, by the id `place` or `describe` gave you."""
    return j(await browser.call("move", [id, x, y]))


@server.tool()
async def remove(id: str) -> str:
    """Remove a piece. Its collision tiles go with it — never clean those up
    yourself, and never leave one behind: an orphaned blocker is an invisible wall
    standing in open floor that nobody can find by looking at the room."""
    return j(await browser.call("remove", [id]))


@server.tool()
async def paint(x: int, y: int, kind: str) -> str:
    """Paint one tile: floor, wall, door, grass or water."""
    return j(await browser.call("paint", [x, y, kind]))


@server.tool()
async def desk(x: int, y: int, owner: str = "") -> str:
    """Stamp a whole agent pod at once: desk, collision tiles, monitor and chair.
    This is how a room says how many agents it has."""
    return j(await browser.call("desk", [x, y, owner]))


@server.tool()
async def undo() -> str:
    """Undo one step — the same stack as the human's Ctrl+Z. Prefer letting them
    undo their own way; use this to take back something you just did."""
    return j(await browser.call("undo", []))


@server.tool()
async def login(password: str) -> str:
    """Type the password into the gate for the human, when they have given it to
    you. Fills the form and submits it, then reports whether you are through.

    Never repeat the password back in your own text, and never write it into a
    file, a note or a config. If the human has not offered it, do not ask — say
    you will wait, and let them type it in the browser window themselves."""
    try:
        if not browser.port:
            return j({"error": "nothing is open", "hint": "call `open_editor` first"})
        if await browser.has_cjx():
            return j({"open": True, "waiting": False, "note": "already through"})

        filled = await browser.evaluate(
            "(function(){var f=document.querySelector('input[name=password]');"
            "if(!f) return 'no-form';"
            f"f.value={json.dumps(password)};f.form.submit();return 'submitted';}})()")
        if filled == "no-form":
            return j({"error": "no password box on this page",
                      "hint": "the browser may not be on the editor — call "
                              "`open_editor`, or check what page is showing"})

        # The submit is a round trip; give it a moment before judging it.
        for _ in range(20):
            await asyncio.sleep(0.5)
            if await browser.has_cjx():
                return j({"open": True, "waiting": False,
                          "room": await browser.call("describe", [])})
            if await browser.evaluate(
                    "document.body.textContent.indexOf('Wrong password') >= 0"):
                return j({"error": "wrong password",
                          "hint": "ask the human to check it — do not guess, and "
                                  "do not try variations"})
        return j({"open": True, "waiting": True,
                  "hint": "submitted, but the editor has not appeared. The room "
                          "editor lives at the /room/ path — try `ready` again."})
    except Exception as exc:
        return j({"error": str(exc)})


@server.tool()
async def look() -> str:
    """Screenshot the page to a file, for judging how something reads rather than
    where it sits. Returns the path — open it with your own file reader. `describe`
    is cheaper and usually enough."""
    try:
        png = await browser.screenshot()
        out = Path(tempfile.gettempdir()) / "pixel-room-look.png"
        out.write_bytes(png)
        return j({"path": str(out), "bytes": len(png)})
    except Exception as exc:
        return j({"error": str(exc)})


@server.tool()
async def call(verb: str, args: list[Any] | None = None) -> str:
    """Call any cjx verb by name, including ones newer than this server. The editor
    is deployed separately, so `help` may list verbs that have no tool here — this
    is how you reach them without reinstalling anything."""
    return j(await browser.call(verb, args or []))


if __name__ == "__main__":
    try:
        server.run("stdio")
    finally:
        browser.close()
