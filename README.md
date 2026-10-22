# Beast Drills — Beta

Spaced-repetition training for Street Fighter 6.

> **This is a beta.** It works, but it has rough edges and a short list of
> known problems further down this page.
> Back up `Documents\Beast Drills` now and then, and please report anything
> that looks wrong on the page you downloaded it from.

> ⚠️ **Do not use the REFramework on Nexus Mods.** It is an older build
> (June 2025) and Beast Drills cannot run on it. Mod managers install it
> automatically, and it can replace a newer REFramework you already had,
> after which the game closes or Beast Drills never appears. Get
> REFramework **nightly 01394 from GitHub** instead (both zips, same
> page) — see [What you need](#what-you-need). If Vortex or Fluffy already
> installed the Nexus one, disable it there first.

Beast Drills treats execution like flashcards. You practise a drill, it
grades the rep from what actually happened in the game, and it schedules
the next showing — often for the ones you keep missing, rarely for the ones
you have down. The scheduling is the same idea Anki uses; the grading reads
the game's own state, so a counter hit counts because the game says it was
one.

It runs entirely on your machine. Drills run in offline Training Mode;
your real matches are only **read**, to grade them afterwards — see
[Safety](#safety).

![Your profile: drills, sessions, success rate and best streak for each character](https://raw.githubusercontent.com/sykesjason162-code/BeastDrills/main/screenshots/profile.jpg)

## What it looks like

**Your drills.** Search, filter by character, star favourites, and see how
each one is going at a glance. New drills can be written right here, or
saved straight from a Training Mode setup.

![The Drills page](https://raw.githubusercontent.com/sykesjason162-code/BeastDrills/main/screenshots/drills.jpg)

**How it is sticking.** A practice calendar, how often you pass drills you
have already learned, and a forecast of what comes due, the way Anki shows
it.

![Stats](https://raw.githubusercontent.com/sykesjason162-code/BeastDrills/main/screenshots/stats.jpg)

---

## What you need

- **Street Fighter 6** on PC.
- **REFramework nightly 01394, with its .NET plugin support** — from
  <https://github.com/praydog/REFramework-nightly/releases/tag/nightly-01394-ec6c81fd39831b328027ae00e102bc9c9c3f8aa5>.
  Download **both** `REFramework.zip` and `csharp-api.zip` from that one
  page and extract both into your Street Fighter 6 folder. Then confirm
  the game boots with its menu (**Insert**) before adding Beast Drills.

  **Not the REFramework on Nexus Mods.** That one is an older build, from
  June 2025, and Beast Drills does not run on it. If Vortex or Fluffy
  already installed it for you, disable it there first, or it will put the
  old build back over the new one.

  The two zips must come from the **same** nightly. Mixing them is what
  happens when a mod manager replaces one half, and it stops Beast Drills
  appearing (see *Nothing appears in-game* below). Newer nightlies may well
  work; 01394 is the one this beta was tested on.
- **The .NET 10 Runtime (x64)** — <https://dotnet.microsoft.com/download/dotnet/10.0>.
  REFramework's .NET plugin support runs on it.
- **Python 3.10 or newer**, from <https://www.python.org/downloads/>. Tick
  **"Add python.exe to PATH"** during install; the launcher needs to find it.
- **Flask**, one Python package the web dashboard uses. You do not need to
  install it yourself: the first time you run the launcher it notices it is
  missing and **asks** before installing it. That is the only time anything
  here downloads anything, and only if you say yes. Without the Web
  Dashboard option (below) Flask is never needed or asked about.

## Installing

Beast Drills comes as **two options in one zip**:

- **Beast Drills - Core** — required. The in-game mod and the background
  service that grades and schedules your drills.
- **Beast Drills - Web Dashboard** — optional. The browser pages: your
  drills, stats, matches and the WongScript editor. Leave it out only if
  you use a dashboard of your own (see *Using your own dashboard*).

Any of these three ends up in the same place. It does not matter which
drive your Steam library is on.

- **Vortex:** use **Mod Manager Download** on the Files tab, then enable and
  deploy. Vortex's Street Fighter 6 support hands the mod to Fluffy Mod
  Manager, so open Fluffy afterwards and tick the options you want.
- **Fluffy Mod Manager:** put the zip, unopened, into Fluffy's
  `Games\StreetFighter6\Mods` folder and refresh. Beast Drills shows as one
  entry with both options inside: tick **Core**, and **Web Dashboard**
  unless you are using your own.
- **By hand:** the zip holds two folders. Copy what is inside
  `Beast Drills - Core` into your Street Fighter 6 folder, so that
  `reframework\` merges with the one already there, then do the same with
  `Beast Drills - Web Dashboard` if you want it. (The `modinfo.ini` and
  `screenshot.png` in each are for Fluffy; you can leave them out.)

**Upgrading from 0.1:** the options have new names. If Fluffy still lists
the old single "Beast Drills" entry, untick it before ticking the new ones,
so the two do not install over each other.

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

### Uninstalling

**If you installed through Vortex, untick Beast Drills in Fluffy first.**
Vortex hands Street Fighter 6 mods to Fluffy Mod Manager, and Fluffy is
what puts the files in the game folder. Disabling the mod in Vortex only
takes the zip back out of Fluffy's folder; the installed files stay. So:
open Fluffy, untick Beast Drills, close Fluffy, then disable or remove it
in Vortex.

Installed by hand: delete `reframework\plugins\managed\BeastDrills.dll`,
`reframework\data\BeastDrills_data\`, `dashboard\` and the two `.bat`
files. Your drills in `Documents\Beast Drills` are not touched either way.

## Running it

1. The **first time**, double-click **`Start Beast Drills.bat`** in the game
   folder. It may ask to install Flask (see above), then runs in the
   background with no window of its own and opens your browser at
   <http://localhost:8765>, or wherever `beast_drills.ini` says. (With
   Core alone it starts only the service, and opens nothing.)
   After that, **the game starts it for you**: when Street Fighter 6 starts
   and Beast Drills is not running, it starts it in the background (no
   browser). The menu bar reads **Starting** for a few seconds while it
   comes up. Turn this off with `auto_start = false` under `[dashboard]` in
   `beast_drills.ini`. The .bat still works whenever you like.
2. Launch Street Fighter 6 and enter **Training Mode**.

   > **The first launch can look frozen for a couple of minutes** on the
   > Capcom and startup screens. That is REFramework building its .NET
   > files, the first time after you install it, after every Street
   > Fighter 6 update, and after you update REFramework. It is not a
   > crash: leave it running.
   > Closing it only makes the next launch start the build over.

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
- **cap how much space recorded matches use**, with `max_size_mb` under
  `[matches]` -- the oldest are cleared first, starred ones never are.
  An ini from an earlier version will not have this line; add it under a
  `[matches]` heading, or delete the file to get a fresh one.
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

### Using your own dashboard

Install **Core** only. The service keeps running without the Web Dashboard
option, the launcher stops asking about Flask, and the in-game menu says
the dashboard is not installed instead of offering a page that is not
there. Everything a dashboard needs is in `Documents\Beast Drills`:

- `shared_database.json` -- your drills and their schedule.
- `stats.db` -- SQLite: every session's result, and every match round by
  round.
- `runtime\live_status.json` -- what the game sees right now, rewritten
  every frame.

**Read those, but do not write them.** The service owns them and will
overwrite your changes. To change something, drop an event into `outbox\`
-- one JSON file per change, written to a `.tmp` name and then renamed, so
the service never reads half a file. `dashboard\beast_drills\outbox_writer.py`
in Core does exactly that, and the Web Dashboard's `dashboard.py` is a
working example of every event it sends.

Beast Drills itself never talks to the internet. It does not phone home,
check for updates or send anything anywhere. The dashboard is a local
server for the ordinary reason: so two programs can read the same file.

---

## Your first session

**DRILLS → Start Session** runs whatever is due. A briefing appears saying
what the drill wants; **Start Drill** begins it, and the rep counter sits at
the right-hand end of the menu bar.

That is the whole loop. Everything below is optional.

**You start with 10 drills ticked for practice.** Over 2,300 more come with
it — combos for every character (from the SuperCombo wiki) and the belt
drills — waiting in the library. Tick the ones you want in **DRILLS** or on
the dashboard's Drills page; with nothing ticked, everything is in rotation.

- **Combo drills show the combo on screen**, the way SF6's Combo Trials do:
  the steps down the left, each lighting up when you land *that* move, with
  DR / AIR / HOLD beside the steps that need them, and **SUCCESS** when the
  rep is a success. Turn it off with **VIEW → Combo Steps**, or the
  checkbox on a combo drill's briefing.
- **Belts.** Belt drills — marked with a belt icon on the Drills page — are
  the curriculum: White through Black, a set of skills each. Your belt for
  each character is worked out from how you do on them, and shown on your
  profile. They work like any drill, but are read-only so they cannot be
  changed by accident; **Duplicate** one to make your own version (a copy
  does not count toward a belt).
- **Practice, without the schedule.** **DRILLS → Practice** sets the game
  up exactly like a drill and gets out of the way: no 10-rep stop, no
  grading prompt, and nothing is scheduled or added to your stats. Play as
  long as you like; the bar shows how many reps landed, and **Stop
  Practice** (or Numpad 2) puts your Training settings back.
- **Save the combo you just did.** Land a combo of two hits or more, then
  **FILE → Save Last Combo as Drill**: it becomes a combo drill for your
  character, named after the combo and graded by the same rules as every
  combo drill. The menu says what it was saved as, or why it could not be.
- **Drill cards say who you practised it against** -- a row of "vs Mai 12"
  chips under the characters you played it as.

- **TALLY** counts what happened both ways — what you did to them and what
  they did to you — across a session or a whole practice night.
- **The dashboard** is where you read your record and write new drills. It
  has its own help page, linked in the header.
- **Matches.** Every real match you play — Arcade, Versus, Ranked, Casual,
  Battle Hub, Custom Room — is recorded in the background and graded on
  the dashboard's **Matches** page, round by round. The newest one decides
  which due drills come first in your next session: a drill that works in
  Training Mode but keeps failing you in matches is exactly the one to
  practise. Nothing to start and nothing on screen; just play. The
  briefing says when a drill is next because of your last match.
  Your **overall** record keeps every match forever; the round-by-round
  detail of old matches is cleared once it passes a size you choose (50 MB
  by default, thousands of matches -- see Settings). **Star** a match to
  keep its detail for good.

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
check fails it writes nothing at all. Online matches, Online Training,
Battle Hub, replays and spectating are all refused, and if it cannot tell
which mode the game is in, it refuses too.

That check is deliberately the strictest part of the whole thing.

**During a match, including an online one, it only reads.** To grade your
matches it reads who won each round, how, and the same hit/block/throw
events the tally counts, and saves them on your PC for the dashboard. It
never changes anything in a match, and while an online match is on it
draws nothing on screen and ignores its hotkeys, so nothing it knows can
be seen mid-match.

Be clear-eyed about what that is: REFramework itself is a third-party
tool that Capcom has not approved, and reading the game during an online
match is still running a mod while you play online. Capcom has not said
anything about client-side mods either way, and the community reading is
that read-only mods are not acted on — but nobody can promise that.

---

## If something looks wrong

**The game sits on the Capcom screens for minutes.**
Normal on the first launch after installing REFramework, after every
Street Fighter 6 update, and after updating REFramework: it is rebuilding
its .NET files. Wait it
out. If it never gets past them, check `re2_framework_log.txt` in the game
folder for errors.

**The menu bar says "Jammed."**
The dashboard is not running, or it stopped, and the game could not start
it. Run `Start Beast Drills.bat` -- if Flask is missing it asks to install
it, which the game will not do by itself. Hover over "Jammed" for the
reason. Jammed means the game cannot reach it — results are not being saved
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
for `BeastDrills.dll` under `reframework\plugins\managed\`. Then open
`re2_framework_log.txt` in the game folder and search for `BeastDrills`:

- `overlay off: REFramework's core ... and its csharp-api are from
  different builds` — the two REFramework zips came from different
  nightlies, usually because a mod manager installed the Nexus copy over
  one of them. Reinstall both from the same nightly (see *What you need*).
  Beast Drills turns its overlay off rather than let the mismatch crash
  the game.
- No `BeastDrills` lines at all — REFramework's .NET support is not
  loading. Check `csharp-api.zip` was extracted and the .NET 10 Runtime is
  installed.

---

## Known issues in this beta

- **Stop your session before you queue for a match.** Queueing Ranked or
  Casual from Training Mode takes you to the match and back. Beast Drills
  stops writing to the game as soon as it detects an online match, but the
  session keeps running, so you return to a drill that is still counting. Stop it first (**Numpad 2**) and start again afterwards.
- **The belt drills are first drafts.** The curriculum's 155 hand-written
  drills have not all been played through yet, so some will need their
  timing or criteria adjusted. Report one that grades wrong and it will be
  fixed in an update.
- **Belts come from drill results only.** A rank test in real matches is
  planned for a later 0.2 update.
- **PC, WHIFF and frame counts are not shown on combo steps.** No drill's
  notation can say them yet.

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

## Credits

The combo drills and the frame data come from the
[SuperCombo wiki](https://wiki.supercombo.gg/w/Street_Fighter_6) and its
contributors. Each combo drill names it in its description.

## Supporting it

Beast Drills is free and always will be. If it has helped your game and you
want to say thanks, you can
[donate through PayPal](https://www.paypal.com/donate/?hosted_button_id=GQH87AZWTZQJS)
or [buy me a coffee](https://buymeacoffee.com/chipflip). It is never expected, and nothing in the mod is locked behind it.
