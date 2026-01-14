"""Discord command tests for Bristol cog

These tests use the command invocation framework - same pattern as NFL tests!
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
class TestBristolCommands:
    """Test Bristol Discord command functionality using command invocation"""

    async def test_bristol_command(self, bot, channel, load_cog, sample_bristol_lifts, sample_bristol_trails, invoke_command):
        """Test !bristol command shows lift and trail conditions"""
        # Load the cog
        await load_cog(bot, "bristolMountainConditions.bristolconditions", "BristolConditions")

        # Mock the web scraping
        cog = bot.get_cog("BristolConditions")
        with patch.object(cog, 'get_bristol_conditions', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (sample_bristol_lifts, sample_bristol_trails)

            # Invoke command (same pattern as NFL!)
            messages = await invoke_command(bot, "!bristol", channel)

            # Verify 2 embeds sent (lifts and trails)
            assert len(messages) == 2

            # Verify lift embed
            lift_embed = messages[0].embed
            assert isinstance(lift_embed, discord.Embed)
            assert "Lift Status" in lift_embed.title
            assert lift_embed.color.value == 0x0066CC
            assert lift_embed.url == "https://www.bristolmountain.com/conditions/"

            # Verify trail embed
            trail_embed = messages[1].embed
            assert "Trail Conditions" in trail_embed.title
            assert trail_embed.footer.text == "Data from bristolmountain.com"

    async def test_bristol_two_embeds(self, bot, channel, load_cog, sample_bristol_lifts, sample_bristol_trails, invoke_command):
        """Test that exactly 2 embeds are sent"""
        await load_cog(bot, "bristolMountainConditions.bristolconditions", "BristolConditions")

        cog = bot.get_cog("BristolConditions")
        with patch.object(cog, 'get_bristol_conditions', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (sample_bristol_lifts, sample_bristol_trails)

            messages = await invoke_command(bot, "!bristol", channel)

            assert len(messages) == 2
            assert all(hasattr(msg, 'embed') and msg.embed for msg in messages)

    async def test_bristol_no_data(self, bot, channel, load_cog, invoke_command):
        """Test error handling when no data is available"""
        await load_cog(bot, "bristolMountainConditions.bristolconditions", "BristolConditions")

        cog = bot.get_cog("BristolConditions")
        with patch.object(cog, 'get_bristol_conditions', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (None, None)

            messages = await invoke_command(bot, "!bristol", channel)

            assert len(messages) >= 1
            assert "Could not fetch" in messages[0].content

    async def test_bristol_lift_status_icons(self, bot, channel, load_cog, sample_bristol_lifts, sample_bristol_trails, invoke_command):
        """Test that lift status icons (✅/❌) are displayed"""
        await load_cog(bot, "bristolMountainConditions.bristolconditions", "BristolConditions")

        cog = bot.get_cog("BristolConditions")
        with patch.object(cog, 'get_bristol_conditions', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (sample_bristol_lifts, sample_bristol_trails)

            messages = await invoke_command(bot, "!bristol", channel)

            lift_embed = messages[0].embed
            field_value = lift_embed.fields[0].value

            # Check for status icons
            assert '✅' in field_value or '❌' in field_value
            assert 'Rocket Lodge' in field_value

    async def test_bristol_trail_grouping(self, bot, channel, load_cog, sample_bristol_lifts, sample_bristol_trails, invoke_command):
        """Test that trails are grouped by open/closed status"""
        await load_cog(bot, "bristolMountainConditions.bristolconditions", "BristolConditions")

        cog = bot.get_cog("BristolConditions")
        with patch.object(cog, 'get_bristol_conditions', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (sample_bristol_lifts, sample_bristol_trails)

            messages = await invoke_command(bot, "!bristol", channel)

            trail_embed = messages[1].embed

            # Should have both open and closed trail fields
            field_names = [f.name for f in trail_embed.fields]
            assert any('Open' in name for name in field_names)
            assert any('Closed' in name for name in field_names)

    async def test_bristol_embed_structure(self, bot, channel, load_cog, sample_bristol_lifts, sample_bristol_trails, invoke_command):
        """Test that embeds have correct structure"""
        await load_cog(bot, "bristolMountainConditions.bristolconditions", "BristolConditions")

        cog = bot.get_cog("BristolConditions")
        with patch.object(cog, 'get_bristol_conditions', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = (sample_bristol_lifts, sample_bristol_trails)

            messages = await invoke_command(bot, "!bristol", channel)

            # Verify lift embed structure
            lift_embed = messages[0].embed
            assert isinstance(lift_embed, discord.Embed)
            assert lift_embed.color.value == 0x0066CC
            assert len(lift_embed.fields) > 0

            # Verify trail embed structure
            trail_embed = messages[1].embed
            assert isinstance(trail_embed, discord.Embed)
            assert trail_embed.color.value == 0x0066CC
            assert len(trail_embed.fields) > 0

    async def test_bristol_empty_lifts(self, bot, channel, load_cog, sample_bristol_trails, invoke_command):
        """Test handling when lift data is empty but trails exist"""
        await load_cog(bot, "bristolMountainConditions.bristolconditions", "BristolConditions")

        cog = bot.get_cog("BristolConditions")
        with patch.object(cog, 'get_bristol_conditions', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = ([], sample_bristol_trails)

            messages = await invoke_command(bot, "!bristol", channel)

            # Should still send error message if lifts are empty
            assert len(messages) >= 1
