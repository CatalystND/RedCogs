# Discord Cog Testing Guide

This directory contains a comprehensive testing infrastructure for Discord cogs. The framework is **future-proof** - it works for any cog (current and future) using a generic command invocation pattern.

## Table of Contents
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Running Tests](#running-tests)
- [Test Structure](#test-structure)
- [Command Invocation Framework](#command-invocation-framework)
- [Testing Future Cogs](#testing-future-cogs)
- [Writing Tests](#writing-tests)
- [Troubleshooting](#troubleshooting)

## Quick Start

```bash
# Install test dependencies
pip3 install -r requirements-dev.txt

# Run all tests
python3 -m pytest

# Run only fast unit tests
python3 -m pytest -m unit

# Run with coverage report
python3 -m pytest --cov --cov-report=html
```

## Installation

### Test Dependencies

Install all required testing packages:

```bash
pip3 install -r requirements-dev.txt
```

This installs:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `pytest-mock` - Mocking utilities
- `aiohttp` - HTTP client (for cogs)
- `aioresponses` - Mock HTTP responses
- `beautifulsoup4` - HTML parsing
- `discord.py` - Discord library

## Running Tests

### Basic Commands

```bash
# Run all tests
python3 -m pytest

# Run with verbose output
python3 -m pytest -v

# Run specific test file
python3 -m pytest tests/unit/test_nfl_parsing.py

# Run specific test function
python3 -m pytest tests/unit/test_nfl_parsing.py::TestParseGameBox::test_parse_standard_game_box
```

### Test Categories (Markers)

Tests are organized by markers for selective execution:

```bash
# Unit tests only (fast, no I/O)
python3 -m pytest -m unit

# Discord command tests (mocked Discord)
python3 -m pytest -m discord

# Integration tests (live websites)
python3 -m pytest -m integration

# Exclude network tests
python3 -m pytest -m "not network"

# Exclude slow tests
python3 -m pytest -m "not slow"
```

### Coverage Reports

```bash
# Generate coverage report
python3 -m pytest --cov --cov-report=term-missing

# Generate HTML coverage report
python3 -m pytest --cov --cov-report=html

# View HTML report
open htmlcov/index.html
```

### Test Output Options

```bash
# Short traceback
python3 -m pytest --tb=short

# Show local variables in tracebacks
python3 -m pytest --tb=long -vv

# Stop on first failure
python3 -m pytest -x

# Run last failed tests only
python3 -m pytest --lf
```

## Test Structure

```
tests/
├── README.md                    # This file
├── conftest.py                  # Shared fixtures and command invocation framework
├── fixtures/
│   ├── nfl_html_samples.py     # Sample HTML for NFL tests
│   └── bristol_html_samples.py # Sample HTML for Bristol tests
├── unit/
│   └── test_nfl_parsing.py     # Pure function unit tests
├── discord/
│   ├── test_nfl_commands.py    # NFL Discord command tests
│   └── test_bristol_commands.py # Bristol Discord command tests
└── integration/
    ├── test_nfl_scraping.py    # Live NFL website tests
    └── test_bristol_scraping.py # Live Bristol website tests
```

## Command Invocation Framework

**The Key Innovation**: Instead of testing cog methods directly, we invoke commands by text (just like Discord does) and capture the output. This works for **ANY** cog without modification.

### How It Works

```python
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.discord
@pytest.mark.asyncio
async def test_my_command(bot, channel, load_cog, invoke_command):
    # 1. Load any cog dynamically
    await load_cog(bot, "nfl.nfl", "NFLGames")

    # 2. Mock external dependencies (web scraping, APIs)
    cog = bot.get_cog("NFLGames")
    with patch.object(cog, 'fetch_nfl_games', new_callable=AsyncMock) as mock:
        mock.return_value = sample_data

        # 3. Invoke command by text (generic!)
        messages = await invoke_command(bot, "!nfl today", channel)

        # 4. Verify Discord output
        assert len(messages) >= 1
        assert messages[0].embed.title == "NFL Games - Today"
```

### Key Components

**`bot` fixture** - Real discord.py Bot with command support
- Processes commands like Discord would
- Mocked network I/O (no actual Discord connection)

**`channel` fixture** - Mock channel that captures messages
- `channel.messages` - List of all messages sent
- `channel.send()` - Records messages for verification

**`load_cog` fixture** - Dynamically load any cog
```python
await load_cog(bot, "module.path", "CogClassName")
```

**`invoke_command` fixture** - Invoke commands by text
```python
messages = await invoke_command(bot, "!command args", channel)
```

## Testing Future Cogs

When you create a new cog, testing is simple. Here's a complete example:

### Example: Testing a Hypothetical "Weather" Cog

```python
# tests/discord/test_weather_commands.py

import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.discord
@pytest.mark.asyncio
async def test_weather_command(bot, channel, load_cog, invoke_command):
    """Test !weather command with location"""
    # Load the new cog (works exactly like NFL/Bristol)
    await load_cog(bot, "weather.weather", "Weather")

    # Mock external API
    cog = bot.get_cog("Weather")
    with patch.object(cog, 'fetch_weather', new_callable=AsyncMock) as mock:
        mock.return_value = {'temp': 72, 'condition': 'Sunny'}

        # Invoke command with arguments
        messages = await invoke_command(bot, "!weather Rochester NY", channel)

        # Verify output
        assert len(messages) == 1
        assert "72" in messages[0].embed.description
        assert "Sunny" in messages[0].embed.description


@pytest.mark.discord
@pytest.mark.asyncio
async def test_weather_no_location(bot, channel, load_cog, invoke_command):
    """Test error handling when location is missing"""
    await load_cog(bot, "weather.weather", "Weather")

    messages = await invoke_command(bot, "!weather", channel)

    assert len(messages) == 1
    assert "Please provide a location" in messages[0].content
```

**That's it!** No cog-specific infrastructure needed. The framework handles:
- ✅ Command parsing
- ✅ Argument handling
- ✅ Permission checks
- ✅ Output capture

## Writing Tests

### Test Types

#### 1. Unit Tests (Fast, No I/O)

Test pure functions in isolation:

```python
@pytest.mark.unit
def test_parse_function(bot):
    from nfl.nfl import NFLGames
    cog = NFLGames(bot)

    result = cog.parse_game_box(game_box_text)

    assert result['time'] == '4:30 PM ET'
    assert result['away'] == '5 LAR 12-5'
```

#### 2. Discord Command Tests (Mocked)

Test commands using the invocation framework:

```python
@pytest.mark.discord
@pytest.mark.asyncio
async def test_command(bot, channel, load_cog, invoke_command):
    await load_cog(bot, "nfl.nfl", "NFLGames")

    # Mock external dependencies
    cog = bot.get_cog("NFLGames")
    with patch.object(cog, 'fetch_nfl_games', new_callable=AsyncMock) as mock:
        mock.return_value = sample_data

        messages = await invoke_command(bot, "!nfl", channel)

        assert messages[0].embed.color == 0x013369
```

#### 3. Integration Tests (Live Websites)

Test against real websites:

```python
@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
async def test_live_scraping(bot):
    from nfl.nfl import NFLGames
    cog = NFLGames(bot)

    try:
        result = await cog.fetch_nfl_games()

        if result:
            assert 'games' in result
            assert 'round' in result
    finally:
        await cog.session.close()
```

### Fixtures Available

From `conftest.py`:

- **`bot`** - Discord.py Bot instance
- **`channel`** - Mock channel with message capture
- **`load_cog`** - Helper to load cogs
- **`invoke_command`** - Command invocation helper
- **`mock_guild`** - Mock Discord guild
- **`mock_author`** - Mock Discord user
- **`sample_nfl_game_box`** - Sample NFL data
- **`sample_game_data`** - Parsed game structure
- **`sample_nfl_full_response`** - Full NFL response
- **`sample_bristol_lifts`** - Bristol lift data
- **`sample_bristol_trails`** - Bristol trail data

### Mocking External APIs

Always mock web requests and external APIs:

```python
# Mock async method
with patch.object(cog, 'method_name', new_callable=AsyncMock) as mock:
    mock.return_value = test_data
    messages = await invoke_command(bot, "!command", channel)

# Mock aiohttp
from aioresponses import aioresponses
with aioresponses() as m:
    m.get('https://example.com', body='<html>...</html>')
    messages = await invoke_command(bot, "!command", channel)
```

## Troubleshooting

### Common Issues

**Import Errors**
```
ModuleNotFoundError: No module named 'redbot'
```
✅ Fixed: `conftest.py` automatically mocks redbot.core

**Event Loop Errors**
```
RuntimeError: no running event loop
```
✅ Fixed: `conftest.py` patches aiohttp.ClientSession

**Permission Errors**
```
BotMissingPermissions: Bot requires Embed Links
```
✅ Fixed: `invoke_command` sets all permissions

### Test Not Found

If pytest can't find tests:

```bash
# Verify test discovery
python3 -m pytest --collect-only

# Check pytest.ini testpaths
cat pytest.ini
```

### Coverage Issues

If coverage is low:

```bash
# Run with coverage and see what's missing
python3 -m pytest --cov --cov-report=term-missing

# Generate HTML report for detailed view
python3 -m pytest --cov --cov-report=html
open htmlcov/index.html
```

## Visualizing Command Output

Since we can't see actual Discord embeds in the terminal, the framework provides **`print_embed()`** and **`print_embed_list()`** helpers to visualize what commands would output.

### Running Output Tests

```bash
# See simulated output for all cogs
python3 -m pytest tests/integration/ -k "CommandOutput" -v -s

# NFL commands only
python3 -m pytest tests/integration/test_nfl_scraping.py::TestNFLCommandOutput -v -s

# Bristol commands only
python3 -m pytest tests/integration/test_bristol_scraping.py::TestBristolCommandOutput -v -s
```

### Example Output

```
======================================================================
SIMULATED OUTPUT: !nfl team bills
======================================================================

EMBED TITLE: Buffalo Bills - 2025 Season
DESCRIPTION: **13-5, 2nd in AFC East**
----------------------------------------------------------------------

[Playoffs]
2025-26 Playoffs:
WC: 1/11 at 13-4 Jaguars W 27-24 13-5
...

----------------------------------------------------------------------
FOOTER: Data from plaintextsports.com
======================================================================
```

### Using print_embed in Your Tests

```python
from conftest import print_embed, print_embed_list

async def test_my_command_output(self, integration_bot):
    """Simulate !mycommand and print what the embed would show"""
    cog = MyCog(integration_bot)

    try:
        data = await cog.fetch_data()
        embed = cog.build_embed(data)

        # Print single embed
        print_embed(embed, "!mycommand")

        # Or print multiple embeds
        # print_embed_list([embed1, embed2], "!mycommand")

    finally:
        await cog.session.close()
```

**IMPORTANT**: These output visualization tests should be run at the end of every testing cycle to verify command output looks correct.

## Best Practices

1. **Use markers** - Tag tests appropriately (`@pytest.mark.unit`, `@pytest.mark.discord`, etc.)
2. **Mock external calls** - Never hit real APIs in unit/discord tests
3. **Test commands, not methods** - Use the command invocation framework for Discord tests
4. **Keep tests fast** - Unit tests should run in <2 seconds
5. **Clean up resources** - Always close aiohttp sessions in integration tests
6. **Parametrize similar tests** - Use `@pytest.mark.parametrize` for multiple similar cases
7. **Run output tests** - Always run `pytest -k "CommandOutput" -v -s` to visualize output

## Test Coverage Goals

- **Unit Tests**: 80%+ coverage of parsing/formatting logic
- **Discord Tests**: All commands tested with both success and error cases
- **Integration Tests**: Basic smoke tests for live websites

## Contributing New Tests

When adding new cogs:

1. Create unit tests for pure functions in `tests/unit/`
2. Create Discord command tests in `tests/discord/` using the invocation framework
3. Add integration tests in `tests/integration/` if the cog scrapes external data
4. Add sample data fixtures to `tests/fixtures/` if needed
5. Run `python3 -m pytest --cov` to verify coverage

---

**Questions?** Check the examples in existing test files or refer to the plan file: `/Users/nick/.claude/plans/drifting-roaming-sonnet.md`
