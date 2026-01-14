import discord
from redbot.core import commands
import sys
import os

# Add parent directory to path for sportslib import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sportslib import BaseSportsCog, SportConfig


class MLBGames(BaseSportsCog):
    """Get upcoming MLB game information from PlainTextSports"""

    def __init__(self, bot):
        config = SportConfig(
            name="MLB",
            slug="mlb",
            full_name="Major League Baseball",
            color=0x002D72,  # MLB blue
            other_leagues=['National Football League', 'National Basketball',
                          'National Hockey League', 'Major League Soccer'],
            season_start_month=3  # MLB season starts in March/April
        )
        super().__init__(bot, config)

    @commands.bot_has_permissions(embed_links=True)
    @commands.group(invoke_without_command=True)
    async def mlb(self, ctx):
        """Show MLB games for today

        Subcommands:
          team <name> [year] - Show a team's full season schedule
          today              - Show only today's games
          tomorrow           - Show only tomorrow's games
          <day>              - Show specific day (monday, tuesday, etc.)
        """
        if ctx.invoked_subcommand is None:
            await self.show_games(ctx)

    @commands.bot_has_permissions(embed_links=True)
    @mlb.command(name="today")
    async def mlb_today(self, ctx):
        """Show only today's MLB games"""
        await self.show_day(ctx, "Today")

    @commands.bot_has_permissions(embed_links=True)
    @mlb.command(name="tomorrow")
    async def mlb_tomorrow(self, ctx):
        """Show only tomorrow's MLB games"""
        await self.show_day(ctx, "Tomorrow")

    @commands.bot_has_permissions(embed_links=True)
    @mlb.command(name="monday")
    async def mlb_monday(self, ctx):
        """Show Monday's MLB games"""
        await self.show_day(ctx, "Monday")

    @commands.bot_has_permissions(embed_links=True)
    @mlb.command(name="tuesday")
    async def mlb_tuesday(self, ctx):
        """Show Tuesday's MLB games"""
        await self.show_day(ctx, "Tuesday")

    @commands.bot_has_permissions(embed_links=True)
    @mlb.command(name="wednesday")
    async def mlb_wednesday(self, ctx):
        """Show Wednesday's MLB games"""
        await self.show_day(ctx, "Wednesday")

    @commands.bot_has_permissions(embed_links=True)
    @mlb.command(name="thursday")
    async def mlb_thursday(self, ctx):
        """Show Thursday's MLB games"""
        await self.show_day(ctx, "Thursday")

    @commands.bot_has_permissions(embed_links=True)
    @mlb.command(name="friday")
    async def mlb_friday(self, ctx):
        """Show Friday's MLB games"""
        await self.show_day(ctx, "Friday")

    @commands.bot_has_permissions(embed_links=True)
    @mlb.command(name="saturday")
    async def mlb_saturday(self, ctx):
        """Show Saturday's MLB games"""
        await self.show_day(ctx, "Saturday")

    @commands.bot_has_permissions(embed_links=True)
    @mlb.command(name="sunday")
    async def mlb_sunday(self, ctx):
        """Show Sunday's MLB games"""
        await self.show_day(ctx, "Sunday")

    @commands.bot_has_permissions(embed_links=True)
    @mlb.command(name="team")
    async def mlb_team(self, ctx, team_name: str, year: int = None):
        """Show a team's full season schedule

        Examples:
            [p]mlb team yankees          - Current season
            [p]mlb team newyork 2023     - 2023 season
            [p]mlb team nyy              - Fuzzy matched
        """
        await self.show_team(ctx, team_name, year)

    @commands.command()
    async def mlbtest(self, ctx):
        """Test connection to PlainTextSports for MLB"""
        await self.test_connection(ctx)


async def setup(bot):
    await bot.add_cog(MLBGames(bot))
