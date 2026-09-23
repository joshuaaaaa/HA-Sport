/*
 * HA Sport CZ/SK – Lovelace cards
 *
 *   type: custom:ha-sport-card
 *   mode: matches | team | bracket | standings | smart | live
 *
 * Install: copy this file to /config/www/ha-sport-card.js and add the dashboard
 * resource /local/ha-sport-card.js (type: JavaScript module).
 * Requires the HA Sport CZ/SK integration (custom_components/ha_sport).
 *
 * The card talks to the integration through the WebSocket API (ha_sport/*),
 * so it always has the full data (brackets, tables, odds, streams) without
 * bloating entity attributes.
 */
const CARD_VERSION = "1.3.1";
const WS = "ha_sport";

const I18N = {
  cs: {
    timeline: "Průběh", stats: "Statistiky", lineups: "Sestavy", h2h: "Vzájemné zápasy", fans: "Tip fanoušků", bookmakers: "Kurzy sázkových kanceláří", best: "nejlepší", subs: "Náhradníci", detail_loading: "Načítám detail…", opening: "otevírací", wins: "výhry", draws: "remízy", unconfirmed: "předpokládané",
    upcoming: "Nadcházející", live: "Živě", results: "Výsledky", all: "Vše", search: "Hledat tým, soutěž nebo město…",
    no_matches: "Žádné zápasy", loading: "Načítám…", today: "Dnes", tomorrow: "Zítra", yesterday: "Včera",
    watch: "Sledovat", detail: "Detail", odds: "Kurzy", draw: "Remíza", win_prob: "Šance na výhru",
    follow: "Upozornit", following: "Sleduji", no_match_week: "Tento týden bez zápasu", last_result: "Poslední výsledek",
    form: "Forma", position: "Pozice", pts: "b.", table: "Tabulka", bracket: "Pavouk", no_bracket: "Soutěž nemá pavouka (play-off zatím nezačalo).",
    no_table: "Tabulka není k dispozici.", starts_in: "za", home: "doma", away: "venku", this_week: "Tento týden",
    fav_only: "Jen oblíbené", no_favorites: "Nemáte oblíbené týmy – přidejte je v nastavení integrace.", guessed: "odhad dle vysílacích práv",
    team: "Tým", p: "Z", w: "V", d: "R", l: "P", score: "Skóre", not_loaded: "Integrace HA Sport není načtena.", tbd: "?",
    days: ["ne", "po", "út", "st", "čt", "pá", "so"], min: "min", h: "h", d_: "d", free: "zdarma", error: "Chyba zdroje dat",
  },
  sk: {
    timeline: "Priebeh", stats: "Štatistiky", lineups: "Zostavy", h2h: "Vzájomné zápasy", fans: "Tip fanúšikov", bookmakers: "Kurzy stávkových kancelárií", best: "najlepší", subs: "Náhradníci", detail_loading: "Načítavam detail…", opening: "otváracie", wins: "výhry", draws: "remízy", unconfirmed: "predpokladané",
    upcoming: "Nadchádzajúce", live: "Naživo", results: "Výsledky", all: "Všetko", search: "Hľadať tím, súťaž alebo mesto…",
    no_matches: "Žiadne zápasy", loading: "Načítavam…", today: "Dnes", tomorrow: "Zajtra", yesterday: "Včera",
    watch: "Pozerať", detail: "Detail", odds: "Kurzy", draw: "Remíza", win_prob: "Šanca na výhru",
    follow: "Upozorniť", following: "Sledujem", no_match_week: "Tento týždeň bez zápasu", last_result: "Posledný výsledok",
    form: "Forma", position: "Pozícia", pts: "b.", table: "Tabuľka", bracket: "Pavúk", no_bracket: "Súťaž nemá pavúka (play-off ešte nezačalo).",
    no_table: "Tabuľka nie je k dispozícii.", starts_in: "o", home: "doma", away: "vonku", this_week: "Tento týždeň",
    fav_only: "Len obľúbené", no_favorites: "Nemáte obľúbené tímy – pridajte ich v nastaveniach integrácie.", guessed: "odhad podľa vysielacích práv",
    team: "Tím", p: "Z", w: "V", d: "R", l: "P", score: "Skóre", not_loaded: "Integrácia HA Sport nie je načítaná.", tbd: "?",
    days: ["ne", "po", "ut", "st", "št", "pi", "so"], min: "min", h: "h", d_: "d", free: "zadarmo", error: "Chyba zdroja dát",
  },
  en: {
    timeline: "Timeline", stats: "Statistics", lineups: "Lineups", h2h: "Head to head", fans: "Fans' tip", bookmakers: "Bookmakers' odds", best: "best", subs: "Substitutes", detail_loading: "Loading detail…", opening: "opening", wins: "wins", draws: "draws", unconfirmed: "expected",
    upcoming: "Upcoming", live: "Live", results: "Results", all: "All", search: "Search team, competition or city…",
    no_matches: "No matches", loading: "Loading…", today: "Today", tomorrow: "Tomorrow", yesterday: "Yesterday",
    watch: "Watch", detail: "Details", odds: "Odds", draw: "Draw", win_prob: "Win chance",
    follow: "Notify me", following: "Following", no_match_week: "No match this week", last_result: "Last result",
    form: "Form", position: "Position", pts: "pts", table: "Table", bracket: "Bracket", no_bracket: "No bracket for this competition yet.",
    no_table: "No table available.", starts_in: "in", home: "home", away: "away", this_week: "This week",
    fav_only: "Favorites only", no_favorites: "No favorite teams – add them in the integration options.", guessed: "guessed from broadcast rights",
    team: "Team", p: "P", w: "W", d: "D", l: "L", score: "Score", not_loaded: "HA Sport integration is not loaded.", tbd: "TBD",
    days: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], min: "min", h: "h", d_: "d", free: "free", error: "Data source error",
  },
};

const SPORT_EMOJI = { football: "⚽", "ice-hockey": "🏒", basketball: "🏀" };

const norm = (v) =>
  String(v ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/\s+/g, " ").trim();

// Accepts a numeric id or a (part of a) name: "Chance Liga", "extraliga", "Sparta"
const resolveId = (value, items) => {
  if (value === undefined || value === null || value === "") return null;
  const raw = String(value).trim();
  if (/^-?\d+$/.test(raw)) return Number(raw);
  const byId = items.find((i) => String(i.id) === raw); // e.g. "szlh-819"
  if (byId) return byId.id;
  const q = norm(value);
  const exact = items.find((i) => norm(i.name) === q);
  const hit = exact || items.find((i) => norm(i.name).includes(q));
  return hit ? hit.id : undefined; // undefined = not found
};

