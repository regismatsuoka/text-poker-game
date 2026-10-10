A simple Text base poker game!

## Starting the game

Run the start script for your shell from the project directory:

```bash
./start.sh
```

```bat
start.bat
```

```powershell
.\start.ps1
```

## Tests

The test suite contains 23 pytest tests:

- `tests/test_poker_engine.py` (21 tests): hand evaluation and comparison,
  dealing cards, betting, blinds, pot payouts, bot decisions, dealer rotation,
  action logging, and active-player tracking.
- `tests/test_text_display.py` (2 tests): plain-text card formatting and
  terminal output without graphical formatting or ANSI escape codes.

Run the tests with:

```bash
python -m pytest -q
```
