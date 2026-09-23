"""Constants for the HA Sport CZ/SK integration."""
from __future__ import annotations

from typing import Final

DOMAIN: Final = "ha_sport"
NAME: Final = "HA Sport CZ/SK"
VERSION: Final = "1.3.4"

PLATFORMS: Final = ["sensor", "binary_sensor", "calendar", "switch", "button"]

# --- Data source -----------------------------------------------------------
DEFAULT_BASE_URL: Final = "https://www.sofascore.com/api/v1"
FALLBACK_BASE_URLS: Final = (
    "https://api.sofascore.com/api/v1",
    "https://api.sofascore.app/api/v1",
)
IMAGE_BASE_URL: Final = "https://img.sofascore.com/api/v1"
WEB_BASE_URL: Final = "https://www.sofascore.com"

# --- Sports & countries ----------------------------------------------------
SPORT_FOOTBALL: Final = "football"
SPORT_HOCKEY: Final = "ice-hockey"
SPORT_BASKETBALL: Final = "basketball"

SPORTS: Final = {
    SPORT_FOOTBALL: "Fotbal",
    SPORT_HOCKEY: "Hokej",
    SPORT_BASKETBALL: "Basketbal",
}
SPORT_ICONS: Final = {
    SPORT_FOOTBALL: "mdi:soccer",
    SPORT_HOCKEY: "mdi:hockey-puck",
    SPORT_BASKETBALL: "mdi:basketball",
}
SPORT_EMOJI: Final = {
    SPORT_FOOTBALL: "⚽",
    SPORT_HOCKEY: "🏒",
    SPORT_BASKETBALL: "🏀",
}

COUNTRIES: Final = {"CZ": "Česko", "SK": "Slovensko"}

# --- Config / options keys -------------------------------------------------
CONF_SPORTS: Final = "sports"
CONF_COUNTRIES: Final = "countries"
CONF_COMPETITIONS: Final = "competitions"
CONF_FAVORITE_TEAMS: Final = "favorite_teams"
CONF_TEAM_FILTER: Final = "team_filter"
CONF_CITY_FILTER: Final = "city_filter"

CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_LIVE_SCAN_INTERVAL: Final = "live_scan_interval"
CONF_DAYS_AHEAD: Final = "days_ahead"
CONF_DAYS_BACK: Final = "days_back"
CONF_FETCH_ODDS: Final = "fetch_odds"
CONF_FETCH_TV: Final = "fetch_tv"
CONF_BASE_URL: Final = "base_url"
CONF_ODDS_API_KEY: Final = "odds_api_key"
CONF_ODDS_API_INTERVAL: Final = "odds_api_interval"
CONF_ODDS_BOOKMAKERS: Final = "odds_bookmakers"

CONF_NOTIFY_ENABLED: Final = "notify_enabled"
CONF_NOTIFY_SCOPE: Final = "notify_scope"
CONF_NOTIFY_BEFORE: Final = "notify_before"
CONF_NOTIFY_START: Final = "notify_start"
CONF_NOTIFY_SCORE: Final = "notify_score"
CONF_NOTIFY_PERIODS: Final = "notify_periods"
CONF_NOTIFY_END: Final = "notify_end"
CONF_NOTIFY_LIVE_INTERVAL: Final = "notify_live_interval"
CONF_NOTIFY_TARGETS: Final = "notify_targets"
CONF_NOTIFY_PERSISTENT: Final = "notify_persistent"
CONF_NOTIFY_ODDS: Final = "notify_odds"
CONF_ODDS_THRESHOLD: Final = "odds_threshold"
CONF_NOTIFY_LINEUPS: Final = "notify_lineups"
CONF_NOTIFY_CARDS: Final = "notify_cards"
CONF_QUIET_START: Final = "quiet_start"
CONF_QUIET_END: Final = "quiet_end"

NOTIFY_SCOPE_FAVORITES: Final = "favorites"
NOTIFY_SCOPE_FOLLOWED: Final = "followed"
NOTIFY_SCOPE_ALL: Final = "all"

DEFAULT_SCAN_INTERVAL: Final = 15  # minutes
DEFAULT_LIVE_SCAN_INTERVAL: Final = 60  # seconds
DEFAULT_DAYS_AHEAD: Final = 14
DEFAULT_DAYS_BACK: Final = 7
DEFAULT_NOTIFY_BEFORE: Final = ["60", "15"]
DEFAULT_NOTIFY_LIVE_INTERVAL: Final = 0  # minutes, 0 = off
DEFAULT_ODDS_THRESHOLD: Final = 10  # % change of the odd on my team
DEFAULT_ODDS_API_INTERVAL: Final = 6  # hours (The Odds API free quota)
DEFAULT_ODDS_BOOKMAKERS: Final = 4  # extra bookmakers asked for favorite matches

NOTIFY_BEFORE_CHOICES: Final = ["5", "10", "15", "30", "60", "120", "180", "1440"]

# How long the "heavy" data (seasons, standings, brackets, team details) is cached
HEAVY_REFRESH_MINUTES: Final = 60
ODDS_CACHE_MINUTES: Final = 30
TV_CACHE_MINUTES: Final = 360
TEAM_CACHE_HOURS: Final = 24
# Switch the coordinator to the fast interval this long before a followed kick-off
PRE_LIVE_WINDOW_MINUTES: Final = 20

# --- Event / status -------------------------------------------------------
STATUS_NOT_STARTED: Final = "notstarted"
STATUS_LIVE: Final = "inprogress"
STATUS_FINISHED: Final = "finished"
STATUS_POSTPONED: Final = "postponed"
STATUS_CANCELED: Final = "canceled"

EVENT_NOTIFICATION: Final = f"{DOMAIN}_notification"
EVENT_MATCH_UPDATE: Final = f"{DOMAIN}_match_update"
EVENT_ODDS_CHANGE: Final = f"{DOMAIN}_odds_change"
SIGNAL_UPDATE: Final = f"{DOMAIN}_update"

STORAGE_KEY: Final = f"{DOMAIN}.state"
STORAGE_VERSION: Final = 1

LOGO_URL: Final = f"/api/{DOMAIN}/logo"

ATTR_EVENT_ID: Final = "event_id"
ATTR_TEAM_ID: Final = "team_id"
ATTR_QUERY: Final = "query"
