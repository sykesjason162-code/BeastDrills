function titleCase(id) {
  return String(id || "")
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

const CHARACTER_LABELS = {
  jp: "JP",
  chun_li: "Chun-Li",
  dee_jay: "Dee Jay",
  m_bison: "M. Bison",
  c_viper: "C. Viper",
  aki: "A.K.I.",
  honda: "E. Honda",
};

function characterLabel(id) {
  if (!id) return "?";

  const named = window.i18n && window.i18n.name && window.i18n.name(id);
  return named || CHARACTER_LABELS[id] || titleCase(id);
}

const BUCKET_LABELS = {
  new: "New",
  learning: "Learning",
  review_young: "Review",
  review_mature: "Review (mature)",
};

function bucketLabel(bucket) {
  return BUCKET_LABELS[bucket] || titleCase(bucket);
}

const CHARACTER_ROSTER = [
  "ryu", "luke", "jamie", "chun_li", "guile", "kimberly", "juri", "ken",
  "blanka", "dhalsim", "honda", "dee_jay", "manon", "marisa", "jp", "zangief",
  "lily", "cammy", "rashid", "aki", "ed", "akuma", "m_bison", "terry",
  "mai", "elena", "sagat", "c_viper", "alex", "ingrid", "yasmine",
];

const COUNTER_LABELS = {

  anti_air: "Anti-aired them",
  throw: "Threw them",
  throw_missed_me: "Their throw missed",
  throw_tech: "Teched a throw",
  counter_hit: "Counter hit",
  punish_counter_hit: "Punish counter",
  block: "Blocked a hit",
  parry: "Parried",
  perfect_parry: "Perfect parry",
  drive_impact: "Drive Impact landed",
  drive_impact_counter: "Countered their Drive Impact",
  drive_impact_vs_di: "Won a Drive Impact clash",
  stuff_dash: "Stuffed their dash",
  stuff_drive_rush: "Stuffed their Drive Rush",
  jump_attack: "Jump-in landed",
  hit_confirm: "Hit confirmed",
  reversal: "Reversal",
  backroll: "Back-rolled",
  blocked_their_string: "Blocked their string",
  hit: "Landed a hit",
  hit_high: "Landed high",
  hit_mid: "Landed mid",
  hit_low: "Landed low",

  whiff: "Whiffed",
  got_hit: "Got hit",
  got_hit_high: "Got hit high",
  got_hit_mid: "Got hit mid",
  got_hit_low: "Got hit low",
  throw_whiff: "My throw whiffed",
  throw_got_teched: "My throw was teched",
  got_drive_impact_countered: "My Drive Impact was countered",
  lost_di_clash: "Lost a Drive Impact clash",
  dash_got_stuffed: "My dash was stuffed",
  drive_rush_got_stuffed: "My Drive Rush was stuffed",
  block_miss: "Failed to block",
  parry_miss: "Failed to parry",
  got_thrown: "Got thrown",
  got_counter_hit: "Took a counter hit",
  got_punish_countered: "Took a punish counter",
  got_blocked: "They blocked me",
  got_parried: "They parried me",
  got_anti_aired: "Got anti-aired",
  got_drive_impacted: "Took a Drive Impact",
  got_jump_attacked: "Took a jump-in",
  got_hit_confirmed: "They hit-confirmed me",
  non_hit_confirm: "My string was blocked",
  parry_whiff: "Parried nothing",
  got_reversaled: "Hit by a reversal",
  got_backrolled: "They back-rolled",
  no_backroll: "Got up without rolling",
};

function counterLabel(id) {
  const english = COUNTER_LABELS[id] || titleCase(id);
  return window.i18n ? window.i18n.T(english) : english;
}
