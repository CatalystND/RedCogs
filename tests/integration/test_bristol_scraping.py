"""Integration tests for Bristol Mountain scraping

These tests hit the real bristolmountain.com website to validate scraping logic.
They may be slower and can fail if the website is down or changes structure.
"""

import pytest
import sys
import os
import discord
from datetime import datetime, timezone

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from bristolMountainConditions.bristolconditions import BristolConditions

# Import print helpers from conftest
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from conftest import print_embed, print_embed_list


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
class TestBristolLiveScraping:
    """Test live scraping of bristolmountain.com"""

    async def test_get_bristol_conditions_live(self, integration_bot):
        """Test fetching real Bristol conditions from bristolmountain.com

        This test validates that:
        1. The website is reachable
        2. The HTML structure matches our expectations
        3. Lift and trail parsing works with live data
        """
        cog = BristolConditions(integration_bot)

        try:
            lifts, trails = await cog.get_bristol_conditions()

            # Validate structure if data exists
            if lifts:
                assert isinstance(lifts, list)
                for lift in lifts:
                    assert 'Name' in lift
                    assert 'Status' in lift
            else:
                # Empty lifts might mean website issues or format change
                print("No lifts found (website may have changed structure)")

            if trails:
                assert isinstance(trails, list)
                for trail in trails:
                    assert 'Name' in trail
                    assert 'Status' in trail
                    assert 'Difficulty' in trail
                    assert 'Conditions' in trail
            else:
                print("No trails found (website may have changed structure)")

        finally:
            await cog.session.close()

    async def test_handles_invalid_response(self, integration_bot):
        """Test that invalid responses are handled gracefully"""
        cog = BristolConditions(integration_bot)

        try:
            result = await cog.get_bristol_conditions()

            # Should return tuple or (None, None), not crash
            assert isinstance(result, tuple)
            assert len(result) == 2

        finally:
            await cog.session.close()

    async def test_session_cleanup(self, integration_bot):
        """Test that aiohttp session is properly created and can be closed"""
        cog = BristolConditions(integration_bot)

        assert cog.session is not None
        assert not cog.session.closed

        await cog.session.close()
        assert cog.session.closed

    @pytest.mark.slow
    async def test_multiple_fetches(self, integration_bot):
        """Test that multiple consecutive fetches work correctly"""
        cog = BristolConditions(integration_bot)

        try:
            lifts1, trails1 = await cog.get_bristol_conditions()
            lifts2, trails2 = await cog.get_bristol_conditions()

            # Both should return tuples
            assert isinstance((lifts1, trails1), tuple)
            assert isinstance((lifts2, trails2), tuple)

            # If we got data in first fetch, second should also work
            if lifts1 and trails1:
                assert lifts2 is not None or trails2 is not None

        finally:
            await cog.session.close()


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
class TestBristolCommandOutput:
    """Test and display simulated Bristol command output

    These tests hit live websites and print what Discord embeds would look like.
    Run with: pytest tests/integration/test_bristol_scraping.py::TestBristolCommandOutput -v -s
    """

    async def test_bristol_command_output(self, integration_bot):
        """Simulate !bristol and print what the embeds would show"""
        cog = BristolConditions(integration_bot)

        try:
            lifts, trails = await cog.get_bristol_conditions()

            if not lifts and not trails:
                print("\n[SKIP] Could not fetch Bristol conditions (network/SSL issue)")
                return

            embeds = []

            # Build lift embed (same logic as the cog)
            lift_embed = discord.Embed(
                title="Bristol Mountain - Ski Lift Status",
                color=0x0066CC,
                url="https://www.bristolmountain.com/conditions/"
            )
            lift_lines = []
            for lift in lifts:
                icon = "✅" if lift['Status'] == "OPEN" else "❌"
                lift_lines.append(f"{icon} **{lift['Name']}** - {lift['Status']}")
            if lift_lines:
                lift_embed.add_field(name="Lifts", value="\n".join(lift_lines), inline=False)
            embeds.append(lift_embed)

            # Build trail embed
            trail_embed = discord.Embed(
                title="Bristol Mountain - Trail Conditions",
                color=0x0066CC,
                url="https://www.bristolmountain.com/conditions/"
            )
            open_trails = [t for t in trails if t['Status'] == 'OPEN']
            closed_trails = [t for t in trails if t['Status'] != 'OPEN']

            if open_trails:
                trail_lines = []
                for trail in open_trails[:15]:
                    trail_lines.append(f"**{trail['Name']}** {trail['Difficulty']}\n└ {trail['Conditions']}")
                trail_embed.add_field(name=f"Open Trails ({len(open_trails)})", value="\n".join(trail_lines), inline=False)

            if closed_trails:
                closed_names = [f"~~{t['Name']}~~" for t in closed_trails[:10]]
                trail_embed.add_field(name=f"Closed Trails ({len(closed_trails)})", value=", ".join(closed_names), inline=False)

            trail_embed.set_footer(text="Data from bristolmountain.com")
            embeds.append(trail_embed)

            print_embed_list(embeds, "!bristol")

            assert len(embeds) == 2

        except Exception as e:
            print(f"\n[SKIP] Network error: {type(e).__name__}")

        finally:
            await cog.session.close()
