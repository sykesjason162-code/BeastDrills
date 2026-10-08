# Help page screenshots

Drop PNGs here with these exact names -- `help.html` already references
them, so they appear as soon as the file exists (static files are served
fresh per request; no restart needed).

| filename                     | what it should show |
|------------------------------|---------------------|
| `menu-bar.png`               | The menu bar strip across the top of the screen |
| `drills-menu.png`            | The Drills menu open, list visible |
| `drills-page.png`            | Drills page: search box, filters, grid |
| `diagnostics-window.png`     | Diagnostics panel, live match, both players |
| `tally-panel.png`            | Tally panel, both columns |
| `wongscript-tab.png`         | Edit Drill modal, WongScript tab open |
| `character-dummy-fields.png` | Form tab, Character/Dummy dropdowns |
| `export-import.png`          | Drills page toolbar: Export All / Import |

Until a file exists its `<img>` renders broken with a "Screenshot
needed" caption -- that is intentional, so a missing one is obvious
rather than silently absent.

## Taking the in-game ones

`tools/screenshot.ps1` captures the DESKTOP, so the game has to be the
foreground window; it photographs whatever is in front otherwise. Stage
the panels with `tools/bd.ps1 show|hide -Target diagnostics|tally_panel`
rather than by hand, then crop to our own UI.

Do NOT try to drive the menus with synthetic mouse or keyboard input.
SF6 ignores injected input entirely -- SendInput moves, clicks and
keypresses all reach the foreground window and produce no hover, no
menu and no hotkey. Anything behind a dropdown needs a real person to
click it. (`SetPanel` also has no `trace` case, so the Trace panel
cannot be staged from the dev channel at all yet.)

Crop tight. These are screenshots of OUR interface, not of the game --
keep Capcom's UI and branding out of the frame.
