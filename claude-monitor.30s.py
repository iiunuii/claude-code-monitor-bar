#!/usr/bin/env python3

# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideLastUpdated>true</swiftbar.hideLastUpdated>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>

# Metadata for SwiftBar plugin manager
# <bitbar.title>Claude Code Usage Monitor</bitbar.title>
# <bitbar.version>v1.0.0</bitbar.version>
# <bitbar.author>iiunuii</bitbar.author>
# <bitbar.author.github>iiunuii</bitbar.author.github>
# <bitbar.desc>Real-time Claude AI token usage monitor for your menu bar. Shows token %, cost, messages, burn rate, and more.</bitbar.desc>
# <bitbar.dependencies>python3, claude-monitor</bitbar.dependencies>
# <bitbar.abouturl>https://github.com/iiunuii/claude-code-monitor-bar</bitbar.abouturl>
# <swiftbar.schedule>*/30 * * * * *</swiftbar.schedule>

"""
SwiftBar/xbar plugin for Claude Code Usage Monitor.

Shows Claude AI token usage in the macOS menu bar with a dropdown
showing detailed session metrics. Refreshes every 30 seconds.

Installation:
    1. Install SwiftBar: brew install --cask swiftbar
    2. Install claude-monitor: pip install claude-monitor
    3. Copy or symlink this file to your SwiftBar plugin directory
    4. The widget appears in the menu bar automatically

Configuration:
    Set your plan via environment variable or config file:
    - Environment: export CCM_PLAN=pro  (pro, max5, max20, custom)
    - Config file: ~/.claude-monitor/widget-config.json
      {"plan": "pro"}

If claude-monitor is installed via 'uv tool', the script auto-detects
the uv tool venv and adds it to sys.path so imports work regardless
of which Python SwiftBar invokes.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# --- Auto-detect uv tool venv for claude-monitor ---
# When installed via `uv tool install claude-monitor`, the package lives in
# ~/.local/share/uv/tools/claude-monitor/lib/python*/site-packages/
# SwiftBar runs with the system python which can't see that, so we add it.
def _setup_uv_tool_path():
    """Add uv tool site-packages to sys.path if claude_monitor isn't importable."""
    try:
        import claude_monitor  # noqa: F401
        return  # already importable, nothing to do
    except ImportError:
        pass

    uv_tool_dir = Path.home() / ".local" / "share" / "uv" / "tools" / "claude-monitor"
    if not uv_tool_dir.exists():
        return

    lib_dir = uv_tool_dir / "lib"
    if not lib_dir.exists():
        return

    # Find python*/site-packages under lib/
    for pydir in sorted(lib_dir.glob("python*/site-packages"), reverse=True):
        if pydir.is_dir():
            sys.path.insert(0, str(pydir))
            return


_setup_uv_tool_path()

# --- Color thresholds (SwiftBar ANSI hex) ---
COLOR_GREEN = "#6BDB7B"
COLOR_YELLOW = "#FFD95C"
COLOR_ORANGE = "#FF9F43"
COLOR_RED = "#FF6B6B"
COLOR_GRAY = "#8E8E93"
COLOR_WHITE = "#FFFFFF"
COLOR_DIM = "#A0A0A8"
COLOR_LABEL = "#B0B0B8"

# --- Font settings ---
TITLE_FONT = "SFMono-Regular"
TITLE_SIZE = 12
TITLE_OFFSET = 2  # push title down 2px to vertically center
MONO_FONT = "SFMono-Regular"
BODY_SIZE = 12
SMALL_SIZE = 11


def get_color(pct: float) -> str:
    """Return a hex color based on usage percentage."""
    if pct >= 95:
        return COLOR_RED
    if pct >= 80:
        return COLOR_ORANGE
    if pct >= 50:
        return COLOR_YELLOW
    return COLOR_GREEN


def bar_graph(pct: float, width: int = 10) -> str:
    """Create a minimal bar using unicode block characters."""
    filled = int(pct / 100 * width)
    filled = min(filled, width)
    return "\u2588" * filled + "\u2591" * (width - filled)


def fmt_number(n: int) -> str:
    """Format a number with comma separators."""
    return f"{n:,}"


def fmt_cost(c: float) -> str:
    """Format a cost value as $X.XX."""
    return f"${c:.2f}"


def fmt_pct(v: float, total: float) -> str:
    """Format a value as a percentage of a total."""
    if total <= 0:
        return "0.0%"
    return f"{v / total * 100:.1f}%"


def fmt_duration(minutes: float) -> str:
    """Format minutes into a human-readable duration."""
    if minutes < 1:
        return "<1m"
    if minutes < 60:
        return f"{int(minutes)}m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    return f"{hours}h {mins}m"


