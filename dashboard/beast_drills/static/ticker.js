(function () {
"use strict";

  const CHEESE = [

    "Every legend was once a scrub who refused to quit.",
    "The dummy never gets tired. Neither should your fundamentals.",
    "Nobody has ever regretted labbing the matchup.",
    "The lab is undefeated. Visit anyway.",
    "Drop the combo a hundred times. The magic lives in rep 101.",
    "Muscle memory doesn't check your feelings. It checks your reps.",
    "Ten minutes in the lab beats ten losses in ranked. Marginally.",
    "Your hands will learn it long after your brain gives up. Trust them.",
    "Practice doesn't make perfect. Practice makes automatic. Automatic wins.",
    "Nobody levels up on the days they felt like it.",
    "Repetition is boring. So is losing. Pick your boredom.",
    "The combo isn't hard. You're just new to it. Those are different.",
    "You are one thousand reps from not thinking about this at all.",
    "Somewhere, someone is practising the matchup they hate. Be that person.",
    "The grind is undefeated and it does not care about your excuses.",

    "Blocking is a personality trait.",
    "Neutral is just a staring contest with consequences.",
    "You miss 100% of the anti-airs you don't throw.",
    "Footsies: the art of standing slightly too far away, on purpose.",
    "Walking backwards is a legitimate strategy and I will not be taking questions.",
    "Every jump-in is a question. Learn to answer with your uppercut.",
    "The best defence is blocking. Revolutionary, I know.",
    "Patience is a move. It has zero startup and it beats mashing.",
    "Your opponent is also mashing. Be the one who isn't.",
    "Space control is just polite bullying.",
    "Throw tech is free. Free things are good. Take the free thing.",
    "You cannot be opened up if you simply refuse to press buttons. (You can. But try.)",
    "Holding back is not cowardice. It is a frame-perfect lifestyle.",
    "The gap is not a gap if you never checked it.",

    "Perfect parry, or perfectly parried. There is no third option.",
    "A dropped combo is just a hit confirm with commitment issues.",
    "The frame data doesn't lie, but it will hurt your feelings.",
    "Your execution is temporary. Your muscle memory is forever.",
    "One more rep. That's what everyone says at rep 40 too.",
    "If it works in the lab and not in a match, the problem was never the combo.",
    "Buffering: doing the input early and pretending you meant it.",
    "The link is two frames. You have two hands. The maths works out.",
    "Nobody drops the easy route. That's why it's the route.",
    "You'll hit it clean right after you stop trying to hit it clean.",

    "Losing is just winning with extra steps and more information.",
    "Mash today, read tomorrow.",
    "Wake-up DP is a cry for help. We hear you. We forgive you.",
    "Respect the reversal. Then bait it into the shadow realm.",
    "You can't spell 'fundamentals' without 'fun'. You also can't spell it without 'mental'.",
    "Salt is just unprocessed feedback.",
    "Every character is top tier when you refuse to learn the matchup.",
    "The tier list is a suggestion. Your execution is the argument.",
    "Blaming lag is free. Improving costs reps. Choose wisely.",
    "It's a 5-5. It's always a 5-5. Everything is a 5-5 if you cope hard enough.",
    "You did not lose to the character. You lost to the person holding it.",
    "The rematch button is a growth mindset with a shortcut key.",
    "Rage quitting saves zero frames of your development.",
    "There is no bad matchup, only unread frame data. (There are bad matchups.)",
    "Getting bodied is tuition. Expensive, but the lessons stick.",

    "The training dummy has seen things. The training dummy says nothing.",
    "The corner is not a place. It is a state of mind. Yours.",
    "In the corner, nobody can hear you hold back.",
    "Oki is just hospitality with intent.",
    "Meaties are affection, delivered on frame one.",
    "Your opponent respects nothing. Give them a reason.",
    "Drive Rush is a personality. Burnout is the consequence.",
    "Burnout: when your defence files for bankruptcy.",
    "Somewhere a training dummy is updating its résumé.",
    "Every dummy is somebody's main. Think about that.",
    "The dummy blocks everything and judges you silently.",

    "Confidence is a stat. Sadly it is not in the frame data.",
    "You are not stuck. You are between plateaus. That's a lateau.",
    "Believe in the you that believes in the option select.",
    "Hit them until the health bar changes colour. That's the whole game.",
    "Fighting games are chess where the pieces can uppercut.",
    "There is no secret. There is only Tuesday, and reps.",
    "Some say the perfect neutral was achieved once, in 2013, by accident.",
    "The real combo was the inputs we buffered along the way.",
    "Your inputs are valid. Your timing is a work in progress.",
    "Greatness is just consistency wearing a cool jacket.",
  ];

  const NAME_OVERRIDES = {
    jp: "JP", chun_li: "Chun-Li", dee_jay: "Dee Jay", m_bison: "M. Bison",
    c_viper: "C. Viper", aki: "A.K.I.", honda: "E. Honda",
  };
  const label = (id) =>
    NAME_OVERRIDES[id] ||
    String(id || "").split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");

  const ABANDONED = [
    "Your {c} feels abandoned.",
    "{c} has not seen daylight in a while. Just saying.",
    "{c} left a voicemail. It was mostly sighing.",
    "{c} is sitting in character select. Still waiting.",
    "{c} has drills and zero sessions. That is a cry for help.",
    "{c} has been practising alone. It is going badly.",
    "Remember {c}? {c} remembers you.",
    "{c} has started describing themselves as \"between projects\".",
    "{c} keeps checking whether the drills still work. They do.",
    "{c} is technically on the roster. Technically.",
    "{c} would settle for one round. One.",
    "You made drills for {c} and then simply... did not.",
    "{c} is dusty. Emotionally, mostly.",
    "Somewhere {c} is doing solo footsies against a wall.",
    "{c} has entered their quiet era. You did this.",
  ];

  const PUNCHING_BAG = [
    "{c} is calling the cops for domestic violence.",
    "{c} has eaten {n} rounds as your dummy and is building a case.",
    "{c} would like to be a player character for once.",
    "Someone check on {c}. That is {n} hits and counting.",
    "{c}'s lawyer has been in touch. Something about \"the corner\".",
    "{c} has absorbed {n} hits without complaint. The silence is unsettling.",
    "{c} did not consent to being this good at standing still.",
    "{c} has started flinching at the character select screen.",
    "{n} hits on {c}. At some point this becomes a hobby.",
    "{c} is unionising. The dummies have demands.",
    "{c} has requested a transfer to somebody else's training mode.",
    "{c} would like it noted that this is not a fair fight.",
    "{c} appears in your stats more than in your victories. Reflect on that.",
    "{c}: {n} hits taken, zero rounds won. A career.",
    "{c} has been the dummy so long they have stopped struggling.",
  ];

  const ONE_TRICK = [
    "Not saying you like {c}, but... {n} of your drills say otherwise.",
    "{p}% of your drills are {c}. That is not a main, that is a marriage.",
    "The character select screen is decorative at this point.",
    "Statistically speaking, you are {c}.",
    "Every drill is a {c} drill. This is a {c} household.",
    "You could play someone else. You won't, but you could.",
    "{n} {c} drills. The roster has thirty-odd others, for reference.",
    "Loyalty, or fear of learning a new matchup? Only you know.",
    "Not saying you're a one-trick. The data is saying it. I am just reading it aloud.",
    "{c} main detected. No further tests required.",
    "{p}% {c}. At this point the other characters are just scenery.",
    "Somewhere there is a second character you could learn. Somewhere.",
  ];

  const DUE = [
    "{n} drills are due. They are not going to practise themselves, champ.",
    "{n} drills due. The queue is not a suggestion.",
    "{n} drills are due and quietly judging you.",
    "You have {n} drills due. That is {n} more than zero, mathematically.",
    "{n} due. Spaced repetition waits for no one.",
    "{n} drills would like a word. Preferably today.",
    "Due now: {n}. Due later: also {n}, but worse.",
  ];

  const NOTHING_DUE = [
    "Nothing due. Either you are a machine, or you are avoiding something.",
    "Queue empty. Suspiciously empty.",
    "Nothing due today. Go get bodied online for research purposes.",
    "All caught up. Now do it again tomorrow.",
    "Zero due. The schedule respects you. Briefly.",
  ];

  const NEVER_TOUCHED = [
    "{n} drills you have never touched. They are starting to talk about you.",
    "{n} drills still in the wrapper. Unbox one.",
    "{n} untouched drills. Collecting them is not the same as doing them.",
    "{n} drills have never met you. Introduce yourself.",
    "{n} drills sit unplayed. Bold of you to keep making more.",
  ];

  const COLD_STREAK = [
    "{n} drills have a streak of zero. Bullying is illegal, but they started it.",
    "{n} drills at streak zero. They have humbled you and they know it.",
    "{n} drills currently winning the rivalry {n}-0.",
    "{n} drills sitting at zero. Everyone has a nemesis. You have {n}.",
  ];

  const BEST_STREAK = [
    "Best streak: {n}. Somewhere a training dummy is filing a complaint.",
    "{n} in a row. Do not get cocky. Actually, do, briefly.",
    "Streak of {n}. The muscle memory is memorying.",
    "{n} straight. This is what competence feels like. Enjoy it.",
  ];

  const COWERING = [
    "{b} blocks, {h} hits. You are not fighting, you are commuting.",
    "Blocked {b} times, landed {h}. The corner has offered you a lease.",
    "{b} defensive actions to {h} hits. Even the dummy feels bad for you.",
    "You blocked {b} and hit {h}. That is not neutral, that is hostage footage.",
    "{b} blocks vs {h} hits. The training dummy is filing a missing persons report.",
    "{h} hits, {b} blocks. Somebody bring this man a button.",
  ];

  const ONE_NOTE = [
    "{p}% of your hits are {h}. They stopped guessing about an hour ago.",
    "{p}% {h}. Your mixup is a single-page document.",
    "Everything you land is {h} ({p}%). Predictable is a kind of consistency, I suppose.",
    "{p}% of your damage comes in {h}. Blocking you is a part-time job.",
    "{p}% {h} hits. You have one idea and you are committed to it.",
  ];

  const MIXING_WELL = [
    "{high}/{mid}/{low} high/mid/low. Genuinely hard to guess against. Well done.",
    "Your hits split {high}/{mid}/{low}. That is a real mixup, not a rumour.",
  ];

  const ZONE_LOW = [
    "{p}% of what hits you comes in low. Your ankles have filed a grievance.",
    "{p}% low. Crouching is free and you are leaving it on the table.",
    "{p}% of your damage arrives below the knee. Consider blocking down.",
    "{p}% low hits. Somebody has read your standing guard like a menu.",
  ];

  const ZONE_HIGH = [
    "{p}% of your damage arrives from above. Have you considered... looking up?",
    "{p}% high. The sky is not your friend and it keeps proving it.",
    "{p}% of hits land up top. Anti-airs exist. They are right there.",
    "{p}% high hits. Every jump-in is a question you keep failing to answer.",
  ];

  const ZONE_MID = [
    "{p}% of your damage is mid. Textbook. Unfortunately for you.",
    "{p}% mid. You are being beaten by the most ordinary buttons available.",
    "{p}% mid hits. No mix-up required, apparently.",
  ];

  const LAST_MATCH_DRILL = [
    "Last match: {w} x{n}. \"{d}\" jumps the queue whenever it is due. Coincidence? No.",
    "You ate {w} {n} times last match. \"{d}\" now cuts in line when it comes up.",
    "{w} x{n} last match. \"{d}\" has been promoted. The lab is petty like that.",
    "Your last match filed a complaint: {w} x{n}. \"{d}\" is the remedy, first in line when due.",
  ];

  const LAST_MATCH_NO_DRILL = [
    "Last match: {w} x{n}, and not one drill trains it. Time to write one.",
    "{w} x{n} last match. Your deck has no answer. Yet.",
    "Nothing in your deck fixes {w} ({n} last match). That is a drill-shaped hole.",
  ];

  const MATCH_RECORD = [
    "{w}-{l} across {m} recorded matches. The lab remembers every one.",
    "Recorded record: {w} wins, {l} losses. Every loss is a drill waiting to happen.",
    "{m} matches on the books. {w} of them went your way. Onward.",
  ];

  const BEST_CHAR = [
    "{c} wins {p}% of your matches. Everyone else on your roster is a hobby.",
    "Your {c} is at {p}%. Whatever you do there, try doing it with the others.",
    "{c}: {p}% win rate. Capcom would like a word about balance.",
    "{p}% with {c}. Frame it. Hang it in the lab.",
  ];

  const WORST_CHAR = [
    "{c} wins {p}% of the time. That is not a main, that is a cry for help.",
    "Your {c} sits at {p}%. The lab is open 24 hours. Just saying.",
    "{p}% with {c}. Bold to keep picking them. Respect. Sort of.",
    "{c} at {p}%. Somewhere a {c} main just felt a disturbance.",
  ];

  const NEMESIS = [
    "{o} has a {q}% record against you. Rent is due.",
    "Against {o} you are {w}-{l}. Somewhere, a {o} main is telling this story.",
    "You win {p}% against {o}. They have your number, and they call it often.",
    "{o}: {w}-{l}. Not a matchup. A recurring nightmare with health bars.",
  ];

  const EASY_PREY = [
    "You beat {o} {p}% of the time. They are scared of you. As they should be.",
    "{o}: {w}-{l}. You have them on speed dial.",
    "{p}% against {o}. At this point it is a mentorship.",
  ];

  const MOST_USED = [
    "{p}% of your matches are {c}. Loyalty or fear? We may never know.",
    "{c} again? {p}% of everything you play. They deserve a holiday.",
    "{p}% {c}. The rest of the roster has started a support group.",
  ];

  const TOP_WEAKNESS = [
    "Across every recorded match, {w} is your #1 problem. {n} times. It has a fan club now.",
    "{w}: {n} times in your matches. At this point it is a lifestyle.",
    "Your matches agree on one thing: {w} ({n}). There is a drill for that. Probably.",
    "{n} x {w}. Your opponents have noticed. Trust me.",
  ];

  const TOP_STRENGTH = [
    "Your best habit: {w}, {n} times across your matches. Keep doing that. Specifically that.",
    "{n} x {w}. Whatever else is going wrong, that part works.",
    "{w}, {n} times. Your opponents have it in their nightmares, filed under you.",
  ];

  const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

  const cheese = () =>
    window.i18n ? window.i18n.pool("CHEESE", CHEESE) : CHEESE;

  const say = (name, arr, vars) =>
    window.i18n ? window.i18n.fill(pick(window.i18n.pool(name, arr)), vars)
                : fillLocal(pick(arr), vars);

  const fillLocal = (text, vars) =>
    !vars ? text
          : text.replace(/\{(\w+)\}/g, (whole, key) =>
              Object.prototype.hasOwnProperty.call(vars, key) ? String(vars[key]) : whole);

  async function getJSON(url) {
    try {
      const r = await fetch(url);
      return r.ok ? await r.json() : null;
    } catch { return null; }
  }

  function suggestions(overview, zones, drills, live, matchData, roster) {
    const out = [];
    const n = (v) => (v || 0);
    const words = (k) => String(k || "").replace(/_/g, " ");

    const GENERIC = new Set(["hit", "hit_high", "hit_mid", "hit_low",
      "got_hit", "got_hit_high", "got_hit_mid", "got_hit_low"]);
    const telling = (list, key) => (list || []).find((x) => !GENERIC.has(x[key || "weakness"]));

    const last = ((matchData && matchData.matches) || [])
      .find((m) => m.finished && m.player_side != null);
    if (last) {
      const rec = (last.recommendations || [])[0];
      const gap = telling(last.unaddressed);
      if (rec) {
        out.push(say("LAST_MATCH_DRILL", LAST_MATCH_DRILL,
          { w: words(rec.weakness), n: rec.weakness_count, d: rec.name || rec.drill_id }));
      } else if (gap) {
        out.push(say("LAST_MATCH_NO_DRILL", LAST_MATCH_NO_DRILL,
          { w: words(gap.weakness), n: gap.count }));
      }
    }
    const all = matchData && matchData.overall && matchData.overall.all;
    if (all && n(all.matches) >= 5) {
      out.push(say("MATCH_RECORD", MATCH_RECORD, { w: all.wins, l: all.losses, m: all.matches }));
      const weak = telling(all.weaknesses);
      if (weak && n(weak.count) >= 10)
        out.push(say("TOP_WEAKNESS", TOP_WEAKNESS, { w: words(weak.weakness), n: weak.count }));
      const strong = telling(all.strengths);
      if (strong && n(strong.count) >= 10)
        out.push(say("TOP_STRENGTH", TOP_STRENGTH, { w: words(strong.weakness), n: strong.count }));
    }

    if (roster) {
      const as = roster.as_char || {}, vs = roster.vs_char || {};
      const rate = (r) => (r && r.rate != null ? r.rate : null);
      if (roster.best_as && rate(as[roster.best_as]) != null)
        out.push(say("BEST_CHAR", BEST_CHAR, { c: label(roster.best_as), p: rate(as[roster.best_as]) }));
      if (roster.worst_as && rate(as[roster.worst_as]) != null)
        out.push(say("WORST_CHAR", WORST_CHAR, { c: label(roster.worst_as), p: rate(as[roster.worst_as]) }));
      const nem = roster.worst_vs && vs[roster.worst_vs];
      if (nem && rate(nem) != null)
        out.push(say("NEMESIS", NEMESIS, { o: label(roster.worst_vs), p: rate(nem),
          q: 100 - rate(nem), w: nem.wins, l: nem.losses }));
      const prey = roster.best_vs && vs[roster.best_vs];
      if (prey && rate(prey) != null)
        out.push(say("EASY_PREY", EASY_PREY, { o: label(roster.best_vs), p: rate(prey),
          w: prey.wins, l: prey.losses }));
      const top = Object.entries(as).sort((a, b) => b[1].matches - a[1].matches)[0];
      if (top && n(roster.total) >= 5 && top[1].share >= 0.5)
        out.push(say("MOST_USED", MOST_USED, { c: label(top[0]), p: Math.round(top[1].share * 100) }));
    }

    if (overview) {
      if (n(overview.due_now) > 0) out.push(say("DUE", DUE, { n: overview.due_now }));
      else if (n(overview.total) > 0) out.push(say("NOTHING_DUE", NOTHING_DUE));

    }

    if (Array.isArray(drills) && drills.length) {
      const never = drills.filter((d) => !n(d.total_attempts));
      const cold = drills.filter((d) => n(d.total_attempts) >= 5 && n(d.streak) === 0);
      const best = drills.reduce((a, d) => Math.max(a, n(d.streak)), 0);

      if (cold.length) out.push(say("COLD_STREAK", COLD_STREAK, { n: cold.length }));
      if (best >= 3) out.push(say("BEST_STREAK", BEST_STREAK, { n: best }));
      if (never.length && never.length < drills.length)
        out.push(say("NEVER_TOUCHED", NEVER_TOUCHED, { n: never.length }));

      const byChar = {};
      drills.forEach((d) => {
        if (!d.character_id) return;
        const c = (byChar[d.character_id] ||= { drills: 0, sessions: 0 });
        c.drills++;
        c.sessions += n(d.total_sessions);
      });
      const idle = Object.entries(byChar).filter(([, v]) => v.drills > 0 && v.sessions === 0);
      if (idle.length) out.push(say("ABANDONED", ABANDONED, { c: label(pick(idle)[0]) }));

      const assigned = Object.values(byChar).reduce((a, v) => a + v.drills, 0);
      const top = Object.entries(byChar).sort((a, b) => b[1].drills - a[1].drills)[0];
      if (top && assigned >= 4 && top[1].drills / assigned >= 0.7) {
        const share = Math.round((top[1].drills / assigned) * 100);
        out.push(say("ONE_TRICK", ONE_TRICK, { c: label(top[0]), n: top[1].drills, p: share }));
      }
    }

    if (zones) {

      const asDummy = {};
      Object.values(zones).forEach((e) => {
        Object.entries((e && e.by_dummy) || {}).forEach(([d, v]) => {
          if (d === "unknown") return;
          const c = (v && v.counts) || {};
          asDummy[d] = (asDummy[d] || 0) + n(c.high) + n(c.mid) + n(c.low);
        });
      });
      const worst = Object.entries(asDummy).sort((a, b) => b[1] - a[1])[0];

      if (worst && worst[1] >= 25) out.push(say("PUNCHING_BAG", PUNCHING_BAG, { c: label(worst[0]), n: worst[1] }));

      let high = 0, mid = 0, low = 0;
      Object.values(zones).forEach((e) => {
        const c = (e && e.counts) || {};
        high += n(c.high); mid += n(c.mid); low += n(c.low);
      });
      const total = high + mid + low;
      if (total >= 30) {
        const top = Math.max(high, mid, low);
        const pct = Math.round((top / total) * 100);
        if (top === low) out.push(say("ZONE_LOW", ZONE_LOW, { p: pct }));
        else if (top === high) out.push(say("ZONE_HIGH", ZONE_HIGH, { p: pct }));
        else out.push(say("ZONE_MID", ZONE_MID, { p: pct }));
      }
    }

    const tally = (live && live.criteria_tally) || null;
    if (tally) {
      const hits = n(tally.hit);
      const defence = n(tally.block) + n(tally.parry);
      if (hits + defence >= 20 && defence > hits) {
        out.push(say("COWERING", COWERING, { b: defence, h: hits }));
      }

      const high = n(tally.hit_high), mid = n(tally.hit_mid), low = n(tally.hit_low);
      const heights = high + mid + low;
      if (heights >= 15) {
        const top = Math.max(high, mid, low);
        const share = Math.round((top / heights) * 100);
        if (share >= 80) {
          const name = top === high ? "high" : top === low ? "low" : "mid";
          out.push(say("ONE_NOTE", ONE_NOTE, { h: name, p: share }));
        } else if (share <= 50) {

          out.push(say("MIXING_WELL", MIXING_WELL, { high: high, mid: mid, low: low }));
        }
      }
    }

    return out;
  }

  function shuffled(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function mount() {
    const el = document.getElementById("bd-ticker");
    if (!el) return;

    let lines = shuffled(cheese());
    let i = 0;

    const show = () => {
      if (i >= lines.length) { lines = shuffled(lines); i = 0; }
      el.classList.remove("is-in");

      requestAnimationFrame(() => {
        el.textContent = lines[i];
        el.classList.add("is-in");
        i++;
      });
    };

    show();
    setInterval(show, 11000);

    (async () => {
      const [overview, zones, drills, live, matchData, roster] = await Promise.all([
        getJSON("/api/stats/overview"),
        getJSON("/api/stats/hit_zones"),
        getJSON("/api/drills"),
        getJSON("/api/live"),
        getJSON("/api/matches?limit=5"),
        getJSON("/api/matches/roster"),
      ]);
      const list = Array.isArray(drills) ? drills : (drills && drills.drills) || [];
      const real = suggestions(overview, zones, list, live, matchData, roster);
      if (!real.length) return;
      lines = [...real, ...shuffled(cheese())];
      i = 0;
      show();
    })();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }

})();
