"""Discord command tests for NFL cog

These tests use the command invocation framework to test the full command flow.
This pattern works for ANY cog - completely future-proof!
"""

import pytest
import sys
import os
from unittest.mock import patch, AsyncMock
import discord

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


@pytest.mark.discord
@pytest.mark.asyncio
class TestNFLCommands:
    """Test NFL Discord command functionality using command invocation"""

    async def test_nfl_command_no_args(self, bot, channel, load_cog, sample_nfl_full_response, invoke_command):
        """Test !nfl command shows all games"""
        await load_cog(bot, "nfl.nfl", "NFLGames")

        cog = bot.get_cog("NFLGames")
        with patch.object(cog, 'fetch_nfl_games', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_nfl_full_response

            messages = await invoke_command(bot, "!nfl", channel)

            assert len(messages) >= 1
            assert all(hasattr(msg, 'embed') and msg.embed for msg in messages)

            first_embed = messages[0].embed
            assert "NFL Games" in first_embed.title
            assert first_embed.color.value == 0x013369

    async def test_nfl_today_command(self, bot, channel, load_cog, sample_nfl_full_response, invoke_command):
        """Test !nfl today command shows only today's games"""
        await load_cog(bot, "nfl.nfl", "NFLGames")

        cog = bot.get_cog("NFLGames")
        with patch.object(cog, 'fetch_nfl_games', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_nfl_full_response

            messages = await invoke_command(bot, "!nfl today", channel)

            assert len(messages) >= 1
            assert messages[0].embed.title == "NFL Games - Today"

    async def test_nfl_tomorrow_command(self, bot, channel, load_cog, sample_nfl_full_response, invoke_command):
        """Test !nfl tomorrow command"""
        await load_cog(bot, "nfl.nfl", "NFLGames")

        cog = bot.get_cog("NFLGames")
        with patch.object(cog, 'fetch_nfl_games', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_nfl_full_response

            messages = await invoke_command(bot, "!nfl tomorrow", channel)

            assert len(messages) >= 1
            assert messages[0].embed.title == "NFL Games - Tomorrow"

    async def test_nfl_specific_day_command(self, bot, channel, load_cog, invoke_command):
        """Test !nfl monday, !nfl sunday, etc."""
        await load_cog(bot, "nfl.nfl", "NFLGames")

        cog = bot.get_cog("NFLGames")
        sample_data = {
            'round': 'Week 18',
            'games': {
                'Sunday': [
                    {
                        'time': '1:00 PM ET',
                        'away': 'KC 15-2',
                        'home': 'DEN 9-8',
                        'network': 'CBS'
                    }
                ]
            }
        }

        with patch.object(cog, 'fetch_nfl_games', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_data

            messages = await invoke_command(bot, "!nfl sunday", channel)

            assert len(messages) >= 1
            assert messages[0].embed.title == "NFL Games - Sunday"

    async def test_nfl_no_games_message(self, bot, channel, load_cog, invoke_command):
        """Test 'No games' message when day has no games"""
        await load_cog(bot, "nfl.nfl", "NFLGames")

        cog = bot.get_cog("NFLGames")
        sample_data = {
            'round': 'Week 18',
            'games': {
                'Sunday': [
                    {
                        'time': '1:00 PM ET',
                        'away': 'KC 15-2',
                        'home': 'DEN 9-8',
                        'network': 'CBS'
                    }
                ]
            }
        }

        with patch.object(cog, 'fetch_nfl_games', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_data

            # Request a day with no games
            messages = await invoke_command(bot, "!nfl monday", channel)

            assert len(messages) >= 1
            assert "No NFL games" in messages[0].content

    async def test_nfl_no_data_error(self, bot, channel, load_cog, invoke_command):
        """Test error handling when fetch returns None"""
        await load_cog(bot, "nfl.nfl", "NFLGames")

        cog = bot.get_cog("NFLGames")
        with patch.object(cog, 'fetch_nfl_games', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None

            messages = await invoke_command(bot, "!nfl", channel)

            assert len(messages) >= 1
            assert "Could not fetch" in messages[0].content

    async def test_nfl_embed_structure(self, bot, channel, load_cog, sample_nfl_full_response, invoke_command):
        """Test that embed has correct structure"""
        await load_cog(bot, "nfl.nfl", "NFLGames")

        cog = bot.get_cog("NFLGames")
        with patch.object(cog, 'fetch_nfl_games', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = sample_nfl_full_response

            messages = await invoke_command(bot, "!nfl today", channel)

            embed = messages[0].embed
            assert isinstance(embed, discord.Embed)
            assert embed.color.value == 0x013369
            assert "Wild Card Round" in embed.description
            assert embed.footer.text == "Data from plaintextsports.com"
            assert len(embed.fields) > 0


@pytest.mark.discord
@pytest.mark.asyncio
class TestNFLTestCommand:
    """Test nfltest command"""

    async def test_nfltest_command(self, bot, channel, load_cog, invoke_command):
        """Test !nfltest connectivity check"""
        await load_cog(bot, "nfl.nfl", "NFLGames")

        cog = bot.get_cog("NFLGames")

        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='<html>Test</html>')

        with patch.object(cog.session, 'get') as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_response

            messages = await invoke_command(bot, "!nfltest", channel)

            assert len(messages) >= 1
            assert "200" in messages[0].content
            assert "plaintextsports.com" in messages[0].content
