import discord
from redbot.core import commands
import sys
import os

# Add parent directory to path for sportslib import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sportslib import BaseSportsCog, SportConfig


class NBAGames(BaseSportsCog):
    """Get upcoming NBA game information from PlainTextSports"""

    def __init__(self, bot):
        config = SportConfig(
            name="NBA",
            slug="nba",
            full_name="National Basketball Association",
            color=0x1D428A,  # NBA blue
            other_leagues=['National Football League', 'National Hockey League',
                          'Major League Baseball', 'Major League Soccer'],
            season_start_month=10  # NBA season starts in October
        )
        super().__init__(bot, config)

    @commands.bot_has_permissions(embed_links=True)
    @commands.group(invoke_without_command=True)
    async def nba(self, ctx):
        """Show NBA games for today

        Subcommands:
          team <name> [year] - Show a team's full season schedule
          today              - Show only today's games
          tomorrow           - Show only tomorrow's games
          <day>              - Show specific day (monday, tuesday, etc.)
        """
        if ctx.invoked_subcommand is None:
            await self.show_games(ctx)

    @commands.bot_has_permissions(embed_links=True)
    @nba.command(name="today")
    async def nba_today(self, ctx):
        """Show only today's NBA games"""
        await self.show_day(ctx, "Today")

    @commands.bot_has_permissions(embed_links=True)
    @nba.command(name="tomorrow")
    async def nba_tomorrow(self, ctx):
        """Show only tomorrow's NBA games"""
        await self.show_day(ctx, "Tomorrow")

    @commands.bot_has_permissions(embed_links=True)
    @nba.command(name="monday")
    async def nba_monday(self, ctx):
        """Show Monday's NBA games"""
        await self.show_day(ctx, "Monday")

    @commands.bot_has_permissions(embed_links=True)
    @nba.command(name="tuesday")
    async def nba_tuesday(self, ctx):
        """Show Tuesday's NBA games"""
        await self.show_day(ctx, "Tuesday")

    @commands.bot_has_permissions(embed_links=True)
    @nba.command(name="wednesday")
    async def nba_wednesday(self, ctx):
        """Show Wednesday's NBA games"""
        await self.show_day(ctx, "Wednesday")

    @commands.bot_has_permissions(embed_links=True)
    @nba.command(name="thursday")
    async def nba_thursday(self, ctx):
        """Show Thursday's NBA games"""
        await self.show_day(ctx, "Thursday")

    @commands.bot_has_permissions(embed_links=True)
    @nba.command(name="friday")
    async def nba_friday(self, ctx):
        """Show Friday's NBA games"""
        await self.show_day(ctx, "Friday")

    @commands.bot_has_permissions(embed_links=True)
    @nba.command(name="saturday")
    async def nba_saturday(self, ctx):
        """Show Saturday's NBA games"""
        await self.show_day(ctx, "Saturday")

    @commands.bot_has_permissions(embed_links=True)
    @nba.command(name="sunday")
    async def nba_sunday(self, ctx):
        """Show Sunday's NBA games"""
        await self.show_day(ctx, "Sunday")

    @commands.bot_has_permissions(embed_links=True)
    @nba.command(name="team")
    async def nba_team(self, ctx, team_name: str, year: int = None):
        """Show a team's full season schedule

        Examples:
            [p]nba team lakers           - Current season
            [p]nba team losangeles 2023  - 2023 season
            [p]nba team lal              - Fuzzy matched
        """
        await self.show_team(ctx, team_name, year)

    @commands.command()
    async def nbatest(self, ctx):
        """Test connection to PlainTextSports for NBA"""
        await self.test_connection(ctx)


async def setup(bot):
    await bot.add_cog(NBAGames(bot))
