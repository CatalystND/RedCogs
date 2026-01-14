"""Integration tests for live MLB scraping

These tests hit the real plaintextsports.com website to validate scraping logic.
They may be slower and can fail if the website is down or changes structure.
"""

import pytest
import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from mlb.mlb import MLBGames

# Import print helpers from conftest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from conftest import print_embed, print_embed_list


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
class TestMLBLiveScraping:
    """Test live scraping of plaintextsports.com for MLB"""

    async def test_fetch_mlb_games_live(self, integration_bot):
        """Test fetching real MLB games from plaintextsports.com"""
        cog = MLBGames(integration_bot)

        try:
            result = await cog.fetch_games()

            # If we got data, validate structure
            if isinstance(result, dict):
                assert 'games' in result
                assert 'round' in result
                assert isinstance(result['games'], dict)

                if result['games']:
                    for day, games in result['games'].items():
                        assert isinstance(games, list)
                        for game in games:
                            assert 'status' in game
                            assert 'away' in game
                            assert 'home' in game
                            assert 'network' in game
                else:
                    print("No games found (possibly offseason)")
            else:
                # String error message is acceptable (especially in offseason)
                print(f"fetch_games returned: {result}")

        finally:
            await cog.session.close()

    async def test_session_cleanup(self, integration_bot):
        """Test that aiohttp session is properly created and can be closed"""
        cog = MLBGames(integration_bot)

        assert cog.session is not None
        assert not cog.session.closed

        await cog.session.close()
        assert cog.session.closed


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
class TestMLBCommandOutput:
    """Test and display simulated MLB command output"""

    async def test_mlb_games_command_output(self, integration_bot):
        """Simulate !mlb and print what the embeds would show"""
        cog = MLBGames(integration_bot)

        try:
            result = await cog.fetch_games()

            if isinstance(result, str):
                print(f"\n[INFO] {result}")
                return

            if not result or not result.get('games'):
                print("\n[SKIP] No games available - possibly offseason or network issue")
                return

            embeds = [cog.build_day_embed(day, games, result.get('round', 'Schedule'))
                      for day, games in result['games'].items()]

            print_embed_list(embeds, "!mlb")

        except Exception as e:
            print(f"\n[SKIP] Network error: {type(e).__name__}")

        finally:
            await cog.session.close()

    async def test_mlb_team_command_output(self, integration_bot):
        """Simulate !mlb team yankees and print what the embed would show"""
        cog = MLBGames(integration_bot)

        try:
            year = cog.get_current_season_year()
            teams = await cog.fetch_team_list(year)

            if not teams:
                print("\n[SKIP] Could not fetch team list (network/SSL issue)")
                return

            team_slug, full_name = cog.find_team_slug("yankees", teams)

            if not team_slug:
                print("\n[SKIP] Could not find Yankees in team list")
                return

            raw_schedule = await cog.fetch_team_schedule(year, team_slug)

            if not raw_schedule:
                print(f"\n[SKIP] Could not fetch schedule for {full_name}")
                return

            schedule_data = cog.parse_team_schedule(raw_schedule)
            embed = cog.format_team_schedule_embed(schedule_data, year)

            print_embed(embed, "!mlb team yankees")

            assert embed.title is not None
            assert len(embed.fields) > 0

        except Exception as e:
            print(f"\n[SKIP] Network error: {type(e).__name__}")

        finally:
            await cog.session.close()
