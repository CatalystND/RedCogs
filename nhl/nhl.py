import discord
from redbot.core import commands
import sys
import os

# Add parent directory to path for sportslib import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sportslib import BaseSportsCog, SportConfig


class NHLGames(BaseSportsCog):
    """Get upcoming NHL game information from PlainTextSports"""

    def __init__(self, bot):
        config = SportConfig(
            name="NHL",
            slug="nhl",
            full_name="National Hockey League",
            color=0x002D62,  # NHL dark blue
            other_leagues=['National Football League', 'National Basketball',
                          'Major League Baseball', 'Major League Soccer'],
            season_start_month=9  # NHL season starts in October, use September
        )
        super().__init__(bot, config)

    @commands.bot_has_permissions(embed_links=True)
    @commands.group(invoke_without_command=True)
    async def nhl(self, ctx):
        """Show NHL games for today

        Subcommands:
          team <name> [year] - Show a team's full season schedule
          today              - Show only today's games
          tomorrow           - Show only tomorrow's games
          <day>              - Show specific day (monday, tuesday, etc.)
        """
        if ctx.invoked_subcommand is None:
            await self.show_games(ctx)

    @commands.bot_has_permissions(embed_links=True)
    @nhl.command(name="today")
    async def nhl_today(self, ctx):
        """Show only today's NHL games"""
        await self.show_day(ctx, "Today")

    @commands.bot_has_permissions(embed_links=True)
    @nhl.command(name="tomorrow")
    async def nhl_tomorrow(self, ctx):
        """Show only tomorrow's NHL games"""
        await self.show_day(ctx, "Tomorrow")

    @commands.bot_has_permissions(embed_links=True)
    @nhl.command(name="monday")
    async def nhl_monday(self, ctx):
        """Show Monday's NHL games"""
        await self.show_day(ctx, "Monday")

    @commands.bot_has_permissions(embed_links=True)
    @nhl.command(name="tuesday")
    async def nhl_tuesday(self, ctx):
        """Show Tuesday's NHL games"""
        await self.show_day(ctx, "Tuesday")

    @commands.bot_has_permissions(embed_links=True)
    @nhl.command(name="wednesday")
    async def nhl_wednesday(self, ctx):
        """Show Wednesday's NHL games"""
        await self.show_day(ctx, "Wednesday")

    @commands.bot_has_permissions(embed_links=True)
    @nhl.command(name="thursday")
    async def nhl_thursday(self, ctx):
        """Show Thursday's NHL games"""
        await self.show_day(ctx, "Thursday")

    @commands.bot_has_permissions(embed_links=True)
    @nhl.command(name="friday")
    async def nhl_friday(self, ctx):
        """Show Friday's NHL games"""
        await self.show_day(ctx, "Friday")

    @commands.bot_has_permissions(embed_links=True)
    @nhl.command(name="saturday")
    async def nhl_saturday(self, ctx):
        """Show Saturday's NHL games"""
        await self.show_day(ctx, "Saturday")

    @commands.bot_has_permissions(embed_links=True)
    @nhl.command(name="sunday")
    async def nhl_sunday(self, ctx):
        """Show Sunday's NHL games"""
        await self.show_day(ctx, "Sunday")

    @commands.bot_has_permissions(embed_links=True)
    @nhl.command(name="team")
    async def nhl_team(self, ctx, team_name: str, year: int = None):
        """Show a team's full season schedule

        Examples:
            [p]nhl team bruins           - Current season
            [p]nhl team boston 2023      - 2023 season
            [p]nhl team bostonbruins     - Fuzzy matched
        """
        await self.show_team(ctx, team_name, year)

    @commands.command()
    async def nhltest(self, ctx):
        """Test connection to PlainTextSports for NHL"""
        await self.test_connection(ctx)


async def setup(bot):
    await bot.add_cog(NHLGames(bot))