const esc = (v) =>
  v === null || v === undefined
    ? ""
    : String(v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const STYLE = `
  :host { display:block; }
  ha-card { overflow:hidden; }
  .hdr { display:flex; align-items:center; gap:8px; padding:12px 16px 4px; }
  .hdr .title { font-size:1.15em; font-weight:500; flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .hdr img { width:28px; height:28px; object-fit:contain; }
  .badge-live { background:var(--error-color,#db4437); color:#fff; border-radius:10px; padding:1px 8px; font-size:.75em; font-weight:600; animation:pulse 1.6s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.55} }
  .controls { display:flex; flex-wrap:wrap; gap:6px; padding:6px 16px; align-items:center; }
  .tabs { display:flex; gap:4px; flex-wrap:wrap; }
  .tab, .chip { border:1px solid var(--divider-color); background:transparent; color:var(--primary-text-color); border-radius:16px; padding:3px 10px; cursor:pointer; font-size:.85em; font-family:inherit; }
  .tab.active, .chip.active { background:var(--primary-color); border-color:var(--primary-color); color:var(--text-primary-color,#fff); }
  .search { flex:1 1 180px; min-width:140px; padding:6px 10px; border-radius:16px; border:1px solid var(--divider-color); background:var(--secondary-background-color); color:var(--primary-text-color); font-family:inherit; font-size:.9em; }
  .body { padding:4px 0 12px; }
  .day { padding:8px 16px 2px; font-size:.78em; font-weight:600; text-transform:uppercase; letter-spacing:.04em; color:var(--secondary-text-color); }
  .row { display:grid; grid-template-columns: 52px 1fr auto; gap:8px; align-items:center; padding:6px 16px; cursor:pointer; border-left:3px solid transparent; }
  .row:hover { background:var(--secondary-background-color); }
  .row.fav { border-left-color:var(--accent-color,#ff9800); }
  .row .time { font-size:.85em; color:var(--secondary-text-color); text-align:center; line-height:1.2; }
  .row .time.live { color:var(--error-color,#db4437); font-weight:600; }
  .teams { display:flex; flex-direction:column; gap:3px; min-width:0; }
  .t { display:flex; align-items:center; gap:6px; min-width:0; }
  .t img { width:20px; height:20px; object-fit:contain; flex:none; }
  .t .n { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .t.win .n { font-weight:600; }
  .t.fav .n { color:var(--primary-color); }
  .right { display:flex; align-items:center; gap:8px; }
  .scores { display:flex; flex-direction:column; gap:3px; text-align:right; font-weight:600; min-width:18px; }
  .scores.live { color:var(--error-color,#db4437); }
  .odds-mini { display:flex; gap:3px; }
  .odds-mini span { font-size:.75em; padding:2px 5px; border-radius:6px; background:var(--secondary-background-color); color:var(--primary-text-color); min-width:30px; text-align:center; }
  .odds-mini span.fav { background:var(--primary-color); color:var(--text-primary-color,#fff); }
  .icon-btn { background:none; border:none; cursor:pointer; color:var(--secondary-text-color); padding:2px; display:flex; }
  .icon-btn.on { color:var(--accent-color,#ff9800); }
  .icon-btn ha-icon { --mdc-icon-size:20px; }
  .detail { padding:4px 16px 10px 76px; font-size:.85em; color:var(--secondary-text-color); display:flex; flex-direction:column; gap:6px; background:var(--secondary-background-color); }
  .links { display:flex; flex-wrap:wrap; gap:6px; }
  a.btn { display:inline-flex; align-items:center; gap:4px; text-decoration:none; background:var(--primary-color); color:var(--text-primary-color,#fff); border-radius:14px; padding:3px 10px; font-size:.85em; }
  a.btn.sec { background:transparent; color:var(--primary-color); border:1px solid var(--primary-color); }
  a.btn ha-icon { --mdc-icon-size:16px; }
  .empty { padding:24px 16px; text-align:center; color:var(--secondary-text-color); }
  .err { padding:4px 16px; color:var(--error-color); font-size:.8em; }
  /* match detail (Livesport-like) */
  .xd { display:flex; flex-direction:column; gap:10px; margin-top:4px; color:var(--primary-text-color); }
  .xd h5 { margin:0 0 4px; font-size:.75em; text-transform:uppercase; letter-spacing:.05em; color:var(--secondary-text-color); }
  .tl { display:flex; flex-direction:column; gap:2px; }
  .tl .it { display:grid; grid-template-columns:1fr 44px 1fr; align-items:center; gap:6px; }
  .tl .it .m { text-align:center; font-size:.8em; color:var(--secondary-text-color); }
  .tl .it .h { text-align:right; } .tl .it .a { text-align:left; }
  .tl .per { text-align:center; font-size:.75em; color:var(--secondary-text-color); border-top:1px dashed var(--divider-color); padding-top:2px; }
  .st { display:grid; grid-template-columns:44px 1fr 44px; gap:6px; align-items:center; font-size:.85em; }
  .st .nm { grid-column:1 / 4; text-align:center; font-size:.8em; color:var(--secondary-text-color); margin-top:4px; }
  .st .v { text-align:center; font-weight:600; }
  .sbar { display:flex; height:6px; border-radius:3px; overflow:hidden; background:var(--divider-color); grid-column:1 / 4; }
  .sbar div:first-child { background:var(--primary-color); } .sbar div:last-child { background:var(--accent-color,#ff9800); }
  .bm { width:100%; border-collapse:collapse; font-size:.85em; }
  .bm td, .bm th { padding:3px 4px; text-align:center; border-top:1px solid var(--divider-color); }
  .bm td:first-child, .bm th:first-child { text-align:left; }
  .bm .best { font-weight:700; color:var(--success-color,#43a047); }
  .lu { display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:.85em; }
  .lu ol { margin:2px 0; padding-left:18px; }
  .chipline { display:flex; gap:6px; flex-wrap:wrap; font-size:.85em; }
  .chipline span { background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:10px; padding:1px 8px; }
  /* team card */
  .match { padding:8px 16px 4px; }
  .meta { text-align:center; font-size:.85em; color:var(--secondary-text-color); }
  .vs { display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:8px; padding:10px 0; }
  .side { display:flex; flex-direction:column; align-items:center; gap:6px; text-align:center; min-width:0; }
  .side img { width:64px; height:64px; object-fit:contain; }
  .side .n { font-weight:500; line-height:1.2; }
  .side.me .n { color:var(--primary-color); }
  .center { text-align:center; }
  .center .big { font-size:2em; font-weight:700; letter-spacing:.04em; }
  .center .big.live { color:var(--error-color,#db4437); }
  .center .when { font-size:1.05em; font-weight:500; }
  .center .cd { font-size:.85em; color:var(--secondary-text-color); }
  .odds { display:grid; grid-template-columns:repeat(3,1fr); gap:6px; margin:8px 0; }
  .odd { border:1px solid var(--divider-color); border-radius:10px; padding:6px; text-align:center; }
  .odd.me { border-color:var(--primary-color); background:rgba(var(--rgb-primary-color,3,169,244),.12); }
  .odd .k { font-size:.75em; color:var(--secondary-text-color); }
  .odd .v { font-size:1.2em; font-weight:600; }
  .odd .pr { font-size:.7em; color:var(--secondary-text-color); }
  .trend-up { color:var(--success-color,#43a047); } .trend-down { color:var(--error-color,#db4437); }
  .probbar { display:flex; height:6px; border-radius:3px; overflow:hidden; margin:4px 0 8px; }
  .probbar div:nth-child(1){ background:var(--primary-color);} .probbar div:nth-child(2){ background:var(--disabled-text-color,#999);} .probbar div:nth-child(3){ background:var(--accent-color,#ff9800);}
  .foot { display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; padding:4px 16px 12px; font-size:.85em; }
  .formchips { display:flex; gap:3px; }
  .fc { width:20px; height:20px; border-radius:4px; color:#fff; display:flex; align-items:center; justify-content:center; font-size:.7em; font-weight:700; }
  .fc.W { background:var(--success-color,#43a047); } .fc.D { background:var(--warning-color,#fb8c00); } .fc.L { background:var(--error-color,#db4437); }
  .sep { border-top:1px solid var(--divider-color); margin:4px 16px; }
  .mini-list .row { grid-template-columns:52px 1fr auto; }
  /* bracket */
  .bracket-wrap { overflow-x:auto; padding:8px 12px 12px; }
  .bracket { display:flex; gap:22px; min-width:min-content; }
  .round { display:flex; flex-direction:column; min-width:170px; }
  .round h4 { margin:0 0 6px; font-size:.78em; text-transform:uppercase; color:var(--secondary-text-color); text-align:center; letter-spacing:.04em; }
  .round .blocks { display:flex; flex-direction:column; justify-content:space-around; flex:1; gap:10px; }
  .blk { border:1px solid var(--divider-color); border-radius:8px; overflow:hidden; background:var(--card-background-color); position:relative; font-size:.85em; }
  .blk.live { border-color:var(--error-color,#db4437); }
  .blk.fav { box-shadow:0 0 0 2px var(--accent-color,#ff9800) inset; }
  .round:not(:last-child) .blk::after { content:""; position:absolute; right:-23px; top:50%; width:22px; border-top:1px solid var(--divider-color); }
  .bp { display:flex; align-items:center; gap:6px; padding:4px 8px; }
  .bp + .bp { border-top:1px solid var(--divider-color); }
  .bp img { width:18px; height:18px; object-fit:contain; }
  .bp .n { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .bp.win { font-weight:600; }
  .bp.lose { opacity:.6; }
  .bp .s { font-weight:600; min-width:14px; text-align:right; }
  .bdate { font-size:.7em; color:var(--secondary-text-color); padding:2px 8px; border-top:1px dashed var(--divider-color); }
  /* standings */
  table { width:100%; border-collapse:collapse; font-size:.88em; }
  th { font-weight:500; color:var(--secondary-text-color); text-align:center; padding:4px 3px; font-size:.85em; }
  td { padding:5px 3px; text-align:center; border-top:1px solid var(--divider-color); }
  td.tm { text-align:left; } td.tm div { display:flex; align-items:center; gap:6px; }
  td.tm img { width:18px; height:18px; object-fit:contain; }
  td.pos { width:26px; font-weight:600; position:relative; }
  td.pos span { display:inline-block; min-width:20px; border-radius:4px; padding:1px 0; }
  tr.fav td { background:rgba(var(--rgb-primary-color,3,169,244),.1); font-weight:600; }
  td.pts { font-weight:700; }
  .tbl-wrap { padding:0 12px 12px; overflow-x:auto; }
  .narrow .hide-narrow { display:none; }
`;

class HaSportCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._state = { tab: null, sport: null, query: "", favOnly: false, expanded: null, treeIdx: 0, tableIdx: 0 };
    this._data = null;
    this._loading = false;
    this._timer = null;
    this._tick = null;
  }

  static getConfigElement() {
    return document.createElement("ha-sport-card-editor");
  }

  static getStubConfig() {
    return { mode: "matches", show_filter: true };
  }

  setConfig(config) {
    if (!config) throw new Error("Invalid configuration");
    this._config = { mode: "matches", refresh: 60, ...config };
    this._state.tab = this._config.tab || "upcoming";
    this._state.favOnly = !!this._config.favorites_only;
    this._built = false;
    if (this._hass) this._load(true);
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._load(true);
  }

  connectedCallback() {
    this._timer = setInterval(() => this._load(), (this._config?.refresh || 60) * 1000);
    this._tick = setInterval(() => this._updateCountdowns(), 30000);
    if (this._hass && this._config) this._load();
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    clearInterval(this._tick);
  }

  getCardSize() {
    return { team: 5, bracket: 6, standings: 8, smart: 5 }[this._config?.mode] || 6;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6, rows: "auto" };
  }

  get t() {
    const lang = (this._hass?.locale?.language || this._hass?.language || "cs").slice(0, 2);
    return I18N[lang] || I18N.cs;
  }

  _ws(msg) {
    return this._hass.callWS({ ...msg, type: `${WS}/${msg.type}` });
  }

  // ---------------------------------------------------------------- data ----
  async _load(force = false) {
    if (!this._hass || !this._config || (this._loading && !force)) return;
    this._loading = true;
    try {
      const c = this._config;
      const mode = c.mode;
      const data = { overview: await this._ws({ type: "overview" }) };
      this._resolveIds(data.overview);
      if (mode === "matches" || mode === "live") {
        data.matches = (await this._ws(this._matchQuery())).matches;
      } else if (mode === "team" || mode === "smart") {
        const ids = this._tid ? [this._tid] : (data.overview.favorites || []).map((f) => f.id);
        data.teams = await Promise.all(ids.slice(0, c.max_teams || 6).map((id) => this._ws({ type: "team", team_id: Number(id) })));
        if (mode === "smart") {
          const days = c.days || 7;
          const horizon = Date.now() / 1000 + days * 86400;
          data.teams = data.teams.filter(
            (s) => s.next && (s.next.status === "inprogress" || (s.next.timestamp && s.next.timestamp <= horizon))
          );
          if (!data.teams.length && this._cid) {
            data.competition = await this._ws({ type: "competition", competition_id: String(this._cid) });
          }
        }
      } else if ((mode === "bracket" || mode === "standings") && this._cid) {
        data.competition = await this._ws({ type: "competition", competition_id: String(this._cid) });
      }
      this._data = data;
      this._error = null;
    } catch (e) {
      this._error = e?.message || String(e);
    }
    this._loading = false;
    this._render();
  }

  _resolveIds(overview) {
    const c = this._config;
    const comps = overview?.competitions || [];
    const favs = overview?.favorites || [];
    this._hint = null;
    this._cid = resolveId(c.competition_id ?? c.competition, comps);
    this._tid = resolveId(c.team_id ?? c.team, favs);
    if (this._cid === undefined) {
      this._hint = `Soutěž „${c.competition_id ?? c.competition}“ nenalezena. Dostupné: ${comps.map((x) => `${x.name} (${x.id})`).join(", ") || "žádné"}`;
      this._cid = null;
    }
    if (this._tid === undefined) {
      this._hint = `Tým „${c.team_id ?? c.team}“ není mezi oblíbenými. Oblíbené: ${favs.map((x) => `${x.name} (${x.id})`).join(", ") || "žádné"}`;
      this._tid = null;
    }
    if (!this._cid && !this._hint && ["bracket", "standings"].includes(c.mode)) {
      this._hint = `Vyberte soutěž (competition: název nebo competition_id). Dostupné: ${comps.map((x) => `${x.name} (${x.id})`).join(", ") || "žádné – zkontrolujte integraci HA Sport"}`;
    }
  }

  _matchQuery() {
    const c = this._config;
    const s = this._state;
    const q = { type: "matches", limit: c.limit || 60 };
    const status = c.mode === "live" ? "live" : s.tab;
    q.status = status;
    if (status === "upcoming") q.days_ahead = c.days || 14;
    if (status === "results") q.days_back = c.days_back || 7;
    const sport = c.sport || s.sport;
    if (sport) q.sport = sport;
    if (this._cid) q.competition_id = this._cid;
    if (this._tid) q.team_id = this._tid;
    if (s.query) q.query = s.query;
    if (c.city) q.city = c.city;
    if (s.favOnly) q.favorites_only = true;
    return q;
  }

  async _reloadMatches() {
    try {
      this._data.matches = (await this._ws(this._matchQuery())).matches;
    } catch (e) {
      this._error = e?.message || String(e);
    }
    this._renderBody();
  }

  // -------------------------------------------------------------- format ----
  _date(iso) {
    return iso ? new Date(iso) : null;
  }

  _dayLabel(d) {
    const t = this.t;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const day = new Date(d);
    day.setHours(0, 0, 0, 0);
    const diff = Math.round((day - today) / 86400000);
    const base = `${t.days[d.getDay()]} ${d.getDate()}. ${d.getMonth() + 1}.`;
    if (diff === 0) return `${t.today} · ${base}`;
    if (diff === 1) return `${t.tomorrow} · ${base}`;
    if (diff === -1) return `${t.yesterday} · ${base}`;
    return base;
  }

  _time(d) {
    return d.toLocaleTimeString(this._hass?.locale?.language || "cs", { hour: "2-digit", minute: "2-digit" });
  }

  _evTime(ev, d) {
    // SZĽH youth leagues sometimes publish only the day, not the time
    return ev && ev.time_known === false ? "—" : this._time(d);
  }

  _countdown(ts) {
    const t = this.t;
    let s = Math.max(0, ts - Date.now() / 1000);
    const d = Math.floor(s / 86400);
    s -= d * 86400;
    const h = Math.floor(s / 3600);
    const m = Math.floor((s - h * 3600) / 60);
    if (d > 0) return `${t.starts_in} ${d} ${t.d_} ${h} ${t.h}`;
    if (h > 0) return `${t.starts_in} ${h} ${t.h} ${m} ${t.min}`;
    return `${t.starts_in} ${m} ${t.min}`;
  }

  _updateCountdowns() {
    this.shadowRoot.querySelectorAll("[data-cd]").forEach((el) => {
      el.textContent = this._countdown(Number(el.dataset.cd));
    });
  }

  _isFav(id) {
    return (this._data?.overview?.favorites || []).some((f) => Number(f.id) === Number(id));
  }

  _img(src, cls = "") {
    return src ? `<img class="${cls}" src="${esc(src)}" loading="lazy" onerror="this.style.visibility='hidden'">` : "";
  }

  _streamLinks(ev, withDetail = true) {
    const t = this.t;
    const links = (ev.streams || [])
      .map(
        (s) =>
          `<a class="btn" href="${esc(s.url)}" target="_blank" rel="noopener" title="${s.guessed ? esc(t.guessed) : ""}">
             <ha-icon icon="mdi:television-play"></ha-icon>${esc(s.platform)}${s.free ? ` · ${t.free}` : ""}${s.guessed ? " *" : ""}</a>`
      )
      .join("");
    const det = withDetail && ev.url ? `<a class="btn sec" href="${esc(ev.url)}" target="_blank" rel="noopener"><ha-icon icon="mdi:open-in-new"></ha-icon>${t.detail}</a>` : "";
    return `<div class="links">${links}${det}</div>`;
  }

  _bell(ev) {
    if (ev.status === "finished") return "";
    const on = ev.followed;
    return `<button class="icon-btn ${on ? "on" : ""}" data-action="follow" data-id="${ev.id}" data-follow="${on ? 0 : 1}" title="${on ? this.t.following : this.t.follow}">
      <ha-icon icon="${on ? "mdi:bell-ring" : "mdi:bell-outline"}"></ha-icon></button>`;
  }

  _oddsBlock(ev, teamId) {
    const t = this.t;
    const o = ev.odds;
    if (!o) return "";
    const home = ev.home.id === Number(teamId);
    const mine = teamId ? (home ? "1" : "2") : null;
    const cell = (k, label) => {
      if (!o[k]) return `<div class="odd"><div class="k">${label}</div><div class="v">–</div></div>`;
      const trend = o[`${k}_trend`] ? `<span class="trend-${o[`${k}_trend`]}">${o[`${k}_trend`] === "up" ? "▲" : "▼"}</span>` : "";
      const pr = o.probability?.[k] !== undefined ? `<div class="pr">${o.probability[k]} %</div>` : "";
      return `<div class="odd ${mine === k ? "me" : ""}"><div class="k">${label}</div><div class="v">${o[k].toFixed(2)} ${trend}</div>${pr}</div>`;
    };
    const hasX = !!o.X;
    const p = o.probability || {};
    const bar = p["1"] !== undefined
      ? `<div class="probbar"><div style="width:${p["1"] || 0}%"></div><div style="width:${p.X || 0}%"></div><div style="width:${p["2"] || 0}%"></div></div>`
      : "";
    return `<div class="odds" style="${hasX ? "" : "grid-template-columns:1fr 1fr"}">
      ${cell("1", esc(ev.home.short || ev.home.name))}${hasX ? cell("X", t.draw) : ""}${cell("2", esc(ev.away.short || ev.away.name))}
    </div>${bar}`;
  }

  // -------------------------------------------------------------- render ----
  _render() {
    const c = this._config;
    if (!c) return;
    if (!this._built) {
      this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card><div id="hdr"></div><div id="ctl"></div><div id="err"></div><div class="body" id="body"></div></ha-card>`;
      this.shadowRoot.addEventListener("click", (e) => this._onClick(e));
      this.shadowRoot.addEventListener("input", (e) => this._onInput(e));
      this._built = true;
      this._ctlBuilt = false;
    }
    this._renderHeader();
    this._renderControls();
    this._renderBody();
  }

  _title() {
    const c = this._config;
    if (c.title) return c.title;
    const comp = this._data?.competition || (this._data?.overview?.competitions || []).find((x) => String(x.id) === String(this._cid));
    const t = this.t;
    switch (c.mode) {
      case "bracket": return comp ? `${t.bracket} · ${comp.name}` : t.bracket;
      case "standings": return comp ? comp.name : t.table;
      case "team": return "";
      case "smart": return "";
      case "live": return `${t.live}`;
      default: return comp ? comp.name : "Sport";
    }
  }

  _renderHeader() {
    const el = this.shadowRoot.getElementById("hdr");
    const title = this._title();
    const live = this._data?.overview?.live_count || 0;
    const comp = this._data?.competition;
    if (!title && !(this._config.mode === "matches" && live)) {
      el.innerHTML = "";
      return;
    }
    el.innerHTML = `<div class="hdr">${comp ? this._img(comp.logo) : ""}<div class="title">${esc(title)}</div>
      ${live && ["matches", "live"].includes(this._config.mode) ? `<span class="badge-live">${this.t.live} ${live}</span>` : ""}</div>`;
  }

  _renderControls() {
    const el = this.shadowRoot.getElementById("ctl");
    const c = this._config;
    const t = this.t;
    if (c.mode !== "matches") {
      el.innerHTML = "";
      this._ctlBuilt = false;
      return;
    }
    const s = this._state;
    const tabs = ["upcoming", "live", "results"]
      .map((k) => `<button class="tab ${s.tab === k ? "active" : ""}" data-action="tab" data-v="${k}">${t[k]}</button>`)
      .join("");
    const sports = c.sport
      ? ""
      : `<div class="tabs">${[["", t.all], ...Object.entries(SPORT_EMOJI)]
          .map(([k, v]) => `<button class="chip ${(s.sport || "") === k ? "active" : ""}" data-action="sport" data-v="${k}">${v}</button>`)
          .join("")}</div>`;
    const fav = `<button class="chip ${s.favOnly ? "active" : ""}" data-action="fav" title="${t.fav_only}">★</button>`;
    if (!this._ctlBuilt) {
      el.innerHTML = `<div class="controls"><div class="tabs" id="tabs"></div><div id="sports"></div></div>
        ${c.show_filter === false ? "" : `<div class="controls"><input class="search" id="q" type="search" placeholder="${esc(t.search)}" value="${esc(s.query)}"><span id="fav"></span></div>`}`;
      this._ctlBuilt = true;
    }
    el.querySelector("#tabs").innerHTML = tabs;
    el.querySelector("#sports").innerHTML = sports;
    const favEl = el.querySelector("#fav");
    if (favEl) favEl.innerHTML = fav;
  }

  _renderBody() {
    const el = this.shadowRoot.getElementById("body");
    const err = this.shadowRoot.getElementById("err");
    const t = this.t;
    const msg = this._error ? (this._error.includes("unknown_command") ? t.not_loaded : this._error) : this._hint;
    err.innerHTML = msg ? `<div class="err">${esc(msg)}</div>` : "";
    if (!this._data) {
      el.innerHTML = `<div class="empty">${t.loading}</div>`;
      return;
    }
    const mode = this._config.mode;
    if (mode === "matches" || mode === "live") el.innerHTML = this._matchesHtml(this._data.matches || []);
    else if (mode === "team") el.innerHTML = this._teamsHtml(this._data.teams || []);
    else if (mode === "bracket") el.innerHTML = this._bracketHtml(this._data.competition);
    else if (mode === "standings") el.innerHTML = this._standingsHtml(this._data.competition);
    else if (mode === "smart") {
      if ((this._data.teams || []).length) el.innerHTML = this._teamsHtml(this._data.teams);
      else if (this._data.competition) {
        const comp = this._data.competition;
        el.innerHTML = `<div class="hdr">${this._img(comp.logo)}<div class="title">${esc(comp.name)}</div></div>` +
          (comp.has_bracket ? this._bracketHtml(comp) : this._standingsHtml(comp));
      } else el.innerHTML = `<div class="empty">${t.no_match_week}</div>`;
    }
    const w = this.shadowRoot.host.getBoundingClientRect().width;
    this.shadowRoot.querySelector("ha-card")?.classList.toggle("narrow", w > 0 && w < 380);
  }

  // matches list
  _matchRow(ev) {
    const t = this.t;
    const d = this._date(ev.start);
    const live = ev.status === "inprogress";
    const done = ev.status === "finished";
    let time;
    if (live) time = `<div class="time live">${esc(ev.minute || ev.status_text || t.live)}</div>`;
    else if (done) time = `<div class="time">${d ? this._evTime(ev, d) : ""}<br><small>${esc(ev.status_text || "")}</small></div>`;
    else if (ev.status !== "notstarted") time = `<div class="time">${esc(ev.status_text)}</div>`;
    else time = `<div class="time">${d ? this._evTime(ev, d) : ""}</div>`;
    const favH = this._isFav(ev.home.id), favA = this._isFav(ev.away.id);
    const team = (tm, side) => {
      const win = done && ((ev.winner === 1 && side === "h") || (ev.winner === 2 && side === "a"));
      const fav = side === "h" ? favH : favA;
      return `<div class="t ${win ? "win" : ""} ${fav ? "fav" : ""}">${this._img(tm.logo)}<span class="n">${esc(tm.name)}</span></div>`;
    };
    let right = "";
    if (live || done) {
      right = `<div class="scores ${live ? "live" : ""}"><span>${ev.home.score ?? ""}</span><span>${ev.away.score ?? ""}</span></div>`;
    } else if (ev.odds && this._config.show_odds !== false) {
      const mine = favH ? "1" : favA ? "2" : null;
      right = `<div class="odds-mini">${["1", "X", "2"].filter((k) => ev.odds[k]).map((k) => `<span class="${mine === k ? "fav" : ""}">${ev.odds[k].toFixed(2)}</span>`).join("")}</div>`;
    }
    const tv = (ev.streams || []).length && !done
      ? `<a class="icon-btn" href="${esc(ev.streams[0].url)}" target="_blank" rel="noopener" title="${esc(ev.streams.map((s) => s.platform).join(", "))}" data-stop="1"><ha-icon icon="mdi:television-play"></ha-icon></a>`
      : "";
    const expanded = this._state.expanded === ev.id;
    const detail = expanded
      ? `<div class="detail">
          <div>${SPORT_EMOJI[ev.sport] || ""} ${esc(ev.competition || "")}${ev.round ? " · " + esc(ev.round) : ""}</div>
          ${ev.venue || ev.city ? `<div>📍 ${esc([ev.venue, ev.city].filter(Boolean).join(", "))}</div>` : ""}
          ${d ? `<div>🗓 ${esc(this._dayLabel(d))} ${this._evTime(ev, d)}${ev.status === "notstarted" && ev.timestamp > Date.now() / 1000 ? ` · <span data-cd="${ev.timestamp}">${this._countdown(ev.timestamp)}</span>` : ev.status === "notstarted" ? ` · ${esc(ev.status_text || "")}` : ""}</div>` : ""}
          ${ev.home.periods?.length ? `<div>${esc(t.score)}: ${ev.home.periods.map((p, i) => `${p}:${ev.away.periods[i] ?? "-"}`).join(", ")}</div>` : ""}
          ${!done ? this._oddsBlock(ev, favH ? ev.home.id : favA ? ev.away.id : null) : ""}
          ${this._streamLinks(ev)}
          ${this._detailHtml(ev)}
        </div>`
      : "";
    return `<div class="row ${favH || favA ? "fav" : ""}" data-action="expand" data-id="${ev.id}">
        ${time}<div class="teams">${team(ev.home, "h")}${team(ev.away, "a")}</div>
        <div class="right">${right}${tv}${this._bell(ev)}</div>
      </div>${detail}`;
  }

  async _loadDetail(id) {
    this._details = this._details || {};
    const cached = this._details[id];
    if (cached && cached.status === "finished") return;
    try {
      this._details[id] = await this._ws({ type: "event_detail", event_id: id });
    } catch (e) {
      this._details[id] = { error: e?.message || String(e) };
    }
    if (this._state.expanded === id) this._renderBody();
  }

  _detailHtml(ev) {
    if (this._config.show_detail === false) return "";
    const t = this.t;
    const det = (this._details || {})[ev.id];
    if (!det) return `<div class="xd"><small>${t.detail_loading}</small></div>`;
    if (det.error) return `<div class="xd"><small>${esc(det.error)}</small></div>`;
    const parts = [];
    // timeline
    const inc = det.incidents || [];
    if (inc.length) {
      const icon = (i) => i.type === "goal" ? "⚽" : i.type === "var" ? "📺" : i.card === "yellow" ? "🟨" : i.card === "second_yellow" ? "🟨🟥" : "🟥";
      const rows = inc.map((i) => {
        if (i.type === "period") return `<div class="per">${esc(i.text)} · ${esc(i.score)}</div>`;
        const txt = `${icon(i)} ${esc(i.player || "")}${i.assist ? ` <small>(${esc(i.assist)})</small>` : ""}${i.detail && i.type !== "var" ? ` <small>${esc(i.detail)}</small>` : ""}${i.type === "goal" ? ` <b>${esc(i.score)}</b>` : ""}`;
        return `<div class="it"><div class="h">${i.is_home ? txt : ""}</div><div class="m">${esc(i.minute || "")}</div><div class="a">${i.is_home ? "" : txt}</div></div>`;
      }).join("");
      parts.push(`<div><h5>${t.timeline}</h5><div class="tl">${rows}</div></div>`);
    }
    // statistics
    const stats = (det.statistics || []).slice(0, this._config.max_stats || 10);
    if (stats.length) {
      const rows = stats.map((x) => {
        const h = Number(x.home_value ?? parseFloat(x.home)) || 0;
        const a = Number(x.away_value ?? parseFloat(x.away)) || 0;
        const tot = h + a || 1;
        return `<div class="nm">${esc(x.name)}</div><div class="v">${esc(x.home)}</div><div></div><div class="v">${esc(x.away)}</div>
          <div class="sbar"><div style="width:${(h / tot) * 100}%"></div><div style="width:${(a / tot) * 100}%"></div></div>`;
      }).join("");
      parts.push(`<div><h5>${t.stats}</h5><div class="st">${rows}</div></div>`);
    }
    // bookmakers
    const o = det.odds || {};
    if ((o.bookmakers || []).length > 1) {
      const keys = ["1", "X", "2"].filter((k) => o.bookmakers.some((b) => b[k]));
      const cell = (b, k) => (b[k] ? `<td class="${o.best?.[k] === b[k] ? "best" : ""}">${b[k].toFixed(2)}</td>` : "<td>–</td>");
      const open = o.opening && Object.keys(o.opening).length
        ? `<tr><td><small>${t.opening}</small></td>${keys.map((k) => `<td><small>${o.opening[k] ? o.opening[k].toFixed(2) : "–"}</small></td>`).join("")}</tr>` : "";
      parts.push(`<div><h5>${t.bookmakers}</h5><table class="bm"><tr><th></th>${keys.map((k) => `<th>${k}</th>`).join("")}</tr>
        ${o.bookmakers.map((b) => `<tr><td>${esc(b.name)}</td>${keys.map((k) => cell(b, k)).join("")}</tr>`).join("")}${open}</table></div>`);
    }
    // h2h + fans
    const chips = [];
    if (det.h2h) chips.push(`<span>${t.h2h}: ${esc(ev.home.short)} ${det.h2h.home_wins} · ${t.draws} ${det.h2h.draws} · ${esc(ev.away.short)} ${det.h2h.away_wins}</span>`);
    if (det.votes) chips.push(`<span>${t.fans}: 1 ${det.votes["1"]} % · X ${det.votes.X} % · 2 ${det.votes["2"]} %</span>`);
    if (chips.length) parts.push(`<div class="chipline">${chips.join("")}</div>`);
    // lineups
    const lu = det.lineups;
    if (lu && (lu.home?.starters || []).length) {
      const col = (side, tm) => `<div><b>${esc(tm.short)}</b>${side.formation ? ` <small>${esc(side.formation)}</small>` : ""}
        <ol>${(side.starters || []).map((p) => `<li>${p.number ? `<small>${esc(p.number)}</small> ` : ""}${esc(p.name)}</li>`).join("")}</ol>
        ${(side.missing || []).length ? `<small>❌ ${side.missing.map(esc).join(", ")}</small>` : ""}</div>`;
      parts.push(`<div><h5>${t.lineups}${lu.confirmed ? "" : ` <small>(${t.unconfirmed})</small>`}</h5><div class="lu">${col(lu.home, ev.home)}${col(lu.away, ev.away)}</div></div>`);
    }
    return parts.length ? `<div class="xd">${parts.join("")}</div>` : "";
  }

  _matchesHtml(matches) {
    const t = this.t;
    if (!matches.length) return `<div class="empty">${t.no_matches}</div>`;
    let html = "";
    let lastDay = null;
    const grouped = this._config.group_by_day !== false;
    for (const ev of matches) {
      const d = this._date(ev.start);
      if (grouped && d) {
        const key = d.toDateString();
        if (key !== lastDay) {
          html += `<div class="day">${esc(this._dayLabel(d))}</div>`;
          lastDay = key;
        }
      }
      html += this._matchRow(ev);
    }
    return html;
  }

  // team card
  _teamsHtml(summaries) {
    const t = this.t;
    if (!summaries.length) return `<div class="empty">${t.no_favorites}</div>`;
    return summaries.map((s, i) => (i ? `<div class="sep"></div>` : "") + this._teamHtml(s)).join("");
  }

  _teamHtml(s) {
    const t = this.t;
    const c = this._config;
    const team = s.team || {};
    const ev = s.next;
    const days = c.days || 7;
    const horizon = Date.now() / 1000 + days * 86400;
    const form = (s.form || []).length
      ? `<div><span>${t.form}: </span><span class="formchips">${s.form.map((f) => `<span class="fc ${f}">${{ W: t.w, D: t.d, L: t.l }[f]}</span>`).join("")}</span></div>`
      : "";
    const pos = s.position ? `<div>${t.position}: <b>${s.position.position}.</b> · ${s.position.points} ${t.pts}${s.position.competition ? ` · ${esc(s.position.competition)}` : ""}</div>` : "";
    const foot = form || pos ? `<div class="foot">${form}${pos}</div>` : "";
    if (!ev || (ev.status === "notstarted" && ev.timestamp > horizon && c.mode === "smart")) {
      const last = s.last;
      return `<div class="match"><div class="vs" style="grid-template-columns:auto 1fr">
          ${this._img(team.logo || `/api/ha_sport/logo/team/${team.id}`, "")}
          <div><div style="font-weight:500">${esc(team.name || "")}</div><div class="meta" style="text-align:left">${t.no_match_week}</div></div></div>
          ${last ? `<div class="meta">${t.last_result}: ${esc(last.home.name)} <b>${last.home.score}:${last.away.score}</b> ${esc(last.away.name)}</div>` : ""}
        </div>${foot}`;
    }
    const meHome = ev.home.id === Number(team.id);
    const live = ev.status === "inprogress";
    const done = ev.status === "finished";
    const d = this._date(ev.start);
    const center = live || done
      ? `<div class="big ${live ? "live" : ""}">${ev.home.score ?? 0}:${ev.away.score ?? 0}</div><div class="cd">${esc(live ? ev.minute || ev.status_text : ev.status_text)}</div>`
      : `<div class="when">${d ? esc(this._dayLabel(d)) : ""}</div><div class="big" style="font-size:1.5em">${d ? this._evTime(ev, d) : ""}</div>
         <div class="cd" data-cd="${ev.timestamp}">${this._countdown(ev.timestamp)}</div>`;
    const side = (tm, me) => `<div class="side ${me ? "me" : ""}">${this._img(tm.logo)}<div class="n">${esc(tm.name)}</div></div>`;
    const others = (s.this_week || []).filter((e) => e.id !== ev.id);
    return `<div class="match">
        <div class="meta">${SPORT_EMOJI[ev.sport] || ""} ${esc(ev.competition || "")}${ev.round ? " · " + esc(ev.round) : ""} · ${meHome ? t.home : t.away}
          ${live ? `<span class="badge-live">${t.live}</span>` : ""}</div>
        <div class="vs">${side(ev.home, meHome)}<div class="center">${center}</div>${side(ev.away, !meHome)}</div>
        ${ev.venue || ev.city ? `<div class="meta">📍 ${esc([ev.venue, ev.city].filter(Boolean).join(", "))}</div>` : ""}
        ${(ev.incidents || []).filter((i) => i.type === "goal").length ? `<div class="meta">⚽ ${ev.incidents.filter((i) => i.type === "goal").map((i) => `${esc(i.player || "?")} ${esc(i.minute || "")}`).join(", ")}</div>` : ""}
        ${!done && c.show_odds !== false ? this._oddsBlock(ev, team.id) : ""}
        ${ev.odds?.best && ev.odds?.bookmakers?.length > 1 ? `<div class="meta">${t.best}: ${esc(ev.odds.best_bookmaker?.[ev.home.id === Number(team.id) ? "1" : "2"] || "")} ${(ev.odds.best[ev.home.id === Number(team.id) ? "1" : "2"] || 0).toFixed(2)}</div>` : ""}
        ${ev.h2h || ev.votes ? `<div class="chipline" style="justify-content:center;margin:4px 0">${ev.h2h ? `<span>${t.h2h}: ${ev.h2h.home_wins}–${ev.h2h.draws}–${ev.h2h.away_wins}</span>` : ""}${ev.votes ? `<span>${t.fans}: 1 ${ev.votes["1"]} % · X ${ev.votes.X} % · 2 ${ev.votes["2"]} %</span>` : ""}</div>` : ""}
        <div style="display:flex;align-items:center;justify-content:space-between;gap:8px">${this._streamLinks(ev)}${this._bell(ev)}</div>
      </div>
      ${others.length ? `<div class="day">${t.this_week}</div><div class="mini-list">${others.map((e) => this._matchRow(e)).join("")}</div>` : ""}
      ${foot}`;
  }

  // bracket
  _bracketHtml(comp) {
    const t = this.t;
    if (!comp) return `<div class="empty">${this._cid ? t.loading : "—"}</div>`;
    const trees = comp.bracket || [];
    if (!trees.length) return `<div class="empty">${t.no_bracket}</div>` + (comp.has_standings ? this._standingsHtml(comp) : "");
    const idx = Math.min(this._state.treeIdx, trees.length - 1);
    const tabs = trees.length > 1
      ? `<div class="controls"><div class="tabs">${trees.map((tr, i) => `<button class="tab ${i === idx ? "active" : ""}" data-action="tree" data-v="${i}">${esc(tr.name || i + 1)}</button>`).join("")}</div></div>`
      : "";
    const favs = new Set((comp.favorites || []).map(Number));
    const tree = trees[idx];
    const rounds = tree.rounds.map((r) => {
      const blocks = r.blocks.map((b) => {
        const parts = b.participants.length ? b.participants : [];
        const scores = [b.home_score, b.away_score];
        const isFav = parts.some((p) => favs.has(Number(p.team_id)));
        const row = (p, i) => {
          if (!p) return `<div class="bp"><span class="n" style="opacity:.5">${t.tbd}</span></div>`;
          const cls = b.finished ? (p.winner ? "win" : "lose") : "";
          return `<div class="bp ${cls}">${this._img(p.logo)}<span class="n">${esc(p.short || p.name)}</span><span class="s">${scores[i] ?? ""}</span></div>`;
        };
        const next = (b.matches || []).find((m) => m.status !== "finished");
        const dateTs = next?.start || b.start;
        const date = dateTs && !b.finished ? `<div class="bdate">${esc(this._dayLabel(new Date(dateTs)))} ${this._time(new Date(dateTs))}${next?.odds ? ` · ${["1", "X", "2"].filter((k) => next.odds[k]).map((k) => next.odds[k].toFixed(2)).join(" / ")}` : ""}</div>` : "";
        return `<div class="blk ${b.live ? "live" : ""} ${isFav ? "fav" : ""}">${row(parts[0], 0)}${row(parts[1], 1)}${date}</div>`;
      }).join("");
      return `<div class="round"><h4>${esc(r.name || "")}</h4><div class="blocks">${blocks}</div></div>`;
    }).join("");
    return `${tabs}<div class="bracket-wrap"><div class="bracket">${rounds}</div></div>`;
  }

  // standings
  _standingsHtml(comp) {
    const t = this.t;
    if (!comp) return `<div class="empty">${this._cid ? t.loading : "—"}</div>`;
    const tables = comp.standings || [];
    if (!tables.length) return `<div class="empty">${t.no_table}</div>`;
    const idx = Math.min(this._state.tableIdx, tables.length - 1);
    const tabs = tables.length > 1
      ? `<div class="controls"><div class="tabs">${tables.map((tb, i) => `<button class="tab ${i === idx ? "active" : ""}" data-action="table" data-v="${i}">${esc(tb.name || i + 1)}</button>`).join("")}</div></div>`
      : "";
    const favs = new Set((comp.favorites || []).map(Number));
    const promoColors = {};
    const palette = ["#43a047", "#1e88e5", "#8e24aa", "#fb8c00", "#e53935", "#00897b"];
    const rows = tables[idx].rows;
    const ppg = rows.some((r) => r.points_per_game !== undefined && r.points_per_game !== null);
    const max = this._config.max_rows || rows.length;
    const body = rows.slice(0, max).map((r) => {
      let color = "";
      if (r.promotion) {
        if (!(r.promotion in promoColors)) promoColors[r.promotion] = palette[Object.keys(promoColors).length % palette.length];
        color = promoColors[r.promotion];
      }
      const hockey = comp.sport === "ice-hockey";
      return `<tr class="${favs.has(Number(r.team_id)) ? "fav" : ""}" title="${esc(r.promotion || "")}">
        <td class="pos"><span style="${color ? `background:${color};color:#fff` : ""}">${r.position}</span></td>
        <td class="tm"><div>${this._img(r.logo)}<span>${esc(this._config.short_names ? r.short : r.team)}</span></div></td>
        <td>${r.played ?? ""}</td><td class="hide-narrow">${r.wins ?? ""}</td>
        ${comp.sport === "basketball" ? "" : `<td class="hide-narrow">${hockey ? (r.ot_wins ?? 0) + "/" + (r.ot_losses ?? 0) : r.draws ?? ""}</td>`}
        <td class="hide-narrow">${r.losses ?? ""}</td>
        <td>${r.scores_for ?? ""}:${r.scores_against ?? ""}</td><td class="pts">${r.points ?? r.percentage ?? ""}</td>${ppg ? `<td class="hide-narrow">${r.points_per_game ?? ""}</td>` : ""}</tr>`;
    }).join("");
    const hockey = comp.sport === "ice-hockey";
    const legend = Object.entries(promoColors)
      .map(([k, v]) => `<span style="display:inline-flex;align-items:center;gap:4px;margin-right:10px"><span style="width:10px;height:10px;border-radius:2px;background:${v}"></span>${esc(k)}</span>`)
      .join("");
    return `${tabs}<div class="tbl-wrap"><table><thead><tr><th>#</th><th style="text-align:left">${t.team}</th><th>${t.p}</th><th class="hide-narrow">${t.w}</th>
      ${comp.sport === "basketball" ? "" : `<th class="hide-narrow">${hockey ? "P/P" : t.d}</th>`}<th class="hide-narrow">${t.l}</th><th>${t.score}</th><th>${t.pts}</th>${ppg ? `<th class="hide-narrow" title="body na zápas">B/Z</th>` : ""}</tr></thead>
      <tbody>${body}</tbody></table>${legend ? `<div style="font-size:.75em;color:var(--secondary-text-color);padding-top:8px">${legend}</div>` : ""}</div>`;
  }

  // ------------------------------------------------------------- events ----
  async _onClick(e) {
    const path = e.composedPath();
    if (path.some((n) => n.dataset?.stop) || path.some((n) => n.tagName === "A")) return;
    const el = path.find((n) => n.dataset && n.dataset.action);
    if (!el) return;
    const a = el.dataset.action;
    const s = this._state;
    if (a === "tab") {
      s.tab = el.dataset.v;
      s.expanded = null;
      this._renderControls();
      await this._reloadMatches();
    } else if (a === "sport") {
      s.sport = el.dataset.v || null;
      this._renderControls();
      await this._reloadMatches();
    } else if (a === "fav") {
      s.favOnly = !s.favOnly;
      this._renderControls();
      await this._reloadMatches();
    } else if (a === "expand") {
      const id = Number(el.dataset.id);
      s.expanded = s.expanded === id ? null : id;
      this._renderBody();
      if (s.expanded && this._config.show_detail !== false) this._loadDetail(id);
    } else if (a === "tree") {
      s.treeIdx = Number(el.dataset.v);
      this._renderBody();
    } else if (a === "table") {
      s.tableIdx = Number(el.dataset.v);
      this._renderBody();
    } else if (a === "follow") {
      e.stopPropagation();
      const follow = el.dataset.follow === "1";
      await this._ws({ type: "follow", event_id: Number(el.dataset.id), follow });
      await this._load(true);
    }
  }

  _onInput(e) {
    if (e.target.id !== "q") return;
    clearTimeout(this._debounce);
    this._debounce = setTimeout(() => {
      this._state.query = e.target.value.trim();
      this._reloadMatches();
    }, 300);
  }
}

// ------------------------------------------------------------------ editor ----
class HaSportCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._overview) {
      this._overview = {};
      hass.callWS({ type: `${WS}/overview` }).then((o) => {
        this._overview = o;
        this._render();
      }).catch(() => {});
    }
    if (this._form) this._form.hass = hass;
  }

  _schema() {
    const o = this._overview || {};
    const comps = (o.competitions || []).map((c) => ({ value: String(c.id), label: `${SPORT_EMOJI[c.sport] || ""} ${c.name}${c.has_bracket ? " 🏆" : ""}` }));
    const teams = (o.favorites || []).map((f) => ({ value: String(f.id), label: `${SPORT_EMOJI[f.sport] || ""} ${f.name}` }));
    const mode = this._config.mode || "matches";
    const schema = [
      {
        name: "mode",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "matches", label: "Zápasy (nadcházející / živě / výsledky + filtr)" },
              { value: "team", label: "Můj tým – příští zápas s kurzem" },
              { value: "smart", label: "Chytrá: kurz na můj tým tento týden, jinak pavouk/tabulka" },
              { value: "bracket", label: "Pavouk soutěže (play-off)" },
              { value: "standings", label: "Tabulka soutěže" },
              { value: "live", label: "Jen živé zápasy" },
            ],
          },
        },
      },
      { name: "title", selector: { text: {} } },
    ];
    if (["matches", "live", "bracket", "standings", "smart"].includes(mode)) {
      schema.push({ name: "competition_id", selector: { select: { mode: "dropdown", options: [{ value: "", label: "—" }, ...comps] } } });
    }
    if (["team", "smart", "matches"].includes(mode)) {
      schema.push({ name: "team_id", selector: { select: { mode: "dropdown", options: [{ value: "", label: mode === "matches" ? "—" : "Všechny oblíbené" }, ...teams] } } });
    }
    if (mode === "matches" || mode === "live") {
      schema.push(
        { name: "sport", selector: { select: { mode: "dropdown", options: [{ value: "", label: "Všechny" }, { value: "football", label: "⚽ Fotbal" }, { value: "ice-hockey", label: "🏒 Hokej" }, { value: "basketball", label: "🏀 Basketbal" }] } } },
        { name: "city", selector: { text: {} } },
        {
          type: "grid",
          name: "",
          schema: [
            { name: "show_filter", selector: { boolean: {} } },
            { name: "favorites_only", selector: { boolean: {} } },
            { name: "show_odds", selector: { boolean: {} } },
            { name: "show_detail", selector: { boolean: {} } },
            { name: "days", selector: { number: { min: 1, max: 60, mode: "box" } } },
            { name: "limit", selector: { number: { min: 5, max: 300, mode: "box" } } },
          ],
        }
      );
    }
    if (mode === "team" || mode === "smart") {
      schema.push({ type: "grid", name: "", schema: [
        { name: "days", selector: { number: { min: 1, max: 60, mode: "box" } } },
        { name: "show_odds", selector: { boolean: {} } },
      ] });
    }
    if (mode === "standings") {
      schema.push({ type: "grid", name: "", schema: [
        { name: "max_rows", selector: { number: { min: 3, max: 40, mode: "box" } } },
        { name: "short_names", selector: { boolean: {} } },
      ] });
    }
    return schema;
  }

  _render() {
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) => ({
        mode: "Režim karty", title: "Nadpis", competition_id: "Soutěž", team_id: "Tým", sport: "Sport", city: "Město (filtr)",
        show_filter: "Zobrazit vyhledávání", favorites_only: "Jen oblíbené", show_odds: "Zobrazit kurzy", show_detail: "Detail zápasu po kliknutí", days: "Dní dopředu",
        limit: "Max. zápasů", max_rows: "Max. řádků", short_names: "Krátké názvy",
      }[s.name] || s.name);
      this._form.addEventListener("value-changed", (ev) => {
        const cfg = { ...ev.detail.value };
        for (const k of Object.keys(cfg)) if (cfg[k] === "" || cfg[k] === undefined) delete cfg[k];
        this._config = cfg;
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: cfg }, bubbles: true, composed: true }));
        this._form.schema = this._schema();
      });
      this.appendChild(this._form);
    }
    if (this._hass) this._form.hass = this._hass;
    this._form.data = { show_filter: true, show_odds: true, show_detail: true, ...this._config };
    this._form.schema = this._schema();
  }
}

// Thin wrappers so each variant shows up in the card picker
const variant = (mode, extra = {}) =>
  class extends HaSportCard {
    static getStubConfig() {
      return { mode, ...extra };
    }
    setConfig(config) {
      super.setConfig({ mode, ...config });
    }
  };

if (!customElements.get("ha-sport-card")) {
  customElements.define("ha-sport-card", HaSportCard);
  customElements.define("ha-sport-card-editor", HaSportCardEditor);
  customElements.define("ha-sport-team-card", variant("team"));
  customElements.define("ha-sport-bracket-card", variant("bracket"));
  customElements.define("ha-sport-standings-card", variant("standings"));
  customElements.define("ha-sport-smart-card", variant("smart"));
}

window.customCards = window.customCards || [];
window.customCards.push(
  { type: "ha-sport-card", name: "HA Sport – zápasy", description: "Nadcházející zápasy, živé výsledky a výsledky fotbalu, hokeje a basketbalu CZ/SK s filtrem, kurzy a odkazy na stream.", preview: true, documentationURL: "https://github.com/joshuaaaaa/HA-Sport" },
  { type: "ha-sport-team-card", name: "HA Sport – můj tým", description: "Příští zápas oblíbeného týmu s kurzem, odpočtem, formou a kde se dívat.", preview: true },
  { type: "ha-sport-smart-card", name: "HA Sport – chytrá karta", description: "Kurz na můj tým, pokud hraje tento týden – jinak pavouk nebo tabulka vybrané soutěže.", preview: true },
  { type: "ha-sport-bracket-card", name: "HA Sport – pavouk", description: "Play-off pavouk vybrané soutěže.", preview: true },
  { type: "ha-sport-standings-card", name: "HA Sport – tabulka", description: "Tabulka soutěže se zvýrazněním oblíbených týmů.", preview: true }
);

console.info(`%c HA-SPORT-CARD %c ${CARD_VERSION} `, "background:#03a9f4;color:#fff;font-weight:700", "background:#444;color:#fff");
