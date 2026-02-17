# Contributing to Claude Code Monitor Bar

Thanks for your interest in contributing! This is a small project and contributions of all sizes are welcome.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/<your-username>/claude-code-monitor-bar.git
   cd claude-code-monitor-bar
   ```
3. Install dependencies:
   ```bash
   pip install claude-monitor
   ```
4. Symlink to your SwiftBar plugins directory for testing:
   ```bash
   ln -sf "$(pwd)/claude-monitor.30s.py" ~/swiftbar-plugins/claude-monitor.30s.py
   ```

## Development

The entire plugin is a single Python file (`claude-monitor.30s.py`) that outputs SwiftBar-formatted text to stdout.

### Project structure

```
claude-monitor.30s.py   # The SwiftBar plugin (single file)
README.md               # Documentation
CONTRIBUTING.md         # This file
CLAUDE.md               # AI assistant context
LICENSE                 # MIT License
```

### Testing changes

1. Edit `claude-monitor.30s.py`
2. Run it directly to see the output:
   ```bash
   python3 claude-monitor.30s.py
   ```
3. Or click **Refresh** in the SwiftBar dropdown to reload

### Code style

- Python 3.9+ compatible
- Follow existing patterns in the codebase
- Keep it as a single file — no extra modules or dependencies beyond `claude-monitor`
- Use the existing color/font constants instead of hardcoding values
- Test that the script outputs valid SwiftBar format (pipe-delimited parameters)

## Making Changes

### What to work on

- Bug fixes
- New display metrics
- Better formatting or visual improvements
- Documentation improvements
- Compatibility fixes for xbar

### Submitting a pull request

1. Create a branch for your change:
   ```bash
   git checkout -b my-change
   ```
2. Make your changes and test them with SwiftBar
3. Verify the script has no syntax errors:
   ```bash
   python3 -c "import ast; ast.parse(open('claude-monitor.30s.py').read())"
   ```
4. Commit with a clear message describing what and why
5. Push and open a pull request against `main`

### PR guidelines

- Keep PRs focused — one change per PR
- Describe what the change does and why
- Include a screenshot if the change affects the UI
- Make sure the script runs without errors

## SwiftBar Reference

If you're new to SwiftBar plugin development:

- [SwiftBar Plugin API](https://github.com/swiftbar/SwiftBar#plugin-api)
- First line of output = menu bar title
- `---` = separator
- `|` followed by key=value pairs for styling (e.g. `color=`, `font=`, `size=`)
- `--` prefix = submenu item

## Reporting Issues

- Open an issue on GitHub
- Include your macOS version, SwiftBar version, and Python version
- Paste the output of `python3 claude-monitor.30s.py` if relevant

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
