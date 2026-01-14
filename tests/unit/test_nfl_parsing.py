"""Unit tests for NFL parsing functions

These tests verify the pure parsing logic without any I/O or Discord interaction.
"""

import pytest
import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from nfl.nfl import NFLGames


@pytest.mark.unit
class TestParseGameBox:
    """Test parse_game_box function with various inputs"""

    def test_parse_standard_game_box(self, bot):
        """Test parsing a standard game box with all fields"""
        cog = NFLGames(bot)
        game_box = """
        +--------------+
        |  4:30 PM ET |
        | 5 LAR 12-5 |
        | 4 CAR 8-9 |
        +--------- FOX +
        """

        result = cog.parse_game_box(game_box)

        assert result is not None
        assert result['time'] == '4:30 PM ET'
        assert result['away'] == '5 LAR 12-5'
        assert result['home'] == '4 CAR 8-9'
        assert result['network'] == 'FOX'

    def test_parse_game_box_no_network(self, bot):
        """Test parsing game box without network"""
        cog = NFLGames(bot)
        game_box = """
        +--------------+
        |  1:00 PM ET |
        | KC 14-3 |
        | BUF 13-4 |
        +--------------+
        """

        result = cog.parse_game_box(game_box)

        assert result is not None
        assert result['time'] == '1:00 PM ET'
        assert result['away'] == 'KC 14-3'
        assert result['home'] == 'BUF 13-4'
        assert result['network'] == ''

    def test_parse_game_box_no_seeds(self, bot):
        """Test parsing game box without playoff seeds"""
        cog = NFLGames(bot)
        game_box = """
        +--------------+
        |  4:25 PM ET |
        | DAL 12-5 |
        | SF 13-4 |
        +------- CBS +
        """

        result = cog.parse_game_box(game_box)

        assert result is not None
        assert result['time'] == '4:25 PM ET'
        assert result['away'] == 'DAL 12-5'
        assert result['home'] == 'SF 13-4'
        assert result['network'] == 'CBS'

    def test_parse_malformed_box(self, bot):
        """Test parsing malformed box returns None"""
        cog = NFLGames(bot)
        malformed = "+-+ BROKEN +-+"

        result = cog.parse_game_box(malformed)

        assert result is None

    def test_parse_empty_string(self, bot):
        """Test parsing empty string returns None"""
        cog = NFLGames(bot)

        result = cog.parse_game_box("")

        assert result is None

    def test_parse_incomplete_box(self, bot):
        """Test parsing box with missing lines returns None"""
        cog = NFLGames(bot)
        incomplete = """
        +--------------+
        |  4:30 PM ET |
        +--------------+
        """

        result = cog.parse_game_box(incomplete)

        assert result is None


@pytest.mark.unit
class TestFormatTeamInfo:
    """Test format_team_info function"""

    def test_format_with_seed(self, bot):
        """Test formatting team info with playoff seed"""
        cog = NFLGames(bot)

        result = cog.format_team_info("5 LAR 12-5")

        assert result == "**LAR** *(12-5)*"

    def test_format_without_seed(self, bot):
        """Test formatting team info without seed"""
        cog = NFLGames(bot)

        result = cog.format_team_info("DAL 12-5")

        assert result == "**DAL** *(12-5)*"

    def test_format_single_digit_seed(self, bot):
        """Test formatting with single digit seed"""
        cog = NFLGames(bot)

        result = cog.format_team_info("1 KC 15-2")

        assert result == "**KC** *(15-2)*"

    def test_format_edge_case_single_part(self, bot):
        """Test formatting with unexpected single part"""
        cog = NFLGames(bot)

        result = cog.format_team_info("TEAM")

        assert result == "TEAM"  # Fallback

    @pytest.mark.parametrize("team_str,expected", [
        ("1 KC 15-2", "**KC** *(15-2)*"),
        ("DEN 9-8", "**DEN** *(9-8)*"),
        ("7 GB 11-6", "**GB** *(11-6)*"),
        ("2 BUF 13-4", "**BUF** *(13-4)*"),
        ("SF 14-3", "**SF** *(14-3)*"),
    ])
    def test_format_multiple_cases(self, bot, team_str, expected):
        """Test multiple team formatting cases"""
        cog = NFLGames(bot)

        result = cog.format_team_info(team_str)

        assert result == expected
