# Claude Code Monitor Bar

A clean, minimal macOS menu bar widget that shows your Claude AI token usage at a glance. Built for [SwiftBar](https://github.com/swiftbar/SwiftBar).

```
TKN 72%  CST $3.45
```

## Features

- **Live metrics** in your menu bar — token %, cost, messages
- **Bar graph dropdown** with detailed session stats
- **Color-coded** usage levels (green / yellow / orange / red)
- **Burn rate & ETA** — see when tokens will run out
- **Model distribution** breakdown per session
- **Configurable** — pick your plan, choose which metrics to show
- **Zero-daemon** — SwiftBar handles all scheduling

### Menu bar states

| Display | Meaning |
|---------|---------|
| `TKN 72%  CST $3.45` | Active session |
| `CCM  Idle` | No active session |
| `CCM  —` | Error (click for details) |

### Dropdown preview

```
Plan: Pro
Display
───────────────────
Tokens
  ████████████░░░░  72.3%
  13,248 / 19,000
Cost
  ███░░░░░░░░░░░░░  19.2%
  $3.45 / $18.00
Messages
  █████░░░░░░░░░░░  34.8%
  87 / 250
Duration
  1h 23m
───────────────────
Burn  42 tok/min  $0.02/min
ETA   2h 34m left -> 3:15 PM
Reset 5:45 PM
───────────────────
Models
  claude-sonnet-4-5          85%
  claude-opus-4              15%
───────────────────
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

### Step 4 — Configure your plan (optional)

The widget defaults to the **Pro** plan. To change it, use either method:

**Environment variable** — add to `~/.zshrc` or `~/.bashrc`:

```bash
export CCM_PLAN=pro  # pro, max5, max20, custom
```

**Config file** — create `~/.claude-monitor/widget-config.json`:

```json
{
  "plan": "pro"
}
```

Or just click the **Plan** submenu in the dropdown to switch.

## Customization

| Setting | How |
|---------|-----|
| **Refresh interval** | Rename the file: `claude-monitor.10s.py` (10s), `claude-monitor.1m.py` (1min) |
| **Plan type** | `CCM_PLAN` env var, config file, or dropdown submenu |
| **Display metrics** | Click **Display** in the dropdown to toggle TKN%, CST, MSG, etc. |
| **Terminal monitor** | "Open Terminal Monitor" runs `ccm` — change in `_print_footer()` |

## How It Works

The plugin runs on a schedule set by the filename (default: every 30 seconds). It:

1. Imports the `claude-monitor` Python library
2. Calls `analyze_usage()` to read JSONL logs from `~/.claude/projects/`
3. Finds the active 5-hour session block
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