def fmt_time(dt: datetime) -> str:
    """Format a datetime to local time string."""
    local = dt.astimezone()
    return local.strftime("%-I:%M %p")


VALID_PLANS = ("pro", "max5", "max20", "custom")
PLAN_LABELS = {"pro": "Pro", "max5": "Max 5", "max20": "Max 20", "custom": "Custom"}
CONFIG_PATH = Path.home() / ".claude-monitor" / "widget-config.json"

# Display metrics — each can be toggled on/off independently
DISPLAY_METRICS = (
    ("token_pct", "Token %"),
    ("cost", "Cost ($)"),
    ("cost_pct", "Cost %"),
    ("msg", "Messages"),
    ("msg_pct", "Message %"),
)
DEFAULT_DISPLAY = ["token_pct", "cost"]


def get_plan() -> str:
    """Get the plan type from env var, widget config, or default."""
    # 1. Environment variable
    plan = os.environ.get("CCM_PLAN", "").lower().strip()
    if plan in VALID_PLANS:
        return plan

    # 2. Widget config file
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                config = json.load(f)
            plan = config.get("plan", "").lower().strip()
            if plan in VALID_PLANS:
                return plan
        except Exception:
            pass

    # 3. LastUsedParams (plan isn't normally saved here, but check anyway)
    params_path = Path.home() / ".claude-monitor" / "last_used.json"
    if params_path.exists():
        try:
            with open(params_path) as f:
                params = json.load(f)
            plan = params.get("plan", "").lower().strip()
            if plan in VALID_PLANS:
                return plan
        except Exception:
            pass

    return "pro"


def set_plan(plan: str) -> None:
    """Save the selected plan to the widget config file."""
    _save_config("plan", plan)


def get_display() -> list:
    """Get the list of enabled display metrics from config."""
    valid_keys = {k for k, _ in DISPLAY_METRICS}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                config = json.load(f)
            display = config.get("display")
            if isinstance(display, list):
                filtered = [d for d in display if d in valid_keys]
                if filtered:
                    return filtered
        except Exception:
            pass
    return list(DEFAULT_DISPLAY)


def toggle_display(metric: str) -> None:
    """Toggle a display metric on/off and save."""
    current = get_display()
    if metric in current:
        current.remove(metric)
    else:
        current.append(metric)
    # Keep at least one metric enabled
    if not current:
        current = list(DEFAULT_DISPLAY)
    _save_config("display", current)


def _save_config(key: str, value) -> None:
    """Save a key-value pair to the widget config file."""
    config = {}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                config = json.load(f)
        except Exception:
            pass

    config[key] = value
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def print_error(title: str, message: str) -> None:
    """Print a SwiftBar error menu."""
    print(f"CCM \u2014 | color={COLOR_GRAY} font={TITLE_FONT} size={TITLE_SIZE} offset={TITLE_OFFSET}")
    print("---")
    print(f"{title} | color={COLOR_RED} font={MONO_FONT} size={BODY_SIZE}")
    print(f"{message} | color={COLOR_DIM} font={MONO_FONT} size={SMALL_SIZE}")


