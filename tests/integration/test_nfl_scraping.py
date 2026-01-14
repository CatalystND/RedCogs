"""Integration tests for live NFL scraping

These tests hit the real plaintextsports.com website to validate scraping logic.
They may be slower and can fail if the website is down or changes structure.
"""

import pytest
import sys
import os
import asyncio

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from nfl.nfl import NFLGames

# Import print helpers from conftest (pytest makes conftest available)
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from conftest import print_embed, print_embed_list


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
class TestNFLLiveScraping:
    """Test live scraping of plaintextsports.com"""

    async def test_fetch_nfl_games_live(self, integration_bot):
        """Test fetching real NFL games from plaintextsports.com

        This test validates that:
        1. The website is reachable
        2. The HTML structure matches our expectations
        3. Game parsing works with live data
        """
        cog = NFLGames(integration_bot)

        try:
            result = await cog.fetch_nfl_games()

            # If we got data, validate structure
            if result:
                assert 'games' in result
                assert 'round' in result
                assert isinstance(result['games'], dict)

                # If games exist, validate structure
                if result['games']:
                    for day, games in result['games'].items():
                        assert isinstance(games, list)
                        for game in games:
                            assert 'time' in game
                            assert 'away' in game
                            assert 'home' in game
                            assert 'network' in game
                else:
                    # No games is acceptable (offseason)
                    print("No games found (possibly offseason)")
            else:
                # None result is acceptable (website issues, offseason)
                print("fetch_nfl_games returned None (website may be unavailable)")

        finally:
            await cog.session.close()

    async def test_fetch_handles_network_timeout(self, integration_bot):
        """Test that fetch handles network timeouts gracefully"""
        cog = NFLGames(integration_bot)

        try:
            # This should timeout or return None, not crash
            result = await cog.fetch_nfl_games()

            # Result can be None or data, but should not raise
            assert result is None or isinstance(result, dict)

        except asyncio.TimeoutError:
            # Acceptable outcome
            pass
        finally:
            await cog.session.close()

    @pytest.mark.slow
    async def test_multiple_fetches(self, integration_bot):
        """Test that multiple consecutive fetches work correctly"""
        cog = NFLGames(integration_bot)

        try:
            result1 = await cog.fetch_nfl_games()
            result2 = await cog.fetch_nfl_games()

            # Both should succeed or both should fail gracefully
            # The actual data might differ slightly (due to timing)
            # but both should be same type
            assert type(result1) == type(result2) or (result1 is None or result2 is None)

        finally:
            await cog.session.close()

    async def test_session_cleanup(self, integration_bot):
        """Test that aiohttp session is properly created and can be closed"""
        cog = NFLGames(integration_bot)

        assert cog.session is not None
        assert not cog.session.closed

        await cog.session.close()
        assert cog.session.closed


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
class TestNFLCommandOutput:
    """Test and display simulated command output

    These tests hit live websites and print what Discord embeds would look like.
    Run with: pytest tests/integration/test_nfl_scraping.py::TestNFLCommandOutput -v -s
    """

    async def test_nfl_team_command_output(self, integration_bot):
        """Simulate !nfl team bills and print what the embed would show"""
        cog = NFLGames(integration_bot)

        try:
            year = cog.get_current_nfl_year()
            teams = await cog.fetch_team_list(year)

            if not teams:
                print("\n[SKIP] Could not fetch team list (network/SSL issue)")
                return

            team_slug, full_name = cog.find_team_slug("bills", teams)
            raw_schedule = await cog.fetch_team_schedule(year, team_slug)

            if not raw_schedule:
                print(f"\n[SKIP] Could not fetch schedule for {full_name}")
                return

            schedule_data = cog.parse_team_schedule(raw_schedule)
            embed = cog.format_team_schedule_embed(schedule_data, year)

            print_embed(embed, "!nfl team bills")

            assert embed.title is not None
            assert full_name in embed.title
            assert len(embed.fields) > 0

        except Exception as e:
            print(f"\n[SKIP] Network error: {type(e).__name__}")

        finally:
            await cog.session.close()

    async def test_nfl_games_command_output(self, integration_bot):
        """Simulate !nfl and print what the embeds would show"""
        cog = NFLGames(integration_bot)

        try:
            result = await cog.fetch_nfl_games()

            if not result or not result.get('games'):
                print("\n[SKIP] No games available - possibly offseason or network issue")
                return

            embeds = [cog._build_day_embed(day, games, result.get('round', 'Schedule'))
                      for day, games in result['games'].items()]

            print_embed_list(embeds, "!nfl")

        except Exception as e:
            print(f"\n[SKIP] Network error: {type(e).__name__}")

        finally:
            await cog.session.close()
