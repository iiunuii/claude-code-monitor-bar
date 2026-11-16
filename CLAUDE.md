# CLAUDE.md

This file provides context for AI assistants working on this project.

## Project overview

Claude Code Monitor Bar is a macOS menu bar widget (SwiftBar/xbar plugin) that displays real-time Claude AI token usage. It's a single Python script that outputs SwiftBar-formatted text.

## Architecture

- **Single file**: `claude-monitor.30s.py` — the entire plugin
- **Dependency**: `claude-monitor` Python package (provides `analyze_usage()`)
- **Runtime**: Executed by SwiftBar every 30 seconds (configurable via filename)
- **Config**: `~/.claude-monitor/widget-config.json` for display metrics and an optional `profiles` list
- **Limit % source**: oh-my-claudecode HUD cache at `<profile>/plugins/oh-my-claudecode/.usage-cache-anthropic.json` (Anthropic's real 5h/weekly utilisation). claude-monitor's plan token caps are not used; they don't match real limits

## Key conventions

- All output goes to stdout in SwiftBar pipe-delimited format
- First `print()` call = menu bar title, everything after `---` = dropdown
- Colors are defined as constants at the top (`COLOR_GREEN`, `COLOR_RED`, etc.)
- Fonts use `SFMono-Regular` for a clean monospace look
- Font sizes: `TITLE_SIZE` (12) for menu bar, `BODY_SIZE` (12) for section headers, `SMALL_SIZE` (11) for detail rows
- `TITLE_OFFSET` controls vertical alignment of the menu bar text

## Code structure

1. **Path setup** (`_setup_uv_tool_path`) — auto-detects `uv tool` installations
2. **Constants** — colors, fonts, display metrics
3. **Domain model** — `Profile`, `LimitWindow`, `Limits`, `Session`, `ProfileUsage` dataclasses
4. **Config** — `load_config`, `get_display`, `toggle_display`
5. **Profiles** — `discover_profiles` (default `~/.claude` + `~/.claude-*`, deduped by account email)
6. **Data sources** — `read_limits` (OMC cache), `read_session` (`analyze_usage(data_path=...)`, models grouped by raw entry id)
7. **Rendering** — `print_title` (`R $3.45 24%  P 0%`), `print_profile`, `print_display_submenu`
8. **CLI args** — `--toggle-display` for SwiftBar callbacks

## Testing

```bash
# Syntax check
python3 -c "import ast; ast.parse(open('claude-monitor.30s.py').read())"

# Run directly (requires claude-monitor installed)
python3 claude-monitor.30s.py
```

## Things to keep in mind

- This must stay as a single `.py` file — SwiftBar plugins are individual scripts
- Python 3.9+ compatibility required (macOS system Python)
- No additional pip dependencies beyond `claude-monitor`
- SwiftBar runs scripts with system Python, so `_setup_uv_tool_path` is essential
- Unicode characters (block bars, arrows, checkmarks) are used for visual elements
- The `offset=` parameter on title lines adjusts vertical centering in the menu bar
