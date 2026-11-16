# Claude Code Monitor Bar

A clean, minimal macOS menu bar widget that shows your Claude Code usage for every account profile at a glance. Built for [SwiftBar](https://github.com/swiftbar/SwiftBar).

```
R $3.45 24%  P 0%
```

## Features

- **Multiple profiles** — the default `~/.claude` plus any `CLAUDE_CONFIG_DIR` profile (e.g. `~/.claude-personal`), one row per account
- **Real limit %** — the 5-hour and weekly utilisation Anthropic reports for the account, not an estimate from a guessed token cap
- **Session stats** — tokens, API-equivalent cost, burn rate, model mix from local logs
- **Color-coded** usage levels (green / yellow / orange / red); gray when the limit data is stale
- **Configurable** — choose which metrics show in the menu bar
- **Zero-daemon** — SwiftBar handles all scheduling

### Menu bar states

| Display | Meaning |
|---------|---------|
| `R $3.45 24%  P 0%` | One segment per profile: first letter of its label, then the enabled metrics |
| `P –` | Profile with no limit data and no active session |
| `CCM  —` | Error (click for details) |

### Dropdown preview

```
Rentspree  you@company.com
  5h   ███░░░░░░░░░░░   24%  resets 11:59 AM
  Week ██░░░░░░░░░░░░   18%  resets Fri 1:59 AM
  Session  1h 41m  223 msg
  Tokens   267,502
  Cost     ≈$56.65 API-equivalent
  Burn     2624 tok/min  $0.56/min
  Models                                  >
───────────────────
Personal  you@gmail.com
  5h   ░░░░░░░░░░░░░░    0%
  Week ███░░░░░░░░░░░   23%  resets Thu 3:00 PM
  limits as of 19h 56m ago
  Idle — no active session
───────────────────
Display                                   >
Open Terminal Monitor
Refresh
```

### Color thresholds

| Color | Usage |
|-------|-------|
| Green | < 50% |
| Yellow | 50 -- 80% |
| Orange | 80 -- 95% |
| Red | >= 95% |

## Installation

### Prerequisites

- macOS
- [SwiftBar](https://github.com/swiftbar/SwiftBar) (or [xbar](https://github.com/matryer/xbar))
- Python 3.9+
- [`claude-monitor`](https://pypi.org/project/claude-monitor/) package

### Step 1 — Install SwiftBar

```bash
brew install --cask swiftbar
```

On first launch, SwiftBar asks you to choose a plugin directory (e.g. `~/swiftbar-plugins/`).

### Step 2 — Install claude-monitor

```bash
pip install claude-monitor
```

or with [uv](https://github.com/astral-sh/uv):

```bash
uv tool install claude-monitor
```

### Step 3 — Add the plugin

**Option A: Clone + symlink (recommended)**

```bash
git clone https://github.com/iiunuii/claude-code-monitor-bar.git
cd claude-code-monitor-bar
ln -s "$(pwd)/claude-monitor.30s.py" ~/swiftbar-plugins/claude-monitor.30s.py
```

This way you get updates by running `git pull`.

**Option B: Download directly**

```bash
curl -o ~/swiftbar-plugins/claude-monitor.30s.py \
  https://raw.githubusercontent.com/iiunuii/claude-code-monitor-bar/main/claude-monitor.30s.py
chmod +x ~/swiftbar-plugins/claude-monitor.30s.py
```

The widget appears in your menu bar automatically.

### Step 4 — Limit % data (optional)

The 5h and weekly percentages come from the usage cache the [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) HUD writes to `<profile>/plugins/oh-my-claudecode/.usage-cache-anthropic.json` while a Claude Code session runs in that profile. Without it, the profile still shows tokens and cost, just no %. Data older than 10 minutes is shown in gray with its age; a window whose reset time has passed shows 0%.

### Step 5 — Profiles (optional)

By default the widget shows `~/.claude` and every `~/.claude-*` directory that holds a logged-in Claude Code profile, once per account email. To pick profiles and labels yourself, edit `~/.claude-monitor/widget-config.json`:

```json
{
  "profiles": [
    {"dir": "~/.claude", "label": "Work"},
    {"dir": "~/.claude-personal", "label": "Personal"}
  ]
}
```

## Customization

| Setting | How |
|---------|-----|
| **Refresh interval** | Rename the file: `claude-monitor.10s.py` (10s), `claude-monitor.1m.py` (1min) |
| **Profiles** | `profiles` in the config file (see Step 5) |
| **Display metrics** | Click **Display** in the dropdown to toggle 5h %, weekly %, cost, messages |
| **Terminal monitor** | "Open Terminal Monitor" runs `ccm` — change in `print_footer()` |

## How It Works

The plugin runs on a schedule set by the filename (default: every 30 seconds). It:

1. Finds each Claude Code profile and its account email
2. Reads the account's real 5h / weekly limit % from the oh-my-claudecode usage cache
3. Calls `claude-monitor`'s `analyze_usage(data_path=<profile>/projects)` for the active session's tokens, cost and models
4. Formats metrics using the SwiftBar pipe-delimited protocol

No daemon, no server — SwiftBar handles the scheduling.

## Troubleshooting

**Widget shows `CCM  —`**
- Click it to see the error detail
- Check that `claude-monitor` is installed: `pip show claude-monitor`
- Make sure SwiftBar's Python can find the package (see shebang note below)

**Widget shows `CCM  Idle` while working**
- The 5-hour session window may have expired
- Click **Refresh** in the dropdown

**Python path issues**
SwiftBar runs scripts with the system Python. If you installed `claude-monitor` in a venv, update the shebang:

```python
#!/path/to/your/venv/bin/python3
```

The plugin auto-detects `uv tool` installations — no extra config needed.

## Compatibility

Works with both [SwiftBar](https://github.com/swiftbar/SwiftBar) and [xbar](https://github.com/matryer/xbar) (formerly BitBar).

## License

MIT License. See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
