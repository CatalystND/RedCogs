import discord
from redbot.core import commands, Config
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timezone
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
        self.bot.loop.create_task(self.session.close())

    def parse_game_box(self, text: str) -> Dict:
        """Parse ASCII game box: time, away team, home team, network"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        cleaned_lines = []
        for line in lines:
            cleaned = line.strip('+ |')
            if cleaned and not all(c in '+-' for c in cleaned):
                cleaned_lines.append(cleaned)

        if len(cleaned_lines) < 3:
            return None

        network = cleaned_lines[3].strip().replace('-', '').strip() if len(cleaned_lines) > 3 else ''

        return {
            'time': cleaned_lines[0].strip(),
            'away': cleaned_lines[1].strip(),
            'home': cleaned_lines[2].strip(),
            'network': network
        }

    def format_team_info(self, team_str: str) -> str:
        """Format '5 LAR 12-5' or 'LAR 12-5' → '**LAR** *(12-5)*'"""
        parts = team_str.split()
        if len(parts) == 3:
            _, team, record = parts
            return f"**{team}** *({record})*"
        elif len(parts) == 2:
            team, record = parts
            return f"**{team}** *({record})*"
        return team_str

    def get_current_nfl_year(self) -> int:
        """NFL season year (switches to next year after June 1st)"""
        now = datetime.now()
        return now.year if now.month >= 6 else now.year - 1

    async def fetch_team_list(self, year: int) -> List[Dict]:
        """Fetch NFL teams for a year (cached 90 days). Returns [{'name': ..., 'slug': ...}, ...]"""
        team_cache = await self.config.team_cache()
        year_str = str(year)

        if year_str in team_cache:
            cached_at = team_cache[year_str].get('cached_at', 0)
            if (datetime.now().timestamp() - cached_at) < (90 * 24 * 60 * 60):
                return team_cache[year_str]['teams']

        url = f"https://plaintextsports.com/nfl/{year}/teams/"
        async with self.session.get(url, timeout=10) as response:
            if response.status != 200:
                return None
            html = await response.text()

        soup = BeautifulSoup(html, 'html.parser')
        teams = []
        for link in soup.find_all('a', href=re.compile(r'/nfl/\d+/teams/')):
            teams.append({
                'name': link.get_text(strip=True),
                'slug': link.get('href').split('/')[-1]
            })

        team_cache[year_str] = {'teams': teams, 'cached_at': datetime.now().timestamp()}
        await self.config.team_cache.set(team_cache)
        return teams

    def find_team_slug(self, team_input: str, teams: List[Dict]) -> tuple:
        """Fuzzy match team input → (slug, full_name) or (None, None)"""
        team_input_lower = team_input.lower()

        searchable = {}
        for team in teams:
            name, slug = team['name'], team['slug']
            searchable[name.lower()] = (slug, name)
            searchable[slug.lower()] = (slug, name)
            searchable[name.replace(' ', '').lower()] = (slug, name)
            for word in name.split():
                searchable[word.lower()] = (slug, name)

        if team_input_lower in searchable:
            return searchable[team_input_lower]

        matches = get_close_matches(team_input_lower, searchable.keys(), n=1, cutoff=0.6)
        return searchable[matches[0]] if matches else (None, None)

    async def fetch_team_schedule(self, year: int, team_slug: str) -> str:
        """Fetch raw ASCII schedule text for a team"""
        url = f"https://plaintextsports.com/nfl/{year}/teams/{team_slug}"

        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    return None
                html = await response.text()

            soup = BeautifulSoup(html, 'html.parser')

            team_name_div = soup.find('div', class_='font-bold text-center')
            if not team_name_div:
                return None
            team_name = team_name_div.get_text(strip=True)

            record_div = team_name_div.find_next('div', class_='text-center')
            record = record_div.get_text(strip=True) if record_div else ''

            body = soup.find('body')
            if not body:
                return None

            body_html = re.sub(r'</div>', '\n', str(body))
            body_html = re.sub(r'</b>', '\n', body_html)
            text = re.sub(r' +', ' ', re.sub(r'<[^>]+>', ' ', body_html))
            lines = [line.strip() for line in text.split('\n') if line.strip()]

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

        except Exception:
            return None

    def parse_team_schedule(self, raw_text: str) -> Dict:
        """Parse raw schedule → {team_name, record, playoffs, regular_season, preseason}"""
        lines = raw_text.strip().split('\n')
        result = {
            'team_name': lines[0].strip() if lines else '',
            'record': lines[1].strip() if len(lines) > 1 else '',
            'playoffs': [], 'regular_season': [], 'preseason': []
        }

        current_section = None
        for line in lines[2:]:
            line = line.strip()
            if not line:
                continue
            if 'Playoffs:' in line:
                current_section = 'playoffs'
            elif 'Regular Season:' in line:
                current_section = 'regular_season'
            elif 'Preseason:' in line:
                current_section = 'preseason'
            if current_section:
                result[current_section].append(line)

        return result

    def format_team_schedule_embed(self, schedule_data: Dict, year: int) -> discord.Embed:
        """Format parsed schedule as Discord embed"""
        embed = discord.Embed(
            title=f"{schedule_data.get('team_name', 'Unknown Team')} - {year} Season",
            description=f"**{schedule_data.get('record', '')}**" if schedule_data.get('record') else None,
            color=0x013369,
            timestamp=datetime.now(timezone.utc)
        )

        for section, name in [('playoffs', 'Playoffs'), ('regular_season', 'Regular Season'), ('preseason', 'Preseason')]:
            if not schedule_data.get(section):
                continue
            text = '\n'.join(schedule_data[section])
            if section == 'regular_season':
                for i, chunk in enumerate(self._split_text_to_chunks(text, 1020)):
                    embed.add_field(name=name if i == 0 else f"{name} (cont.)", value=f"```\n{chunk}\n```", inline=False)
            else:
                if len(text) > 1024:
                    text = text[:1021] + "..."
                embed.add_field(name=name, value=f"```\n{text}\n```", inline=False)

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
                    return None
                html = await response.text()

            soup = BeautifulSoup(html, 'html.parser')

            nfl_found = False
            current_section = None
            for element in soup.find_all(string=True):
                if 'National Football League' in element:
                    nfl_found = True
                    current_section = element.parent
                    break

            if not nfl_found:
                return None

            round_info = "NFL Games"
            if current_section:
                next_text = current_section.find_next(string=True)
                if next_text and ('Wild Card' in next_text or 'Week' in next_text):
                    round_info = next_text.strip()

            games_by_day = {}
            current_day = "Today"
            processing_nfl = False
            other_leagues = ['National Basketball', 'National Hockey', 'Major League Baseball', 'Major League Soccer', 'National Association']

            for element in soup.find_all(['a', 'h1', 'h2', 'h3', 'p', 'div']):
                text = element.get_text(strip=True)

                if 'National Football League' in text:
                    processing_nfl = True
                    continue

                if processing_nfl:
                    if any(league in text for league in other_leagues):
                        break
                    if sum(len(games) for games in games_by_day.values()) >= 20:
                        break

                if not processing_nfl:
                    continue

                if re.match(r'^(Today|Tomorrow|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', text):
                    day_match = text.split(',')[0]
                    if day_match in ['Today', 'Tomorrow', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                        current_day = day_match
                    continue

                if element.name == 'a' and '+-' in element.get_text():
                    game_data = self.parse_game_box(element.get_text())
                    if game_data:
                        if current_day not in games_by_day:
                            games_by_day[current_day] = []
                        games_by_day[current_day].append(game_data)

            if not games_by_day:
                return None

            return {'round': round_info, 'games': games_by_day}

        except Exception:
            return None

    def _build_day_embed(self, day: str, games: List[Dict], round_info: str) -> discord.Embed:
        """Build embed for a day's games"""
        embed = discord.Embed(
            title=f"NFL Games - {day}",
            description=f"**{round_info}**",
            color=0x013369,
            timestamp=datetime.now(timezone.utc)
        )

        game_lines = []
        for game in games:
            away = self.format_team_info(game['away'])
            home = self.format_team_info(game['home'])
            line = f"**{game['time']}**\n{away} @ {home}"
            if game['network']:
                line += f" - {game['network']}"
            game_lines.append(line)

        if game_lines:
            field_value = "\n\n".join(game_lines)
            if len(field_value) > 1024:
                field_value = field_value[:1021] + "..."
            embed.add_field(name="Games", value=field_value, inline=False)

        embed.set_footer(text="Data from plaintextsports.com")
        return embed

    async def show_nfl_games(self, ctx):
        """Show upcoming NFL games in a formatted embed"""
        async with ctx.typing():
            data = await self.fetch_nfl_games()

            if not data or not data.get('games'):
                await ctx.send("Could not fetch NFL game information. Please try again later.")
                return

            days_order = ['Today', 'Tomorrow', 'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            round_info = data.get('round', 'Schedule')

            # Process ordered days first, then any remaining
            all_days = [d for d in days_order if d in data['games']] + [d for d in data['games'] if d not in days_order]

            for day in all_days:
                games = data['games'].get(day, [])
                if games:
                    await ctx.send(embed=self._build_day_embed(day, games, round_info))

    @commands.bot_has_permissions(embed_links=True)
    @commands.group(invoke_without_command=True)
    async def nfl(self, ctx):
        """Show NFL games for the current week

        Subcommands:
          team <name> [year] - Show a team's full season schedule
          today              - Show only today's games
          tomorrow           - Show only tomorrow's games
          <day>              - Show specific day (monday, tuesday, etc.)
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

            await ctx.send(embed=self._build_day_embed(day, day_games, data.get('round', 'Schedule')))

    @commands.bot_has_permissions(embed_links=True)
    @nfl.command(name="team")
    async def nfl_team(self, ctx, team_name: str, year: int = None):
        """Show a team's full season schedule

        Examples:
            [p]nfl team bills           - Current season
            [p]nfl team buffalo 2022    - 2022 season
            [p]nfl team buffalobills    - Fuzzy matched
        """
        async with ctx.typing():
            if year is None:
                year = self.get_current_nfl_year()

            current_year = self.get_current_nfl_year()
            if year < 2021:
                await ctx.send(f"Data only available for 2021-{current_year}.")
                return
            if year > current_year:
                await ctx.send(f"Data not yet available for {year}.")
                return

            teams = await self.fetch_team_list(year)
            if not teams:
                await ctx.send(f"Could not fetch team list for {year}.")
                return

            team_slug, full_name = self.find_team_slug(team_name, teams)
            if not team_slug:
                await ctx.send(f"Team '{team_name}' not found. Try: {', '.join(t['name'] for t in teams[:5])}, etc.")
                return

            raw_schedule = await self.fetch_team_schedule(year, team_slug)
            if not raw_schedule:
                await ctx.send(f"Could not fetch schedule for {full_name} ({year}).")
                return

            await ctx.send(embed=self.format_team_schedule_embed(self.parse_team_schedule(raw_schedule), year))

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
    await bot.add_cog(NFLGames(bot))
