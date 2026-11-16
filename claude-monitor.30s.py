#!/usr/bin/env python3

# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideLastUpdated>true</swiftbar.hideLastUpdated>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>

# Metadata for SwiftBar plugin manager
# <bitbar.title>Claude Code Usage Monitor</bitbar.title>
# <bitbar.version>v2.0.0</bitbar.version>
# <bitbar.author>iiunuii</bitbar.author>
# <bitbar.author.github>iiunuii</bitbar.author.github>
# <bitbar.desc>Real-time Claude Code usage for every account profile: 5-hour and weekly limit %, session cost, burn rate and models.</bitbar.desc>
# <bitbar.dependencies>python3, claude-monitor</bitbar.dependencies>
# <bitbar.abouturl>https://github.com/iiunuii/claude-code-monitor-bar</bitbar.abouturl>
# <swiftbar.schedule>*/30 * * * * *</swiftbar.schedule>

"""
SwiftBar/xbar plugin for Claude Code Usage Monitor.

Shows Claude Code usage for each account profile (the default ~/.claude plus
any CLAUDE_CONFIG_DIR profile such as ~/.claude-personal) in the macOS menu bar.

Limit percentages are the ones Anthropic reports for the account, read from
the usage cache that the oh-my-claudecode HUD keeps in each profile. Session
tokens, cost, burn rate and models come from the local JSONL logs via
claude-monitor.

Configuration (~/.claude-monitor/widget-config.json), all optional:
    {
      "display": ["session_pct", "cost"],
      "profiles": [
        {"dir": "~/.claude", "label": "Work"},
        {"dir": "~/.claude-personal", "label": "Personal"}
      ]
    }
Without "profiles", ~/.claude and every ~/.claude-* directory that holds a
logged-in Claude Code profile are shown, one row per account.
"""

import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


# SwiftBar runs the system Python, which can't see a `uv tool install`
# of claude-monitor.
def _setup_uv_tool_path():
    try:
        import claude_monitor  # noqa: F401
        return
    except ImportError:
        pass

    lib_dir = Path.home() / ".local" / "share" / "uv" / "tools" / "claude-monitor" / "lib"
    if not lib_dir.exists():
        return
    for pydir in sorted(lib_dir.glob("python*/site-packages"), reverse=True):
        if pydir.is_dir():
            sys.path.insert(0, str(pydir))
            return


_setup_uv_tool_path()

# --- Colors (SwiftBar hex) ---
COLOR_GREEN = "#6BDB7B"
COLOR_YELLOW = "#FFD95C"
COLOR_ORANGE = "#FF9F43"
COLOR_RED = "#FF6B6B"
COLOR_GRAY = "#8E8E93"
COLOR_WHITE = "#FFFFFF"
COLOR_DIM = "#A0A0A8"
COLOR_LABEL = "#B0B0B8"

# --- Fonts ---
TITLE_FONT = "SFMono-Regular"
TITLE_SIZE = 12
TITLE_OFFSET = 2
MONO_FONT = "SFMono-Regular"
BODY_SIZE = 12
SMALL_SIZE = 11

HOME = Path.home()
CONFIG_PATH = HOME / ".claude-monitor" / "widget-config.json"
OMC_USAGE_CACHE = Path("plugins") / "oh-my-claudecode" / ".usage-cache-anthropic.json"
STALE_AFTER_SECONDS = 10 * 60

FREEMAIL_DOMAINS = {
    "gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com",
    "icloud.com", "me.com", "yahoo.com", "proton.me", "protonmail.com",
}

DISPLAY_METRICS = (
    ("session_pct", "5h limit %"),
    ("weekly_pct", "Weekly limit %"),
    ("cost", "Session cost ($)"),
    ("msg", "Session messages"),
)
LEGACY_DISPLAY_KEYS = {"token_pct": "session_pct"}
DEFAULT_DISPLAY = ["session_pct", "cost"]


# --- Domain model ---

@dataclass
class Profile:
    config_dir: Path
    label: str
    email: str

    @property
    def tag(self) -> str:
        return self.label[:1].upper()


@dataclass
class LimitWindow:
    pct: Optional[float]
    resets_at: Optional[datetime]