def main() -> None:
    # --- Try importing claude_monitor ---
    try:
        from claude_monitor.core.plans import Plans
        from claude_monitor.data.analysis import analyze_usage
    except ImportError:
        print_error(
            "claude-monitor not installed",
            "Install: pip install claude-monitor",
        )
        print("---")
        print(
            f"Install claude-monitor | font={MONO_FONT} size={BODY_SIZE} "
            "bash='pip' param1='install' param2='claude-monitor' terminal=true"
        )
        return

    # --- Fetch data ---
    try:
        result = analyze_usage(hours_back=24, quick_start=True)
    except Exception as e:
        print_error("Error loading data", str(e)[:80])
        return

    blocks = result.get("blocks", [])
    if not blocks:
        print(f"CCM  Idle | color={COLOR_GRAY} font={TITLE_FONT} size={TITLE_SIZE} offset={TITLE_OFFSET}")
        print("---")
        print(f"No usage data found | color={COLOR_DIM} font={MONO_FONT} size={BODY_SIZE}")
        print(f"Start a Claude Code session to see metrics | color={COLOR_DIM} font={MONO_FONT} size={SMALL_SIZE}")
        return

    # --- Find active block ---
    active_blocks = [b for b in blocks if b.get("isActive")]
    if not active_blocks:
        last = blocks[-1]
        tokens = last.get("totalTokens", 0)
        cost = last.get("costUSD", 0.0)
        msgs = last.get("sentMessagesCount", 0)
        dur = last.get("durationMinutes", 0)
        print(f"CCM  Idle | color={COLOR_GRAY} font={TITLE_FONT} size={TITLE_SIZE} offset={TITLE_OFFSET}")
        print("---")
        print(f"Last Session | color={COLOR_WHITE} font={MONO_FONT} size={BODY_SIZE}")
        print(f"  TKN  {fmt_number(tokens):>10}     MSG  {msgs} | font={MONO_FONT} size={SMALL_SIZE} color={COLOR_DIM}")
        print(f"  CST  {fmt_cost(cost):>10}     DUR  {fmt_duration(dur)} | font={MONO_FONT} size={SMALL_SIZE} color={COLOR_DIM}")
        print("---")
        _print_footer()
        return

    block = active_blocks[0]

    # --- Get limits ---
    plan = get_plan()
    token_limit = Plans.get_token_limit(plan, blocks)
    cost_limit = Plans.get_cost_limit(plan)
    msg_limit = Plans.get_message_limit(plan)

    # --- Extract metrics ---
    tokens = block.get("totalTokens", 0)
    cost = block.get("costUSD", 0.0)
    messages = block.get("sentMessagesCount", 0)
    duration = block.get("durationMinutes", 0)

    token_pct = (tokens / token_limit * 100) if token_limit > 0 else 0
    cost_pct = (cost / cost_limit * 100) if cost_limit > 0 else 0
    msg_pct = (messages / msg_limit * 100) if msg_limit > 0 else 0

    # Use the highest percentage for color coding
    max_pct = max(token_pct, cost_pct, msg_pct)
    color = get_color(max_pct)

    # --- Menu bar title (clean, label-value style) ---
    display = get_display()
    title = _format_title(display, token_pct, cost_pct, msg_pct, cost, messages, msg_limit)
    print(f"{title} | color={color} font={TITLE_FONT} size={TITLE_SIZE} offset={TITLE_OFFSET}")

    # --- Dropdown ---
    print("---")
    _print_plan_submenu(plan)
    _print_display_submenu(display)
    print("---")

    # --- Session metrics with bar graphs ---
    tkn_color = get_color(token_pct)
    cst_color = get_color(cost_pct)
    msg_color = get_color(msg_pct)

    print(f"Tokens | color={COLOR_WHITE} font={MONO_FONT} size={BODY_SIZE}")
    print(f"  {bar_graph(token_pct, 16)}  {token_pct:.1f}% | color={tkn_color} font={MONO_FONT} size={SMALL_SIZE}")
    print(f"  {fmt_number(tokens)} / {fmt_number(token_limit)} | color={COLOR_DIM} font={MONO_FONT} size={SMALL_SIZE}")
    print(f"Cost | color={COLOR_WHITE} font={MONO_FONT} size={BODY_SIZE}")
    print(f"  {bar_graph(cost_pct, 16)}  {cost_pct:.1f}% | color={cst_color} font={MONO_FONT} size={SMALL_SIZE}")
    print(f"  {fmt_cost(cost)} / {fmt_cost(cost_limit)} | color={COLOR_DIM} font={MONO_FONT} size={SMALL_SIZE}")
    print(f"Messages | color={COLOR_WHITE} font={MONO_FONT} size={BODY_SIZE}")
    print(f"  {bar_graph(msg_pct, 16)}  {msg_pct:.1f}% | color={msg_color} font={MONO_FONT} size={SMALL_SIZE}")
    print(f"  {fmt_number(messages)} / {fmt_number(msg_limit)} | color={COLOR_DIM} font={MONO_FONT} size={SMALL_SIZE}")
    print(f"Duration | color={COLOR_WHITE} font={MONO_FONT} size={BODY_SIZE}")
    print(f"  {fmt_duration(duration)} | color={COLOR_DIM} font={MONO_FONT} size={SMALL_SIZE}")

    # --- Burn rate & projections ---
    burn_rate = block.get("burnRate")
    projection = block.get("projection")

    if burn_rate or projection:
        print("---")

    if burn_rate:
        tpm = burn_rate.get("tokensPerMinute", 0)
        cph = burn_rate.get("costPerHour", 0)
        cost_per_min = cph / 60 if cph else 0
        print(f"Burn  {tpm:.0f} tok/min  {fmt_cost(cost_per_min)}/min | color={COLOR_LABEL} font={MONO_FONT} size={SMALL_SIZE}")

    if projection:
        remaining = projection.get("remainingMinutes", 0)
        if remaining and remaining > 0:
            exhaust_time = datetime.now(timezone.utc) + timedelta(minutes=remaining)
            print(f"ETA   {fmt_duration(remaining)} left \u2192 {fmt_time(exhaust_time)} | color={COLOR_LABEL} font={MONO_FONT} size={SMALL_SIZE}")

    # --- Reset time (end of 5h block) ---
    end_time_str = block.get("endTime")
    if end_time_str:
        try:
            end_time = datetime.fromisoformat(end_time_str)
            print(f"Reset {fmt_time(end_time)} | color={COLOR_LABEL} font={MONO_FONT} size={SMALL_SIZE}")
        except (ValueError, TypeError):
            pass

    # --- Model distribution ---
    per_model = block.get("perModelStats", {})
    if per_model and tokens > 0:
        print("---")
        print(f"Models | color={COLOR_WHITE} font={MONO_FONT} size={BODY_SIZE}")
        sorted_models = sorted(
            per_model.items(),
            key=lambda x: x[1].get("totalTokens", 0)
            if isinstance(x[1], dict)
            else 0,
            reverse=True,
        )
        for model_name, stats in sorted_models:
            if isinstance(stats, dict):
                model_tokens = stats.get("totalTokens", 0)
                pct = model_tokens / tokens * 100 if tokens > 0 else 0
                short_name = model_name
                if len(short_name) > 22:
                    short_name = short_name[:22] + "\u2026"
                m_color = get_color(pct) if pct > 50 else COLOR_DIM
                print(f"  {short_name:<24} {pct:>3.0f}% | color={m_color} font={MONO_FONT} size={SMALL_SIZE}")

    # --- Limit warnings ---
    limit_msgs = block.get("limitMessages", [])
    if limit_msgs:
        print("---")
        print(f"\u26a0 Limit Reached | color={COLOR_RED} font={MONO_FONT} size={BODY_SIZE}")
        for lm in limit_msgs[:3]:
            ltype = lm.get("type", "unknown")
            reset = lm.get("reset_time")
            msg = f"  {ltype}"
            if reset:
                try:
                    rt = datetime.fromisoformat(reset)
                    msg += f" \u2192 resets {fmt_time(rt)}"
                except (ValueError, TypeError):
                    pass
            print(f"{msg} | font={MONO_FONT} size={SMALL_SIZE} color={COLOR_RED}")

    # --- Footer ---
    print("---")
    _print_footer()


