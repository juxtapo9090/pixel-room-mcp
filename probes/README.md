# probes

Not needed to use pixel-room. These are how it was checked, kept so it can be
checked again on a machine that behaves differently.

Each one drives the server's guts directly — no MCP client in the way — so a
failure points at the browser, the port or the page rather than at your agent.

```sh
uv run probes/probe_mcp.py   <password>   # launch, reach cjx, place, screenshot
uv run probes/probe_login.py <password>   # wrong password, then the real one
```

The password is an argument, never a file. Both open a browser window and close
it again.
