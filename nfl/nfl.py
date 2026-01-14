import discord
from redbot.core import commands, Config
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import re
from typing import List, Dict
from difflib import get_close_matches

class NFLGames(commands.Cog):
    """Get upcoming NFL game information from PlainTextSports"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.config = Config.get_conf(self, identifier=1234567890)

        # Register team cache schema
        default_global = {
            "team_cache": {}  # Format: {year: {teams: [...], cached_at: timestamp}}
        }
        self.config.register_global(**default_global)
        
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

    def get_current_nfl_year(self) -> int:
        """Determine current NFL season year

        Switch to next year after June 1st.
        Example: In May 2025 → 2024 season
                 In June 2025 → 2025 season

        Returns:
            int: The current NFL season year
        """
        now = datetime.now()
        if now.month >= 6:  # June or later
            return now.year
        else:  # Before June
            return now.year - 1

    async def fetch_team_list(self, year: int) -> List[Dict]:
        """Fetch list of NFL teams for a given year, with 3-month caching

        Args:
            year: The NFL season year

        Returns:
            List of dicts with 'name' and 'slug' keys
            Example: [{'name': 'Buffalo Bills', 'slug': 'buffalo-bills'}, ...]
        """
        # Check cache first
        team_cache = await self.config.team_cache()
        year_str = str(year)

        if year_str in team_cache:
            cached_at = team_cache[year_str].get('cached_at', 0)
            # Cache valid for 3 months (90 days)
            if (datetime.now().timestamp() - cached_at) < (90 * 24 * 60 * 60):
                return team_cache[year_str]['teams']

        # Fetch from website
        url = f"https://plaintextsports.com/nfl/{year}/teams/"
        async with self.session.get(url, timeout=10) as response:
            if response.status != 200:
                return None
            html = await response.text()

        soup = BeautifulSoup(html, 'html.parser')

        # Parse team links
        # Format: <a href="/nfl/2025/teams/buffalo-bills">Buffalo Bills</a>
        teams = []
        for link in soup.find_all('a', href=re.compile(r'/nfl/\d+/teams/')):
            href = link.get('href')
            name = link.get_text(strip=True)
            # Extract slug from href (/nfl/2025/teams/buffalo-bills → buffalo-bills)
            slug = href.split('/')[-1]
            teams.append({'name': name, 'slug': slug})

        # Cache the results
        team_cache[year_str] = {
            'teams': teams,
            'cached_at': datetime.now().timestamp()
        }
        await self.config.team_cache.set(team_cache)

        return teams

    def find_team_slug(self, team_input: str, teams: List[Dict]) -> tuple:
        """Find team slug using fuzzy matching

        Args:
            team_input: User's team input (e.g., "bills", "buffalo")
            teams: List of team dicts from fetch_team_list()

        Returns:
            tuple: (slug, full_name) or (None, None) if not found
        """
        team_input_lower = team_input.lower()

        # Build searchable strings: full names, slugs, and name parts
        searchable = {}
        for team in teams:
            name = team['name']
            slug = team['slug']

            # Add full name
            searchable[name.lower()] = (slug, name)
            # Add slug
            searchable[slug.lower()] = (slug, name)
            # Add individual words (Buffalo, Bills)
            for word in name.split():
                searchable[word.lower()] = (slug, name)
            # Add concatenated (buffalobills)
            searchable[name.replace(' ', '').lower()] = (slug, name)

        # Exact match first
        if team_input_lower in searchable:
            return searchable[team_input_lower]

        # Fuzzy match
        matches = get_close_matches(team_input_lower, searchable.keys(), n=1, cutoff=0.6)
        if matches:
            return searchable[matches[0]]

        return (None, None)

    async def fetch_team_schedule(self, year: int, team_slug: str) -> str:
        """Fetch team schedule from plaintextsports.com

        Args:
            year: NFL season year
            team_slug: Team URL slug (e.g., 'buffalo-bills')

        Returns:
            str: Raw ASCII schedule text, or None on error
        """
        url = f"https://plaintextsports.com/nfl/{year}/teams/{team_slug}"

        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    return None
                html = await response.text()

            soup = BeautifulSoup(html, 'html.parser')

            # Find the team name (in a div with class "font-bold text-center")
            team_name_div = soup.find('div', class_='font-bold text-center')
            if not team_name_div:
                return None

            team_name = team_name_div.get_text(strip=True)

            # Find the record (next div with class "text-center")
            record_div = team_name_div.find_next('div', class_='text-center')
            record = record_div.get_text(strip=True) if record_div else ''

            # Convert HTML to text, preserving line structure
            body = soup.find('body')
            if not body:
                return None

            # Replace block-level closing tags with newlines
            body_html = str(body)
            body_html = re.sub(r'</div>', '\n', body_html)
            body_html = re.sub(r'</b>', '\n', body_html)

            # Remove all HTML tags
            text = re.sub(r'<[^>]+>', ' ', body_html)

            # Clean up multiple spaces
            text = re.sub(r' +', ' ', text)

            # Split into lines
            lines = [line.strip() for line in text.split('\n') if line.strip()]

            # Extract schedule lines
            schedule_lines = [team_name, record, '']
            schedule_started = False

            for line in lines:
                if 'Playoffs:' in line or 'Regular Season:' in line or 'Preseason:' in line:
                    schedule_started = True
                if schedule_started:
                    if 'Byes:' in line or 'plaintextsports' in line.lower():
                        break
                    if len(line) > 2:
                        schedule_lines.append(line)

            return '\n'.join(schedule_lines)

        except Exception as e:
            print(f"Error fetching team schedule: {e}")
            return None

    def parse_team_schedule(self, raw_text: str) -> Dict:
        """Parse team schedule from raw text

        Args:
            raw_text: ASCII schedule from team page

        Returns:
            Dict with keys: team_name, record, playoffs, regular_season, preseason
            Each section is a list of formatted lines
        """
        lines = raw_text.strip().split('\n')

        result = {
            'team_name': '',
            'record': '',
            'playoffs': [],
            'regular_season': [],
            'preseason': []
        }

        # First line is team name
        if lines:
            result['team_name'] = lines[0].strip()

        # Second line is record
        if len(lines) > 1:
            result['record'] = lines[1].strip()

        # Parse sections
        current_section = None
        for line in lines[2:]:
            line = line.strip()
            if not line:
                continue

            # Detect section headers
            if 'Playoffs:' in line:
                current_section = 'playoffs'
                result['playoffs'].append(line)
            elif 'Regular Season:' in line:
                current_section = 'regular_season'
                result['regular_season'].append(line)
            elif 'Preseason:' in line:
                current_section = 'preseason'
                result['preseason'].append(line)
            elif current_section:
                result[current_section].append(line)

        return result

    def format_team_schedule_embed(self, schedule_data: Dict, year: int) -> discord.Embed:
        """Format team schedule as Discord embed

        Args:
            schedule_data: Parsed schedule from parse_team_schedule()
            year: NFL season year

        Returns:
            discord.Embed: Formatted embed
        """
        team_name = schedule_data.get('team_name', 'Unknown Team')
        record = schedule_data.get('record', '')

        embed = discord.Embed(
            title=f"{team_name} - {year} Season",
            description=f"**{record}**" if record else None,
            color=0x013369,  # NFL blue
            timestamp=datetime.utcnow()
        )

        # Add playoffs if exists
        if schedule_data.get('playoffs'):
            playoff_text = '\n'.join(schedule_data['playoffs'])
            # Discord field limit is 1024 chars
            if len(playoff_text) > 1024:
                playoff_text = playoff_text[:1021] + "..."
            embed.add_field(
                name="Playoffs",
                value=f"```\n{playoff_text}\n```",
                inline=False
            )

        # Add regular season
        if schedule_data.get('regular_season'):
            season_text = '\n'.join(schedule_data['regular_season'])
            # Split into multiple fields if too long
            chunks = self._split_text_to_chunks(season_text, 1020)
            for i, chunk in enumerate(chunks):
                name = "Regular Season" if i == 0 else "Regular Season (cont.)"
                embed.add_field(
                    name=name,
                    value=f"```\n{chunk}\n```",
                    inline=False
                )

        # Add preseason
        if schedule_data.get('preseason'):
            preseason_text = '\n'.join(schedule_data['preseason'])
            if len(preseason_text) > 1024:
                preseason_text = preseason_text[:1021] + "..."
            embed.add_field(
                name="Preseason",
                value=f"```\n{preseason_text}\n```",
                inline=False
            )

        embed.set_footer(text="Data from plaintextsports.com")

        return embed

    def _split_text_to_chunks(self, text: str, max_length: int) -> List[str]:
        """Split text into chunks at line boundaries"""
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_length = 0

        for line in lines:
            line_length = len(line) + 1  # +1 for newline
            if current_length + line_length > max_length:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_length = line_length
            else:
                current_chunk.append(line)
                current_length += line_length

        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    async def fetch_nfl_games(self) -> Dict:
        """Fetch and parse NFL games from plaintextsports.com"""
        url = "https://plaintextsports.com/nfl/"
        
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

                # Check if we've left NFL section (entered another sport/league)
                if processing_nfl:
                    # Look for other major sports leagues
                    other_leagues = [
                        'National Basketball',   # NBA
                        'National Hockey',       # NHL
                        'Major League Baseball', # MLB
                        'Major League Soccer',   # MLS
                        'National Association',  # College sports
                    ]

                    # Check if we hit another league
                    if any(league in text for league in other_leagues):
                        print(f"Found end of NFL section: {text}")
                        break

                    # Safety limit: stop if we've found an unreasonable number of games
                    total_parsed = sum(len(games) for games in games_by_day.values())
                    if total_parsed >= 20:
                        print(f"Safety limit reached: {total_parsed} games parsed")
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

    @commands.bot_has_permissions(embed_links=True)
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
    
    @commands.bot_has_permissions(embed_links=True)
    @nfl.command(name="today")
    async def nfl_today(self, ctx):
        """Show only today's NFL games"""
        await self.show_nfl_day(ctx, "Today")
    
    @commands.bot_has_permissions(embed_links=True)
    @nfl.command(name="tomorrow")
    async def nfl_tomorrow(self, ctx):
        """Show only tomorrow's NFL games"""
        await self.show_nfl_day(ctx, "Tomorrow")
    
    @commands.bot_has_permissions(embed_links=True)
    @nfl.command(name="monday")
    async def nfl_monday(self, ctx):
        """Show Monday's NFL games"""
        await self.show_nfl_day(ctx, "Monday")

    @commands.bot_has_permissions(embed_links=True)
    @nfl.command(name="tuesday")
    async def nfl_tuesday(self, ctx):
        """Show Tuesday's NFL games"""
        await self.show_nfl_day(ctx, "Tuesday")

    @commands.bot_has_permissions(embed_links=True)
    @nfl.command(name="wednesday")
    async def nfl_wednesday(self, ctx):
        """Show Wednesday's NFL games"""
        await self.show_nfl_day(ctx, "Wednesday")

    @commands.bot_has_permissions(embed_links=True)
    @nfl.command(name="thursday")
    async def nfl_thursday(self, ctx):
        """Show Thursday's NFL games"""
        await self.show_nfl_day(ctx, "Thursday")

    @commands.bot_has_permissions(embed_links=True)
    @nfl.command(name="friday")
    async def nfl_friday(self, ctx):
        """Show Friday's NFL games"""
        await self.show_nfl_day(ctx, "Friday")

    @commands.bot_has_permissions(embed_links=True)
    @nfl.command(name="saturday")
    async def nfl_saturday(self, ctx):
        """Show Saturday's NFL games"""
        await self.show_nfl_day(ctx, "Saturday")

    @commands.bot_has_permissions(embed_links=True)
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

    @commands.bot_has_permissions(embed_links=True)
    @nfl.command(name="team")
    async def nfl_team(self, ctx, team_name: str, year: int = None):
        """Show a team's full season schedule

        Usage:
            [p]nfl team bills           - Current season
            [p]nfl team buffalo 2022    - Specific year
            [p]nfl team buffalobills    - Alternative format

        Args:
            team_name: Team name or nickname (fuzzy matched)
            year: Optional season year (2021+), defaults to current season
        """
        async with ctx.typing():
            # Determine year
            if year is None:
                year = self.get_current_nfl_year()

            # Validate year
            current_year = self.get_current_nfl_year()
            if year < 2021:
                await ctx.send(f"Data only available for 2021-{current_year}.")
                return
            if year > current_year:
                await ctx.send(f"Data not yet available for {year}.")
                return

            # Fetch team list
            teams = await self.fetch_team_list(year)
            if not teams:
                await ctx.send(f"Could not fetch team list for {year}.")
                return

            # Find team
            team_slug, full_name = self.find_team_slug(team_name, teams)
            if not team_slug:
                # Build helpful error message
                team_names = [t['name'] for t in teams[:5]]
                await ctx.send(
                    f"Team '{team_name}' not found. Try: {', '.join(team_names)}, etc."
                )
                return

            # Fetch schedule
            raw_schedule = await self.fetch_team_schedule(year, team_slug)
            if not raw_schedule:
                await ctx.send(f"Could not fetch schedule for {full_name} ({year}).")
                return

            # Parse and format
            schedule_data = self.parse_team_schedule(raw_schedule)
            embed = self.format_team_schedule_embed(schedule_data, year)

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
