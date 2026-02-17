# CLAUDE.md

This file provides context for AI assistants working on this project.

## Project overview

Claude Code Monitor Bar is a macOS menu bar widget (SwiftBar/xbar plugin) that displays real-time Claude AI token usage. It's a single Python script that outputs SwiftBar-formatted text.

## Architecture

- **Single file**: `claude-monitor.30s.py` — the entire plugin
- **Dependency**: `claude-monitor` Python package (provides `analyze_usage()` and `Plans`)
- **Runtime**: Executed by SwiftBar every 30 seconds (configurable via filename)
- **Config**: `~/.claude-monitor/widget-config.json` for plan and display preferences

## Key conventions

- All output goes to stdout in SwiftBar pipe-delimited format
- First `print()` call = menu bar title, everything after `---` = dropdown
- Colors are defined as constants at the top (`COLOR_GREEN`, `COLOR_RED`, etc.)
- Fonts use `SFMono-Regular` for a clean monospace look
- Font sizes: `TITLE_SIZE` (12) for menu bar, `BODY_SIZE` (12) for section headers, `SMALL_SIZE` (11) for detail rows
- `TITLE_OFFSET` controls vertical alignment of the menu bar text

## Code structure

1. **Path setup** (`_setup_uv_tool_path`) — auto-detects `uv tool` installations
2. **Constants** — colors, fonts, plans, display metrics
3. **Helpers** — `fmt_number`, `fmt_cost`, `fmt_pct`, `fmt_duration`, `bar_graph`, etc.
4. **Config** — `get_plan`, `set_plan`, `get_display`, `toggle_display`
5. **Main** — fetches data via `analyze_usage()`, formats and prints output
6. **Title** — `_format_title` builds the compact `TKN 72%  CST $3.45` label
7. **Submenus** — `_print_plan_submenu`, `_print_display_submenu`
8. **CLI args** — `--set-plan` and `--toggle-display` for SwiftBar callbacks

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
