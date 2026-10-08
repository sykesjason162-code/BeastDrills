# Profile art — the PROFILE page only

Jason, 2026-08-27: *"I specifically only want these images used on the
profile page. They are center aligned and work best here. I don't want
you to use these for the drills page. Those were right aligned images and
best for drills."*

So this folder and `../characters/` are **not** interchangeable, and the
difference is framing rather than quality:

| | folder | subject sits | used by |
|---|---|---|---|
| Profile | `profile_characters/` | centred | the Profile hero block |
| Drills | `characters/` | left of centre, so the art hugs the right edge of a card | drill cards, `_card` / `_dummy` |

Measured rather than assumed: JP's profile image has its subject at 0.48
of the image width, his drill image at 0.32. Swapping them puts the
character off-centre in the hero, or crops them out of a drill card.

- Filename is `<character_id>.png`, the ids used in
  `shared_database.json` — `jp.png`, `chun_li.png`, `dee_jay.png`. The
  source files in `images/hitzone_sprites/profile-images/` use
  display-style names (`chunli`, `ehonda`, `vega_mbison`), which are
  renamed on the way in.
- A missing file just hides that one image (`onerror` in `profile.js`) —
  no broken icon and no layout shift.
- Tracked in git, deliberately. Jason's call, made twice and settled:
  the repo is private and this is a non-commercial personal tool, so
  Capcom enforcement is not a real concern. Recorded here only so a
  future public release remembers to purge both art folders from history
  first — git keeps every version of a binary forever.
