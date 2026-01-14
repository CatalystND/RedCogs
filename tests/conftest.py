"""Pytest configuration and shared fixtures for Discord cog testing

This module provides a command invocation framework that works for ANY cog:
- Create a real discord.py Bot with command support
- Mock channels that capture messages
- Load cogs dynamically
- Invoke commands by text and capture output
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch, PropertyMock
import discord
from discord.ext import commands
import importlib
import sys
import os
import aiohttp

# Add parent directory to path for cog imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Mock redbot.core before any cog imports
# The cogs depend on redbot which isn't installed in test environment
if 'redbot' not in sys.modules:

    class MockConfig:
        """Mock Red-Discord Bot Config object that supports async operations"""

        class _ConfigAttr:
            """Helper class for config.attr.set() and config.attr() pattern"""
            def __init__(self, parent, attr_name):
                self.parent = parent
                self.attr_name = attr_name

            async def set(self, value):
                """Set config value"""
                self.parent._data[self.attr_name] = value

            async def __call__(self):
                """Get config value when called as async function"""
                return self.parent._data.get(self.attr_name, {} if self.attr_name == 'team_cache' else None)

        def __init__(self):
            self._data = {}

        def register_global(self, **defaults):
            """Register default config values"""
            for key, value in defaults.items():
                if key not in self._data:
                    self._data[key] = value

        def __setattr__(self, name, value):
            """Set config values"""
            if name.startswith('_'):
                super().__setattr__(name, value)
            else:
                self._data[name] = value

        def __getattr__(self, name):
            """Support both config.attr() and config.attr.set() patterns"""
            if name.startswith('_'):
                return object.__getattribute__(self, name)

            # Return a helper object that supports both () and .set()
            return self._ConfigAttr(self, name)

    class MockConfigClass:
        """Mock Config class that creates MockConfig instances"""
        @staticmethod
        def get_conf(cog, identifier, **kwargs):
            return MockConfig()

    # Create mock redbot module
    redbot_mock = MagicMock()
    redbot_core_mock = MagicMock()

    # Important: use real discord.py commands, not a mock
    redbot_core_mock.commands = commands

    # Use our proper async Config mock
    redbot_core_mock.Config = MockConfigClass

    sys.modules['redbot'] = redbot_mock
    sys.modules['redbot.core'] = redbot_core_mock


@pytest.fixture
def bot():
    """Create a real discord.py Bot instance with command support

    This is a real Bot, not a mock, so it can process commands properly.
    The Discord API connection is mocked, but command processing is real.
    """
    # Mock aiohttp.ClientSession globally so cogs can be instantiated
    # without needing a running event loop
    with patch('aiohttp.ClientSession') as mock_session_class:
        # Create a mock session instance
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        mock_session.get = MagicMock()
        mock_session_class.return_value = mock_session

        # Create a real Bot instance with command prefix
        intents = discord.Intents.default()
        intents.message_content = True
        bot_instance = commands.Bot(command_prefix="!", intents=intents)

        # Mock the _async_setup to prevent actual Discord connection
        bot_instance._async_setup = AsyncMock()

        # Create a mock user for the bot
        bot_user = MagicMock()
        bot_user.id = 123456789
        bot_user.name = "TestBot"
        bot_user.bot = True

        # Patch the user property using PropertyMock
        type(bot_instance).user = PropertyMock(return_value=bot_user)

        # Create a mock loop for the bot
        try:
            bot_instance.loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop in sync tests, create a new one
            bot_instance.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(bot_instance.loop)

        # Store the mock session for access in tests
        bot_instance._mock_session = mock_session

        yield bot_instance


@pytest.fixture
def integration_bot():
    """Create a Bot instance for integration tests that makes REAL HTTP requests

    Unlike the regular 'bot' fixture, this does NOT mock aiohttp.ClientSession,
    allowing integration tests to validate actual web scraping logic.

    Use this fixture for @pytest.mark.integration tests.
    """
    # Create a real Bot instance with command prefix
    intents = discord.Intents.default()
    intents.message_content = True
    bot_instance = commands.Bot(command_prefix="!", intents=intents)

    # Mock the _async_setup to prevent actual Discord connection
    bot_instance._async_setup = AsyncMock()

    # Create a mock user for the bot
    bot_user = MagicMock()
    bot_user.id = 123456789
    bot_user.name = "TestBot"
    bot_user.bot = True

    # Patch the user property using PropertyMock
    type(bot_instance).user = PropertyMock(return_value=bot_user)

    # Create a mock loop for the bot
    try:
        bot_instance.loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop in sync tests, create a new one
        bot_instance.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(bot_instance.loop)

    yield bot_instance


@pytest.fixture
def channel():
    """Create a mock channel that captures all messages sent

    Returns a mock channel with:
    - channel.send() that records messages
    - channel.messages list containing all sent messages
    """
    mock_channel = MagicMock()
    mock_channel.messages = []

    # Create async send function that captures messages
    async def send(content=None, *, embed=None, embeds=None, **kwargs):
        message = MagicMock()
        message.content = content
        message.embed = embed
        message.embeds = embeds or ([embed] if embed else [])
        mock_channel.messages.append(message)
        return message

    mock_channel.send = send
    mock_channel.id = 123456789
    mock_channel.name = "test-channel"

    return mock_channel


@pytest.fixture
def mock_guild():
    """Create a mock guild"""
    guild = MagicMock()
    guild.id = 987654321
    guild.name = "Test Guild"
    guild.me = MagicMock()
    guild.me.guild_permissions = discord.Permissions.all()
    return guild


@pytest.fixture
def mock_author():
    """Create a mock user/author"""
    author = MagicMock()
    author.id = 444555666
    author.name = "TestUser"
    author.display_name = "Test User"
    author.bot = False
    return author


@pytest.fixture
async def load_cog(bot):
    """Helper fixture to dynamically load cogs into the bot

    Usage:
        await load_cog(bot, "nfl.nfl", "NFLGames")
        await load_cog(bot, "bristolMountainConditions.bristolconditions", "BristolConditions")

    Args:
        bot: The bot instance
        module_path: Python module path (e.g., "nfl.nfl")
        cog_class_name: Name of the cog class (e.g., "NFLGames")
    """
    async def _load_cog(bot_instance, module_path, cog_class_name):
        # Import the module
        module = importlib.import_module(module_path)

        # Get the cog class
        cog_class = getattr(module, cog_class_name)

        # Instantiate and add the cog
        cog_instance = cog_class(bot_instance)
        await bot_instance.add_cog(cog_instance)

        return cog_instance

    return _load_cog


@pytest.fixture
async def invoke_command(bot, channel, mock_guild, mock_author):
    """Helper fixture to invoke commands by text and capture output

    This is the key to future-proof testing! It invokes commands exactly
    like Discord would, but captures the output for verification.

    Usage:
        messages = await invoke_command(bot, "!nfl today", channel)
        assert len(messages) == 1
        assert "Today" in messages[0].embed.title

    Args:
        bot: The bot instance with loaded cogs
        command_text: The command text (e.g., "!nfl today")
        channel: The channel to send to

    Returns:
        List of messages sent to the channel
    """
    async def _invoke_command(bot_instance, command_text, target_channel):
        # Create a mock message with the command text
        message = MagicMock()
        message.content = command_text
        message.channel = target_channel
        message.author = mock_author
        message.guild = mock_guild
        message.id = 111222333

        # Ensure channel has permissions_for method
        def permissions_for(member):
            return discord.Permissions.all()

        target_channel.permissions_for = permissions_for

        # Create a context manually if needed
        ctx = await bot_instance.get_context(message)

        # If context has a command, invoke it
        if ctx.command:
            # Override ctx.send to use our channel's send
            ctx.send = target_channel.send

            # Mock ctx.typing() as an async context manager
            typing_cm = AsyncMock()
            typing_cm.__aenter__ = AsyncMock(return_value=None)
            typing_cm.__aexit__ = AsyncMock(return_value=None)
            ctx.typing = MagicMock(return_value=typing_cm)

            # Invoke the command
            await ctx.command.invoke(ctx)
        else:
            # Try processing commands the normal way
            await bot_instance.process_commands(message)

        # Return the captured messages
        return target_channel.messages

    return _invoke_command


# ============================================================================
# Output Visualization Helpers
# ============================================================================

def print_embed(embed, command_name: str = None):
    """Print a Discord embed in a readable terminal format

    Use this to visualize what Discord embeds would look like.
    Works with ANY cog's embed output.

    Args:
        embed: discord.Embed object
        command_name: Optional command name for header (e.g., "!nfl team bills")

    Usage in tests:
        embed = cog.format_some_embed(data)
        print_embed(embed, "!mycommand")
    """
    print("\n" + "=" * 70)
    if command_name:
        print(f"SIMULATED OUTPUT: {command_name}")
        print("=" * 70)

    if embed.title:
        print(f"\nEMBED TITLE: {embed.title}")
    if embed.description:
        print(f"DESCRIPTION: {embed.description}")
    if embed.url:
        print(f"URL: {embed.url}")

    print("-" * 70)

    for field in embed.fields:
        print(f"\n[{field.name}]")
        print(field.value)

    print("-" * 70)

    if embed.footer and embed.footer.text:
        print(f"FOOTER: {embed.footer.text}")

    print("=" * 70 + "\n")


def print_embed_list(embeds: list, command_name: str = None):
    """Print multiple embeds (for commands that send several embeds)"""
    print("\n" + "=" * 70)
    if command_name:
        print(f"SIMULATED OUTPUT: {command_name}")
    print(f"({len(embeds)} embed(s))")
    print("=" * 70)

    for i, embed in enumerate(embeds):
        if len(embeds) > 1:
            print(f"\n--- Embed {i + 1}/{len(embeds)} ---")
        if embed.title:
            print(f"\nEMBED TITLE: {embed.title}")
        if embed.description:
            print(f"DESCRIPTION: {embed.description}")

        for field in embed.fields:
            print(f"\n[{field.name}]")
            print(field.value)

        if embed.footer and embed.footer.text:
            print(f"\nFOOTER: {embed.footer.text}")

    print("\n" + "=" * 70 + "\n")


@pytest.fixture
def print_embed_fixture():
    """Fixture to access print_embed in tests"""
    return print_embed


@pytest.fixture
def print_embed_list_fixture():
    """Fixture to access print_embed_list in tests"""
    return print_embed_list


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_nfl_game_box():
    """Sample NFL game box for parsing tests"""
    return """
    +--------------+
    |  4:30 PM ET |
    | 5 LAR 12-5 |
    | 4 CAR 8-9 |
    +--------- FOX +
    """


@pytest.fixture
def sample_game_data():
    """Sample parsed game data structure"""
    return {
        'time': '4:30 PM ET',
        'away': '5 LAR 12-5',
        'home': '4 CAR 8-9',
        'network': 'FOX'
    }


@pytest.fixture
def sample_nfl_full_response():
    """Sample full NFL data structure from fetch_nfl_games"""
    return {
        'round': 'Wild Card Round',
        'games': {
            'Today': [
                {
                    'time': '4:30 PM ET',
                    'away': '5 LAR 12-5',
                    'home': '4 CAR 8-9',
                    'network': 'FOX'
                },
                {
                    'time': '8:15 PM ET',
                    'away': '6 GB 11-6',
                    'home': '3 PHI 14-3',
                    'network': 'NBC'
                }
            ],
            'Tomorrow': [
                {
                    'time': '1:00 PM ET',
                    'away': '7 PIT 10-7',
                    'home': '2 BUF 13-4',
                    'network': 'CBS'
                }
            ]
        }
    }


@pytest.fixture
def sample_bristol_lifts():
    """Sample Bristol lift data"""
    return [
        {'Name': 'Rocket Lodge', 'Status': 'OPEN'},
        {'Name': 'Galaxy Six', 'Status': 'OPEN'},
        {'Name': 'Comet Express', 'Status': 'CLOSED'}
    ]


@pytest.fixture
def sample_bristol_trails():
    """Sample Bristol trail data"""
    return [
        {
            'Name': 'Upper Rocket',
            'Difficulty': '■ More Difficult',
            'Status': 'OPEN',
            'Conditions': 'Machine Groomed'
        },
        {
            'Name': 'Lower Rocket',
            'Difficulty': '● Easier',
            'Status': 'OPEN',
            'Conditions': 'Packed Powder'
        },
        {
            'Name': 'Expert Chute',
            'Difficulty': '♦♦ Extremely Difficult',
            'Status': 'CLOSED',
            'Conditions': ''
        }
    ]


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()