@dataclass
class Limits:
    five_hour: LimitWindow
    weekly: LimitWindow
    fetched_at: datetime

    @property
    def age_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self.fetched_at).total_seconds()

    @property
    def stale(self) -> bool:
        return self.age_seconds > STALE_AFTER_SECONDS


@dataclass
class Session:
    tokens: int
    cost: float
    messages: int
    duration_min: float
    cost_per_hour: float
    ends_at: Optional[datetime]
    model_tokens: Dict[str, int]


@dataclass
class ProfileUsage:
    profile: Profile
    limits: Optional[Limits]
    session: Optional[Session]
    error: Optional[str] = None


# --- Formatting helpers ---

def get_color(pct: float) -> str:
    if pct >= 95:
        return COLOR_RED
    if pct >= 80:
        return COLOR_ORANGE
    if pct >= 50:
        return COLOR_YELLOW
    return COLOR_GREEN


def bar_graph(pct: float, width: int = 10) -> str:
    filled = max(0, min(int(pct / 100 * width), width))
    return "█" * filled + "░" * (width - filled)


def fmt_number(n: int) -> str:
    return f"{n:,}"


def fmt_cost(c: float) -> str:
    return f"${c:.2f}"


def fmt_duration(minutes: float) -> str:
    if minutes < 1:
        return "<1m"
    if minutes < 60:
        return f"{int(minutes)}m"
    return f"{int(minutes // 60)}h {int(minutes % 60)}m"


def fmt_time(dt: datetime) -> str:
    return dt.astimezone().strftime("%-I:%M %p")


def fmt_reset(dt: datetime) -> str:
    local = dt.astimezone()
    if local.date() == datetime.now().astimezone().date():
        return fmt_time(dt)
    return local.strftime("%a %-I:%M %p")


def fmt_age(seconds: float) -> str:
    return fmt_duration(seconds / 60) + " ago"


