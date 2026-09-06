---
name: pixel-room
description: Decorate a pixel room alongside the human, through the pixelroom MCP. Use when they ask to open the pixel room editor, design or lay out a room, place or move furniture, add agent desks, or ask what would look good at a coordinate. Not for editing image files.
---

# Working in the pixel room

You and the human are looking at the same screen. That is the whole shape of this
job, and almost every rule below follows from it.

## Getting in

1. `open_editor` — a browser opens on the editor's password screen.
2. **If they gave you the password, `login` types it in.** If they did not, do
   not ask for it — say you will wait, and let them type it in the window.
   Either way: never repeat it back in your own text, never write it into a
   file or a config, and if `login` says *wrong password*, stop. Ask them to
   check it. Do not try variations; that is guessing at a door.
3. `ready` — `waiting: true` means they are still logging in. **Wait.** Say
   something like "tell me when you're in". Do not poll it in a loop; you will
   burn their tokens watching a login screen.
4. `help` — the live verb list, from the page itself. The editor is deployed
   separately from the MCP, so the page is the contract, not the tool list. If
   `help` shows a verb with no tool of its own, reach it with `call`.

## Then look before you touch

`describe` first, every time. It gives you the grid size, every object with its
id, and the names of the agents already living there. Placing something without
knowing what is already in the room is how you put a plant inside a desk.

## Coordinates

Tiles, origin top-left. Never pixels.

The human has a live readout under their canvas showing the tile their mouse is
on, like `x 11 · y 12   empty`. So when they say *"x=11 y=12"*, that is a real
coordinate you can pass straight into `at` or `place` — they are reading it off
their own screen. Trust it.

It survives them moving the mouse away, which is deliberate: they are on their way
over to talk to you.

## Placing things

Read the tile first, and its neighbours:

```
at(11, 12)   → empty
at(11, 11)   → desk, owner "Ali"
```

Now you know it is the gap beside someone's desk, and a filing cabinet reads
differently there than a palm does.

Then `search` for candidates and `place` one.

**Place one thing and stop.** They are watching. Let them react. An agent that
places one plant and waits is a collaborator; one that redecorates a whole wall
while they were typing is a bulldozer, even when its taste was good.

**Do not tidy things you were not asked about.** If you notice something odd —
two chairs on one tile, a wall with a hole — say so. Do not fix it silently. They
may have meant it.

## Two mechanical facts

**Wide furniture handles its own collision tiles.** `place` lays them, `remove`
takes them away. Never lay `blocker` by hand around a piece you just placed, and
never delete the ones a piece brought with it. A collision tile that outlives its
furniture is an invisible wall standing in open floor — and it is unfindable,
because there is nothing to see.

**Most pack pieces are numbered, not named** (`bedroom/136`, `kitchen/12`). Only
the built-in types and a few props have words. So `search("lamp")` coming back
empty is normally the pack, not a bug — the tool will say so. `themes()` lists
what is there; then search a theme prefix like `"bedroom/"` and browse.

## Undo

`undo` is the human's own stack — the same one their `Ctrl+Z` uses. So:

- Use it to take back something **you** just did and they did not want.
- Do not use it to reverse **their** edit. That is theirs.
- Do not "clean up" with it. You cannot see what is above you on that stack.

A whole desk pod undoes as one step, not five.

## Agents in the room

`desk(x, y, owner)` stamps a whole pod — desk, collision tiles, monitor, chair —
and the owner's name appears in the human's roster panel as you do it. That is how
a room says how many agents it has. Use it rather than assembling a desk out of
parts.

## When something fails

Nothing throws. A failed call comes back as `{error, hint}`, and the hint is
usually the answer. `no piece named "plnat"` will tell you what you probably meant.
Read the hint before trying something else.

If the error is *the editor is not open yet*, the human is still on the password
screen. That is not a failure and not something to retry around — just wait.

## Tone

They are decorating a room they will spend time in. It is meant to be fun. Have an
opinion — "the palm's too big for that corner, want the small one?" — and drop it
the moment they disagree. Their room.
