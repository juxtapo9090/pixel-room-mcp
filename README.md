# pixel-room

Decorate a pixel room together with your AI agent. You drag things with a mouse;
it places things by name and coordinate. Same room, same screen, same moment.

**The editor:** <https://celestjux-editors.vercel.app/>
**The password:** ask Aizat. It is spoken, never written down — see *Why there is
a password* below.

```
you ──┐
      ├──→  the editor page  ←── window.cjx ←── this MCP ←── your agent
mouse ┘        (the room)
```

---

## What it is actually like

You are laying out a room. There is an empty patch and you cannot decide what
goes there. Under the canvas is a live readout of the tile your mouse is on:

```
x 11 · y 12    empty
```

So you say to your agent:

> dear, x=11 y=12 — can we put something nice here?

It looks at that tile, looks at what is beside it, searches 5537 pieces, and
places one. You watch it land, decide the palm is too big, and drag it two tiles
left. It is on your undo stack, so `Ctrl+Z` takes it back — yours or its, same
stack.

That is the whole idea. Not an agent that redecorates while you are out. One that
is in the room with you.

---

## Install

You need [uv](https://docs.astral.sh/uv/) and any Chrome-family browser (Chrome,
Chromium, Brave or Edge). Nothing else — no virtualenv, no `pip install`. The
dependencies are declared inside the script and install themselves the first time
it runs.

```sh
git clone https://github.com/<you>/pixel-room-mcp
```

Then point your agent at it. For Claude Code, `.mcp.json`:

```json
{
  "mcpServers": {
    "pixelroom": {
      "command": "uv",
      "args": ["run", "/full/path/to/pixel-room-mcp/pixel_room_mcp.py"]
    }
  }
}
```

Cline, Cursor and the rest take the same `command` / `args` pair.

Then say: **"open the pixel room editor"**.

### Settings, if you need them

| Variable | Does |
|---|---|
| `PIXEL_ROOM_URL` | a different editor to open |
| `PIXEL_ROOM_BROWSER` | full path to a browser, if it is somewhere unusual |
| `PIXEL_ROOM_PROFILE` | where the throwaway browser profile lives |

**Run it as your normal user.** Chrome refuses to start as root, and this asks it
to open a window on your desktop — there is no reason for it to be root anyway.

---

## Why there is a password

The artwork is [LimeZu's Modern Interiors](https://limezu.itch.io/), which is paid
and may not be redistributed. 
* Just to Avoid "Abuse" .. Nah its just for fun amongs friends :D

**Two ways in, both fine.** Tell your agent the password and `login` types it in
for you, or leave it out and type it in the browser window yourself — `ready`
answers *waiting*, not an error, so your agent knows to wait rather than hammer.

The one thing worth knowing before you pick: **a password you type into a chat is
in that chat's history**, wherever your agent's provider keeps it. It is already
there the moment you say it, so having the agent use it costs nothing extra — but
if that bothers you, type it in the browser instead and never say it out loud.

---

## The browser it opens

A **dedicated, empty profile**, never your everyday one.

This matters more than it looks. Driving a browser needs a debugging port open on
it, and a debugging port on the profile you actually browse with hands every
process on your machine every tab you are signed into — mail, bank, chat, all of
it. A throwaway profile costs nothing and closes that completely. It starts empty,
it knows nothing about you, and the only thing it has ever visited is the editor.

That is why this launches its own browser instead of attaching to the one you have
open.

---

## The tools

Start with `open_editor`, then `login` or `ready`, then **`help`**.

`help` matters: the editor is deployed separately from this server, so the page is
the source of truth for what it can do — not this list. If the page grows a verb,
`help` will show it and `call` will reach it, with nothing to reinstall.

| | |
|---|---|
| `open_editor` · `login` · `ready` | open a browser; type the password if given one; are we through |
| `help` | the live contract, from the page |
| `describe` · `at` | the whole room; one tile |
| `search` · `themes` | find pieces |
| `place` · `move` · `remove` | furniture |
| `paint` | floor, wall, door, grass, water |
| `desk` | a whole agent pod at once |
| `undo` · `look` | the human's undo stack; a screenshot |
| `call` | any verb `help` lists, including newer ones |

Coordinates are **tiles**, origin top-left. Never pixels, in either direction.

### Two things worth knowing

**Wide furniture blocks its whole footprint automatically.** A sofa is three tiles
wide; `place` lays the collision tiles across the rest of it, and `remove` takes
them away again. Do not lay or clean them by hand. A collision tile left behind
after its furniture is gone is an invisible wall standing in open floor, and
nobody can find that by looking at the room.

**Most pack pieces are numbered, not named** (`bedroom/136`). So `search("lamp")`
finding nothing is usually the pack, not a bug — `themes()` then browsing is the
way in.

---

## What you get out

Your room saves as `room.json`, your cast as `cast.json` plus a sprite sheet each.
Hand all of it to your agent and it has a room, and the people in it.

---

## Licence

The code here is yours to use. **The artwork is not mine** — it is LimeZu's
Modern Interiors. 
