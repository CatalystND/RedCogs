import discord
from redbot.core import commands, Config
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import re
from typing import List, Dict

class NFLGames(commands.Cog):
    """Get upcoming NFL game information from PlainTextSports"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(self, identifier=1234567890)
        
    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        self.bot.loop.create_task(self.session.close())

    def parse_game_box(self, text: str) -> Dict:
        """Parse a game box text into structured data
        
        Format:
        +--------------+
        |  4:30 PM ET |
        | 5 LAR 12-5 |
        | 4 CAR 8-9 |
        +--------- FOX +
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Remove the box drawing characters and plus signs
        cleaned_lines = []
        for line in lines:
            # Remove leading/trailing + and |
            cleaned = line.strip('+ |')
            if cleaned and not all(c in '+-' for c in cleaned):
                cleaned_lines.append(cleaned)
        
        if len(cleaned_lines) < 3:
            return None
        
        # Clean up network by removing dashes
        network = ''
        if len(cleaned_lines) > 3:
            network = cleaned_lines[3].strip().replace('-', '').strip()
        
        game_data = {
            'time': cleaned_lines[0].strip(),
            'away': cleaned_lines[1].strip(),
            'home': cleaned_lines[2].strip(),
            'network': network
        }
        
        return game_data

    def format_team_info(self, team_str: str) -> str:
        """Format team string to make team name stand out
        
        Input: '5 LAR 12-5'
        Output: '**LAR** *(12-5)*'
        """
        parts = team_str.split()
        
        if len(parts) == 3:
            # Format: seed team record
            seed, team, record = parts
            return f"**{team}** *({record})*"
        elif len(parts) == 2:
            # Format: team record (no seed)
            team, record = parts
            return f"**{team}** *({record})*"
        else:
            # Fallback
            return team_str

    async def fetch_nfl_games(self) -> Dict:
        """Fetch and parse NFL games from plaintextsports.com"""
        url = "https://plaintextsports.com/"
        
        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    print(f"HTTP Error: Status code {response.status}")
                    return None
                html = await response.text()
                print(f"Successfully fetched HTML, length: {len(html)}")
                
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find the NFL section by looking for "National Football League" text
            nfl_found = False
            current_section = None
            
            for element in soup.find_all(string=True):
                if 'National Football League' in element:
                    nfl_found = True
                    current_section = element.parent
                    break
            
            if not nfl_found:
                print("Could not find NFL section")
                return None
            
            print("Found NFL section")
            
            # Get round/week info
            round_info = "NFL Games"
            if current_section:
                next_text = current_section.find_next(string=True)
                if next_text and ('Wild Card' in next_text or 'Week' in next_text):
                    round_info = next_text.strip()
            
            games_by_day = {}
            current_day = "Today"
            
            # Find all links (game boxes are wrapped in <a> tags)
            # We need to process the entire NFL section
            processing_nfl = False
            
            for element in soup.find_all(['a', 'h1', 'h2', 'h3', 'p', 'div']):
                text = element.get_text(strip=True)
                
                # Check if we've entered NFL section
                if 'National Football League' in text:
                    processing_nfl = True
                    continue
                
                # Check if we've left NFL section (entered another sport)
                if processing_nfl and ('National Basketball' in text or 'National Hockey' in text):
                    break
                
                if not processing_nfl:
                    continue
                
                # Check for day headers
                if re.match(r'^(Today|Tomorrow|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', text):
                    # Extract just the day part
                    day_match = text.split(',')[0]
                    if day_match in ['Today', 'Tomorrow', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                        current_day = day_match
                        print(f"Found day header: {current_day}")
                    continue
                
                # Parse game boxes (they are in <a> tags with the box drawing)
                if element.name == 'a' and '+-' in element.get_text():
                    game_text = element.get_text()
                    game_data = self.parse_game_box(game_text)
                    
                    if game_data:
                        if current_day not in games_by_day:
                            games_by_day[current_day] = []
                        games_by_day[current_day].append(game_data)
                        print(f"Parsed game: {game_data}")
            
            total_games = sum(len(g) for g in games_by_day.values())
            print(f"Total games found: {total_games}")
            print(f"Games by day: {list(games_by_day.keys())}")
            
            if not games_by_day:
                print("No games parsed")
                return None
            
            result = {
                'round': round_info,
                'games': games_by_day
            }
            print(f"Returning result with {len(games_by_day)} days")
            return result
            
        except aiohttp.ClientError as e:
            print(f"Network error fetching NFL games: {e}")
            return None
        except Exception as e:
            print(f"Error fetching NFL games: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def show_nfl_games(self, ctx):
        """Show upcoming NFL games in a formatted embed"""
        async with ctx.typing():
            data = await self.fetch_nfl_games()
            
            print(f"show_nfl_games - data received: {data is not None}")
            if data:
                print(f"show_nfl_games - games dict: {data.get('games', {})}")
            
            if not data or not data.get('games'):
                await ctx.send("Could not fetch NFL game information. Please try again later.")
                return
            
            # Add games by day - "Today" should be first
            days_order = ['Today', 'Tomorrow', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            
            embeds = []
            
            for day in days_order:
                if day not in data['games']:
                    continue
                    
                games = data['games'][day]
                if not games:
                    continue
                    
                embed = discord.Embed(
                    title=f"NFL Games - {day}",
                    description=f"**{data.get('round', 'Schedule')}**",
                    color=0x013369,  # NFL blue
                    timestamp=datetime.utcnow()
                )
                
                game_lines = []
                for game in games:
                    time = game['time']
                    away = self.format_team_info(game['away'])
                    home = self.format_team_info(game['home'])
                    network = game['network']
                    
                    if network:
                        game_lines.append(f"**{time}**\n{away} @ {home} - {network}")
                    else:
                        game_lines.append(f"**{time}**\n{away} @ {home}")
                
                if game_lines:
                    field_value = "\n\n".join(game_lines)
                    # Discord embed field value limit is 1024 characters
                    if len(field_value) > 1024:
                        field_value = field_value[:1021] + "..."
                    
                    embed.add_field(
                        name="Games",
                        value=field_value,
                        inline=False
                    )
                
                embed.set_footer(text="Data from plaintextsports.com")
                embeds.append(embed)
            
            # Add any remaining days not in the order list
            for day, games in data['games'].items():
                if day not in days_order and games:
                    embed = discord.Embed(
                        title=f"NFL Games - {day}",
                        description=f"**{data.get('round', 'Schedule')}**",
                        color=0x013369,  # NFL blue
                        timestamp=datetime.utcnow()
                    )
                    
                    game_lines = []
                    for game in games:
                        time = game['time']
                        away = self.format_team_info(game['away'])
                        home = self.format_team_info(game['home'])
                        network = game['network']
                        
                        if network:
                            game_lines.append(f"**{time}**\n{away} @ {home} - {network}")
                        else:
                            game_lines.append(f"**{time}**\n{away} @ {home}")
                    
                    if game_lines:
                        field_value = "\n\n".join(game_lines)
                        if len(field_value) > 1024:
                            field_value = field_value[:1021] + "..."
                        
                        embed.add_field(
                            name="Games",
                            value=field_value,
                            inline=False
                        )
                    
                    embed.set_footer(text="Data from plaintextsports.com")
                    embeds.append(embed)
            
            # Send all embeds
            for embed in embeds:
                await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
    async def nfl(self, ctx):
        """Show NFL games
        
        Usage:
        [p]nfl - Show all upcoming games
        [p]nfl today - Show only today's games
        [p]nfl tomorrow - Show only tomorrow's games
        [p]nfl <day> - Show games for a specific day (monday, tuesday, etc.)
        """
        # Only show all games if no subcommand was invoked
        if ctx.invoked_subcommand is None:
            await self.show_nfl_games(ctx)
    
    @nfl.command(name="today")
    async def nfl_today(self, ctx):
        """Show only today's NFL games"""
        await self.show_nfl_day(ctx, "Today")
    
    @nfl.command(name="tomorrow")
    async def nfl_tomorrow(self, ctx):
        """Show only tomorrow's NFL games"""
        await self.show_nfl_day(ctx, "Tomorrow")
    
    @nfl.command(name="monday")
    async def nfl_monday(self, ctx):
        """Show Monday's NFL games"""
        await self.show_nfl_day(ctx, "Monday")
    
    @nfl.command(name="tuesday")
    async def nfl_tuesday(self, ctx):
        """Show Tuesday's NFL games"""
        await self.show_nfl_day(ctx, "Tuesday")
    
    @nfl.command(name="wednesday")
    async def nfl_wednesday(self, ctx):
        """Show Wednesday's NFL games"""
        await self.show_nfl_day(ctx, "Wednesday")
    
    @nfl.command(name="thursday")
    async def nfl_thursday(self, ctx):
        """Show Thursday's NFL games"""
        await self.show_nfl_day(ctx, "Thursday")
    
    @nfl.command(name="friday")
    async def nfl_friday(self, ctx):
        """Show Friday's NFL games"""
        await self.show_nfl_day(ctx, "Friday")
    
    @nfl.command(name="saturday")
    async def nfl_saturday(self, ctx):
        """Show Saturday's NFL games"""
        await self.show_nfl_day(ctx, "Saturday")
    
    @nfl.command(name="sunday")
    async def nfl_sunday(self, ctx):
        """Show Sunday's NFL games"""
        await self.show_nfl_day(ctx, "Sunday")

    async def show_nfl_day(self, ctx, day: str):
        """Show NFL games for a specific day"""
        async with ctx.typing():
            data = await self.fetch_nfl_games()
            
            if not data or not data.get('games'):
                await ctx.send("Could not fetch NFL game information.")
                return
            
            day_games = data['games'].get(day, [])
            
            if not day_games:
                await ctx.send(f"No NFL games scheduled for {day}.")
                return
            
            embed = discord.Embed(
                title=f"NFL Games - {day}",
                description=f"**{data.get('round', 'Schedule')}**",
                color=0x013369,
                timestamp=datetime.utcnow()
            )
            
            game_lines = []
            for game in day_games:
                time = game['time']
                away = self.format_team_info(game['away'])
                home = self.format_team_info(game['home'])
                network = game['network']
                
                if network:
                    game_lines.append(f"**{time}**\n{away} @ {home} - {network}")
                else:
                    game_lines.append(f"**{time}**\n{away} @ {home}")
            
            embed.add_field(
                name="Games",
                value="\n\n".join(game_lines),
                inline=False
            )
            
            embed.set_footer(text="Data from plaintextsports.com")
            
            await ctx.send(embed=embed)

    @commands.command()
    async def nfltest(self, ctx):
        """Test connection to PlainTextSports"""
        async with ctx.typing():
            try:
                url = "https://plaintextsports.com/"
                async with self.session.get(url, timeout=10) as response:
                    status = response.status
                    content_length = len(await response.text())
                    
                await ctx.send(
                    f"**Connection Test**\n"
                    f"Status Code: {status}\n"
                    f"Content Length: {content_length} bytes\n"
                    f"URL: {url}"
                )
            except Exception as e:
                await ctx.send(f"Connection failed: {e}")

async def setup(bot):
    """Required setup function for Red"""
    await bot.add_cog(NFLGames(bot))
