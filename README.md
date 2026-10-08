# Beast Drills — Beta

Spaced-repetition training for Street Fighter 6.

> **This is a beta.** It works, but it has rough edges and a short list of
> known problems further down this page.
> Back up `Documents\Beast Drills` now and then, and please report anything
> that looks wrong on the page you downloaded it from.

Beast Drills treats execution like flashcards. You practise a drill, it
grades the rep from what actually happened in the game, and it schedules
the next showing — often for the ones you keep missing, rarely for the ones
you have down. The scheduling is the same idea Anki uses; the grading reads
the game's own state, so a counter hit counts because the game says it was
one.

It runs entirely on your machine, in offline Training Mode.

![Your profile: drills, sessions, success rate and best streak for each character](https://raw.githubusercontent.com/sykesjason162-code/BeastDrills/main/screenshots/profile.jpg)

## What it looks like

**Your drills.** Search, filter by character, star favourites, and see how
each one is going at a glance. New drills can be written right here, or
saved straight from a Training Mode setup.

![The Drills page](https://raw.githubusercontent.com/sykesjason162-code/BeastDrills/main/screenshots/drills.jpg)

**Where you get hit.** Every hit you take or land, by height and by side,
for each matchup.

![Hit zones](https://raw.githubusercontent.com/sykesjason162-code/BeastDrills/main/screenshots/hit_zones.jpg)

**How it is sticking.** A practice calendar, how often you pass drills you
have already learned, and a forecast of what comes due, the way Anki shows
it.

![Stats](https://raw.githubusercontent.com/sykesjason162-code/BeastDrills/main/screenshots/stats.jpg)

---

## What you need

- **Street Fighter 6** on PC.
- **REFramework**, with .NET plugin support —
  <https://github.com/praydog/REFramework>. Install that first and confirm
  the game boots with its menu (**Insert**) before adding Beast Drills.
- **Python 3.10 or newer**, from <https://www.python.org/downloads/>. Tick
  **"Add python.exe to PATH"** during install; the launcher needs to find it.
- **Flask**, one Python package the dashboard uses. You do not need to
  install it yourself: the first time you run the launcher it notices it is
  missing and **asks** before installing it. That is the only time anything
  here downloads anything, and only if you say yes.

## Installing

Any of these three ends up in the same place. It does not matter which
drive your Steam library is on.

- **Vortex:** use **Mod Manager Download** on the Files tab, then enable and
  deploy. Vortex's Street Fighter 6 support hands the mod to Fluffy Mod
  Manager, so open Fluffy afterwards and make sure Beast Drills is ticked.
- **Fluffy Mod Manager:** put the zip, unopened, into Fluffy's
  `Games\StreetFighter6\Mods` folder, refresh, and tick Beast Drills.
- **By hand:** extract the zip into your Street Fighter 6 folder, so that
  `reframework\` merges with the one already there.

Whichever you use, these land in your Street Fighter 6 folder:

    ...\Street Fighter 6\
        reframework\plugins\managed\BeastDrills.dll
        reframework\data\BeastDrills_data\
        dashboard\
        Start Beast Drills.bat
        Stop Beast Drills.bat

**Leave `dashboard\` and the two `.bat` files where they land**, beside
`reframework\`. That is how the dashboard finds the game's files; moved
somewhere else, it cannot. To find the folder, right-click Street Fighter 6
in Steam → Manage → Browse local files.

## Running it

1. Double-click **`Start Beast Drills.bat`** in the game folder. It runs in
   the background, with no window of its own, and opens your browser at
   <http://localhost:8765>, or wherever `beast_drills.ini` says. The first
   time, it may ask to install Flask (see above).
2. Launch Street Fighter 6 and enter **Training Mode**.
3. Move the mouse to the very top of the screen — the Beast Drills menu bar
   appears. **F1** pins it open.

To stop it, double-click **`Stop Beast Drills.bat`**. Restarting your PC
stops it too.

Leave the dashboard running while you play. The game and the browser share
one database through it, so with it closed the game cannot save results.

## Settings

Everything you can change lives in one file:

    reframework\data\BeastDrills_data\beast_drills.ini

Open it in Notepad. Every setting has a note above it saying what it does,
and each one is optional -- delete a line and it goes back to its default.
Delete the whole file and Beast Drills carries on with defaults and writes
a fresh one.

You would change it to:

- **use a different port**, if something else already has 8765
- **watch your stats from your phone**, by setting `host = 0.0.0.0` (only
  on a network you trust -- there is no password)
- **run the dashboard on another computer** -- see below
- **switch language**

### Where your drills are kept

    Documents\Beast Drills

Your drills, your history, your layout and your hotkeys go there, and
the folder is made for you the first time you run the mod.

It is deliberately **outside** the game folder. Vortex and Fluffy own
that folder, and some of their update paths empty a mod's directory
before writing the new version -- which would take everything you had
practised with it. Nothing in `Documents\Beast Drills` is ever part of
the download, so updating and uninstalling both leave it alone.

Put it somewhere else if you prefer -- another drive, a synced folder:

    [paths]
    data_dir = D:/BeastDrills

### Running the dashboard on another computer

The game always writes to its own disk. To read it from elsewhere, share
your `Beast Drills` folder over the network, then on the OTHER machine
set both paths -- your data, and the game's own files:

    [paths]
    data_dir = //gaming-pc/Beast Drills
    install_dir = //gaming-pc/BeastDrills_data

    [dashboard]
    host = 0.0.0.0
    public_url = http://other-pc:8765

`public_url` is what the in-game menu opens. The game cannot work out
another machine's name on its own, so tell it once here.

Both computers need to reach that share. The dashboard has **no password
of its own**, so anyone who can reach that address can see your stats and
edit your drills. On a home network that is usually what you want. Putting
it somewhere the wider internet can reach means putting something in front
of it -- a login, a reverse proxy, a tunnel -- because Beast Drills will
not ask for one.

That is a warning about what it does not do, not a rule about what you may
do with it. If you want to host dashboards for other people, or run a
community where players show the parts of their practice they want seen and
keep the rest behind a login, go ahead and build it -- the data is plain
JSON and the server is yours.

Beast Drills itself never talks to the internet. It does not phone home,
check for updates or send anything anywhere. The dashboard is a local
server for the ordinary reason: so two programs can read the same file.

---

## Your first session

**DRILLS → Start Session** runs whatever is due. A briefing appears saying
what the drill wants; **Start Drill** begins it, and the rep counter sits at
the right-hand end of the menu bar.

That is the whole loop. Everything below is optional.

- **TALLY** counts what happened both ways — what you did to them and what
  they did to you — across a session or a whole practice night.
- **The dashboard** is where you read your record and write new drills. It
  has its own help page, linked in the header.

### Hotkeys

| Key | |
|---|---|
| **F1** | Keep the menu bar up (it hides itself otherwise) |
| **Numpad 1** | Show / hide the panels |
| **Numpad 2** | Start / stop a session |
| **Numpad 3** | Start / stop the tally |
| **Numpad 4** | Reset the tally |
| **Numpad 5** | Drills panel |
| **Numpad 7** | Open the dashboard in a browser |
| **Numpad 8** | Save the current Training Mode setup as a drill |
| **Numpad 9** | Tally panel |
| **Numpad 0** | Reset the window layout |
| **Ctrl + 1-9** | Start a drill you bound to that number |

---

## Safety

Beast Drills only writes to the game in **local, offline Training Mode**,
and it re-checks that every single frame rather than once at startup. If the
check fails it does nothing at all. Nothing it does is available online, and
it never touches an online mode.

That check is deliberately the strictest part of the whole thing.

---

## If something looks wrong

**The menu bar says "Jammed."**
The dashboard is not running, or it stopped. Run `Start Beast Drills.bat`
again. Jammed means the game cannot reach it — results are not being saved
while it shows.

**"Chamber Empty."**
Nothing is due right now. Pick a drill from the DRILLS menu to run one
anyway, or start a Favorites session.

**The launcher says Python was not found.**
Python is missing from PATH. Reinstall it with **"Add python.exe to PATH"**
ticked, or start it by hand:

    cd dashboard
    python -m beast_drills.service
    python -m beast_drills.dashboard

**The launcher stops at Flask, or says the dashboard did not start.**
If you answered no when it asked about Flask, or the install failed,
install it yourself and run the launcher again:

    python -m pip install flask

**The dummy stands still during a drill.**
That drill's recording slot is empty. Open it in the dashboard and give it
an action, or record one in Training Mode and save the setup over the drill.

**Nothing appears in-game at all.**
Check REFramework itself loads (**Insert** opens its menu). If it does, look
for `BeastDrills.dll` under `reframework\plugins\managed\`.

---

## Known issues in this beta

- **No scrimmage yet.** The CPU scrimmage — three matches that test
  whether a drill holds up against an opponent — is held back from this
  beta. In testing, a recording drill run after a scrimmage would not play
  until the game was restarted. It returns once that is fixed.
- **Stop your session before you queue for a match.** Queueing Ranked or
  Casual from Training Mode takes you to the match and back. Beast Drills
  stops writing to the game as soon as it detects an online match, but it
  does not yet pause the session, so you return to a drill that is still
  counting. Stop it first (**Numpad 2**) and start again afterwards.
- **A Dragon Punch anti-air does not count as an anti-air** in the tally.
  Normal anti-airs do. Specials that launch an airborne opponent are
  missed for now.

---

## Your data

Everything you make lives in `Documents\Beast Drills`, **outside** the
game folder:

- `shared_database.json` — your drills, and every schedule and streak.
- `stats.db` — the history behind the stats pages.
- `player\` — your window layout and hotkeys.

It is kept out of the game folder on purpose. Mod managers own that
folder, and some of them empty a mod's directory when they update it,
which would take all of the above with it. Nothing here is ever part of
a download, so updating and uninstalling both leave it alone.

Move it anywhere you like in `beast_drills.ini`:

    [paths]
    data_dir = D:/BeastDrills

The game folder keeps only the files that ship with Beast Drills — move
names, frame data, translations, and the settings file itself. Those are
replaced when you update, and none of them is worth backing up.

**It is still the only copy you have**, so back it up like anything else
you would miss.

You can export your drills as a `.wong` file from the dashboard at any time,
which is also how you share them with someone else.

---

Beast Drills is free. It is not affiliated with or endorsed by Capcom.