def _format_title(
    display: list,
    token_pct: float,
    cost_pct: float,
    msg_pct: float,
    cost: float,
    messages: int,
    msg_limit: int,
) -> str:
    """Format the menu bar title — clean label + value pairs like system monitors."""
    parts = []
    for key in display:
        if key == "token_pct":
            parts.append(f"TKN {token_pct:.0f}%")
        elif key == "cost":
            parts.append(f"CST {fmt_cost(cost)}")
        elif key == "cost_pct":
            parts.append(f"CST {cost_pct:.0f}%")
        elif key == "msg":
            parts.append(f"MSG {messages}/{msg_limit}")
        elif key == "msg_pct":
            parts.append(f"MSG {msg_pct:.0f}%")
    return "  ".join(parts) if parts else "CCM"


def _print_display_submenu(current_display: list) -> None:
    """Print display metric toggles as a SwiftBar submenu."""
    print(f"Display | color={COLOR_WHITE} font={MONO_FONT} size={BODY_SIZE}")
    script = os.path.realpath(__file__)
    for key, label in DISPLAY_METRICS:
        check = "\u2713 " if key in current_display else "   "
        print(
            f"--{check}{label} | font={MONO_FONT} size={SMALL_SIZE} bash={script} "
            f"param1=--toggle-display param2={key} terminal=false refresh=true"
        )


def _print_plan_submenu(current_plan: str) -> None:
    """Print plan selector as a SwiftBar submenu."""
    label = PLAN_LABELS.get(current_plan, current_plan.upper())
    print(f"Plan: {label} | color={COLOR_WHITE} font={MONO_FONT} size={BODY_SIZE}")
    script = os.path.realpath(__file__)
    for plan_key in VALID_PLANS:
        plan_label = PLAN_LABELS[plan_key]
        check = "\u2713 " if plan_key == current_plan else "   "
        print(
            f"--{check}{plan_label} | font={MONO_FONT} size={SMALL_SIZE} bash={script} "
            f"param1=--set-plan param2={plan_key} terminal=false refresh=true"
        )


def _print_footer() -> None:
    """Print common footer items."""
    print(f"Open Terminal Monitor | font={MONO_FONT} size={BODY_SIZE} bash=ccm terminal=true")
    print(f"Refresh | font={MONO_FONT} size={BODY_SIZE} refresh=true")


if __name__ == "__main__":
    # Handle config arguments (called by SwiftBar when user picks an option)
    valid_metric_keys = {k for k, _ in DISPLAY_METRICS}
    if len(sys.argv) >= 3:
        if sys.argv[1] == "--set-plan":
            chosen = sys.argv[2].lower().strip()
            if chosen in VALID_PLANS:
                set_plan(chosen)
            sys.exit(0)
        if sys.argv[1] == "--toggle-display":
            chosen = sys.argv[2].lower().strip()
            if chosen in valid_metric_keys:
                toggle_display(chosen)
            sys.exit(0)

    main()