def parse_iso(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# --- Config ---

def load_config() -> dict:
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
        return config if isinstance(config, dict) else {}
    except (OSError, ValueError):
        return {}


def get_display(config: dict) -> list:
    valid = {k for k, _ in DISPLAY_METRICS}
    raw = config.get("display")
    if isinstance(raw, list):
        keys = []
        for key in raw:
            key = LEGACY_DISPLAY_KEYS.get(key, key)
            if key in valid and key not in keys:
                keys.append(key)
        if keys:
            return keys
    return list(DEFAULT_DISPLAY)


def toggle_display(metric: str) -> None:
    config = load_config()
    current = get_display(config)
    if metric in current:
        current.remove(metric)
    else:
        current.append(metric)
    config["display"] = current or list(DEFAULT_DISPLAY)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


# --- Profiles ---

def _account_email(config_dir: Path) -> Optional[str]:
    # Claude Code keeps the default profile's account file beside the dir, not inside it.
    account_file = HOME / ".claude.json" if config_dir == HOME / ".claude" else config_dir / ".claude.json"
    try:
        with open(account_file) as f:
            email = json.load(f)["oauthAccount"]["emailAddress"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return email.strip() if isinstance(email, str) and email.strip() else None


def _default_label(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain or domain.lower() in FREEMAIL_DOMAINS:
        return "Personal"
    return domain.split(".")[0].capitalize()


def discover_profiles(config: dict) -> List[Profile]:
    configured = config.get("profiles")
    if isinstance(configured, list) and configured:
        candidates = [
            (Path(p["dir"]).expanduser(), p.get("label"))
            for p in configured
            if isinstance(p, dict) and p.get("dir")
        ]
    else:
        extra = sorted(
            d for d in HOME.glob(".claude-*")
            if d.is_dir() and ".bak" not in d.name and (d / "projects").is_dir()
        )
        candidates = [(d, None) for d in [HOME / ".claude"] + extra]

    profiles = []
    seen_emails = set()
    for config_dir, label in candidates:
        email = _account_email(config_dir)
        if email is None:
            continue
        # Several dirs can hold the same login; show each account once.
        if email.lower() in seen_emails:
            continue
        seen_emails.add(email.lower())
        profiles.append(Profile(config_dir, label or _default_label(email), email))
    return profiles


# --- Data sources ---

def _window_from_cache(pct, resets_at_raw) -> LimitWindow:
    pct = float(pct) if pct is not None else None
    resets_at = parse_iso(resets_at_raw)
    if pct is not None and resets_at and resets_at <= datetime.now(timezone.utc):
        return LimitWindow(0.0, None)
    return LimitWindow(pct, resets_at)


def read_limits(profile: Profile) -> Optional[Limits]:
    """Read the account's real limit utilisation as last fetched by the OMC HUD."""
    # The cache is another tool's file; any unexpected shape means "no limit data".
    try:
        with open(profile.config_dir / OMC_USAGE_CACHE) as f:
            cache = json.load(f)
        data = cache["data"]
        fetched_ms = cache.get("lastSuccessAt") or cache["timestamp"]
        return Limits(
            five_hour=_window_from_cache(data.get("fiveHourPercent"), data.get("fiveHourResetsAt")),
            weekly=_window_from_cache(data.get("weeklyPercent"), data.get("weeklyResetsAt")),
            fetched_at=datetime.fromtimestamp(fetched_ms / 1000, tz=timezone.utc),
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError):
        return None


def read_session(profile: Profile, analyze_usage) -> Optional[Session]:
    result = analyze_usage(
        hours_back=24,
        quick_start=True,
        data_path=str(profile.config_dir / "projects"),
    )
    active = [b for b in result.get("blocks", []) if b.get("isActive")]
    if not active:
        return None
    block = active[0]

    # claude-monitor folds unknown model ids into old names (e.g. claude-3-opus),
    # so group by the raw id on each entry instead of perModelStats.
    model_tokens = defaultdict(int)
    for entry in block.get("entries", []):
        model = entry.get("model") or "unknown"
        model_tokens[model] += (entry.get("inputTokens") or 0) + (entry.get("outputTokens") or 0)

    return Session(
        tokens=block.get("totalTokens") or 0,
        cost=block.get("costUSD") or 0.0,
        messages=block.get("sentMessagesCount") or 0,
        duration_min=block.get("durationMinutes") or 0,
        cost_per_hour=(block.get("burnRate") or {}).get("costPerHour", 0) or 0,
        ends_at=parse_iso(block.get("endTime")),
        model_tokens=dict(model_tokens),
    )


def collect(profile: Profile, analyze_usage) -> ProfileUsage:
    limits = read_limits(profile)
    try:
        session = read_session(profile, analyze_usage)
    except Exception as e:
        return ProfileUsage(profile, limits, None, error=str(e)[:80])
    return ProfileUsage(profile, limits, session)


# --- Rendering ---

def _fresh_pcts(usage: ProfileUsage) -> List[float]:
    limits = usage.limits
    if limits is None or limits.stale:
        return []
    return [w.pct for w in (limits.five_hour, limits.weekly) if w.pct is not None]


def _title_segment(usage: ProfileUsage, display: list) -> str:
    limits, session = usage.limits, usage.session
    parts = []
    for key in display:
        if key == "session_pct" and limits and limits.five_hour.pct is not None:
            parts.append(f"{limits.five_hour.pct:.0f}%")
        elif key == "weekly_pct" and limits and limits.weekly.pct is not None:
            parts.append(f"W{limits.weekly.pct:.0f}%")
        elif key == "cost" and session:
            parts.append(fmt_cost(session.cost))
        elif key == "msg" and session:
            parts.append(f"{session.messages}msg")
    return f"{usage.profile.tag} " + (" ".join(parts) if parts else "–")


def print_title(usages: List[ProfileUsage], display: list) -> None:
    title = "  ".join(_title_segment(u, display) for u in usages)
    pcts = [p for u in usages for p in _fresh_pcts(u)]
    color = get_color(max(pcts)) if pcts else COLOR_GRAY
    print(f"{title} | color={color} font={TITLE_FONT} size={TITLE_SIZE} offset={TITLE_OFFSET}")


def _row(text: str, color: str = COLOR_DIM, size: int = SMALL_SIZE) -> None:
    print(f"{text} | color={color} font={MONO_FONT} size={size}")


def _print_window(name: str, window: LimitWindow, stale: bool) -> None:
    if window.pct is None:
        return
    color = COLOR_GRAY if stale else get_color(window.pct)
    reset = f"  resets {fmt_reset(window.resets_at)}" if window.resets_at else ""
    _row(f"  {name:<5}{bar_graph(window.pct, 14)} {window.pct:>4.0f}%{reset}", color)


def print_profile(usage: ProfileUsage) -> None:
    profile, limits, session = usage.profile, usage.limits, usage.session
    _row(f"{profile.label}  {profile.email}", COLOR_WHITE, BODY_SIZE)

    if limits:
        _print_window("5h", limits.five_hour, limits.stale)
        _print_window("Week", limits.weekly, limits.stale)
        if limits.stale:
            _row(f"  limits as of {fmt_age(limits.age_seconds)}", COLOR_GRAY)
    else:
        _row("  limit % unavailable (no oh-my-claudecode HUD cache)", COLOR_GRAY)

    if usage.error:
        _row(f"  error: {usage.error}", COLOR_RED)
    elif session is None:
        _row("  Idle — no active session", COLOR_GRAY)
    else:
        _row(f"  Session  {fmt_duration(session.duration_min)}  {session.messages} msg", COLOR_LABEL)
        _row(f"  Tokens   {fmt_number(session.tokens)}", COLOR_LABEL)
        _row(f"  Cost     ≈{fmt_cost(session.cost)} API-equivalent", COLOR_LABEL)
        tpm = session.tokens / session.duration_min if session.duration_min > 0 else 0
        _row(f"  Burn     {tpm:.0f} tok/min  {fmt_cost(session.cost_per_hour / 60)}/min", COLOR_LABEL)
        if limits is None and session.ends_at:
            _row(f"  Block ends {fmt_time(session.ends_at)}", COLOR_LABEL)
        _print_models(session)


def _print_models(session: Session) -> None:
    total = sum(session.model_tokens.values())
    if total <= 0:
        return
    _row("  Models", COLOR_LABEL)
    for model, tokens in sorted(session.model_tokens.items(), key=lambda kv: kv[1], reverse=True):
        pct = tokens / total * 100
        name = model if len(model) <= 22 else model[:22] + "…"
        _row(f"--{name:<24} {pct:>3.0f}%", COLOR_DIM)


def print_display_submenu(display: list) -> None:
    _row("Display", COLOR_WHITE, BODY_SIZE)
    script = os.path.realpath(__file__)
    for key, label in DISPLAY_METRICS:
        check = "✓ " if key in display else "   "
        print(
            f"--{check}{label} | font={MONO_FONT} size={SMALL_SIZE} bash={script} "
            f"param1=--toggle-display param2={key} terminal=false refresh=true"
        )


def print_footer() -> None:
    print(f"Open Terminal Monitor | font={MONO_FONT} size={BODY_SIZE} bash=ccm terminal=true")
    print(f"Refresh | font={MONO_FONT} size={BODY_SIZE} refresh=true")


def print_error(title: str, message: str) -> None:
    print(f"CCM — | color={COLOR_GRAY} font={TITLE_FONT} size={TITLE_SIZE} offset={TITLE_OFFSET}")
    print("---")
    _row(title, COLOR_RED, BODY_SIZE)
    _row(message)


def main() -> None:
    try:
        from claude_monitor.data.analysis import analyze_usage
    except ImportError:
        print_error("claude-monitor not installed", "Install: uv tool install claude-monitor")
        return

    config = load_config()
    profiles = discover_profiles(config)
    if not profiles:
        print_error("No Claude Code profile found", "Log in with `claude` first")
        return

    usages = [collect(p, analyze_usage) for p in profiles]
    display = get_display(config)

    print_title(usages, display)
    print("---")
    for usage in usages:
        print_profile(usage)
        print("---")
    print_display_submenu(display)
    print_footer()


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--toggle-display":
        chosen = sys.argv[2].lower().strip()
        if chosen in {k for k, _ in DISPLAY_METRICS}:
            toggle_display(chosen)
        sys.exit(0)

    main()
