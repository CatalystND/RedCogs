"""Base class and shared utilities for PlainTextSports cogs"""

import discord
from redbot.core import commands, Config
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import re
from typing import List, Dict, Optional, Tuple
from difflib import get_close_matches
from dataclasses import dataclass
import logging


@dataclass
class SportConfig:
    """Configuration for a specific sport"""
    name: str                    # "NFL", "NHL", "MLB", "NBA"
    slug: str                    # "nfl", "nhl", "mlb", "nba"
    full_name: str               # "National Football League"
    color: int                   # Discord embed color
    other_leagues: List[str]     # League names to stop parsing at
    season_start_month: int      # Month when new season year starts (6 = June for NFL)
    base_url: str = "https://plaintextsports.com"


class BaseSportsCog(commands.Cog):
    """Base class for PlainTextSports cogs with shared functionality"""

    def __init__(self, bot, config: SportConfig):
        self.bot = bot
        self.sport = config
        self.session = aiohttp.ClientSession()
        self.log = logging.getLogger(f"red.{config.slug}")

        # Config for team cache
        self.config = Config.get_conf(self, identifier=hash(config.slug) & 0xFFFFFFFF)
        self.config.register_global(team_cache={})

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    def get_current_season_year(self) -> int:
        """Get current season year based on sport's calendar"""
        now = datetime.now()
        return now.year if now.month >= self.sport.season_start_month else now.year - 1

    def parse_game_box(self, text: str) -> Optional[Dict]:
        """Parse ASCII game box into structured data

        Handles both scheduled games (time) and live/final games (score).
        Returns: {time/status, away, home, network, scores (if applicable)}
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        cleaned_lines = []
        for line in lines:
            cleaned = line.strip('+ |')
            if cleaned and not all(c in '+-' for c in cleaned):
                cleaned_lines.append(cleaned)

        if len(cleaned_lines) < 3:
            return None

        network = cleaned_lines[3].strip().replace('-', '').strip() if len(cleaned_lines) > 3 else ''

        status_line = cleaned_lines[0].strip()
        away_line = cleaned_lines[1].strip()
        home_line = cleaned_lines[2].strip()

        # Check if this is a live/completed game (has scores)
        away_parts = away_line.split()
        home_parts = home_line.split()

        result = {
            'status': status_line,
            'away': away_line,
            'home': home_line,
            'network': network
        }

        # Try to extract scores if present (for live/final games)
        if len(away_parts) >= 2 and away_parts[-1].isdigit():
            result['away_score'] = int(away_parts[-1])
            result['away_team'] = ' '.join(away_parts[:-1])
        if len(home_parts) >= 2 and home_parts[-1].isdigit():
            result['home_score'] = int(home_parts[-1])
            result['home_team'] = ' '.join(home_parts[:-1])

        return result

    def format_team_info(self, team_str: str) -> str:
        """Format team string for display: '5 LAR 12-5' -> '**LAR** *(12-5)*'"""
        parts = team_str.split()

        # Handle "5 LAR 12-5" (seed team record)
        if len(parts) == 3 and parts[0].isdigit():
            _, team, record = parts
            return f"**{team}** *({record})*"
        # Handle "LAR 12-5" (team record)
        elif len(parts) == 2 and '-' in parts[1]:
            team, record = parts
            return f"**{team}** *({record})*"
        # Handle "LAR 5" (team score)
        elif len(parts) == 2 and parts[1].isdigit():
            team, score = parts
            return f"**{team}** {score}"
        # Handle just team abbreviation
        elif len(parts) == 1:
            return f"**{parts[0]}**"
        return team_str

    def _split_text_to_chunks(self, text: str, max_length: int) -> List[str]:
        """Split text into chunks at line boundaries"""
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_length = 0

        for line in lines:
            line_length = len(line) + 1
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

    async def fetch_team_list(self, year: int) -> Optional[List[Dict]]:
        """Fetch teams for a year (cached 90 days). Returns [{'name': ..., 'slug': ...}, ...]"""
        team_cache = await self.config.team_cache()
        cache_key = f"{self.sport.slug}_{year}"

        if cache_key in team_cache:
            cached_at = team_cache[cache_key].get('cached_at', 0)
            if (datetime.now().timestamp() - cached_at) < (90 * 24 * 60 * 60):
                return team_cache[cache_key]['teams']

        url = f"{self.sport.base_url}/{self.sport.slug}/{year}/teams/"
        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    return None
                html = await response.text()
        except Exception:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        teams = []
        pattern = rf'/{self.sport.slug}/\d+/teams/'
        for link in soup.find_all('a', href=re.compile(pattern)):
            teams.append({
                'name': link.get_text(strip=True),
                'slug': link.get('href').split('/')[-1]
            })

        if teams:
            team_cache[cache_key] = {'teams': teams, 'cached_at': datetime.now().timestamp()}
            await self.config.team_cache.set(team_cache)

        return teams if teams else None

    def find_team_slug(self, team_input: str, teams: List[Dict]) -> Tuple[Optional[str], Optional[str]]:
        """Fuzzy match team input to (slug, full_name) or (None, None)"""
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

    async def fetch_team_schedule(self, year: int, team_slug: str) -> Optional[str]:
        """Fetch raw ASCII schedule text for a team"""
        url = f"{self.sport.base_url}/{self.sport.slug}/{year}/teams/{team_slug}"

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
                if 'Playoffs:' in line or 'Regular Season:' in line or 'Preseason:' in line or 'Postseason:' in line:
                    schedule_started = True
                if schedule_started:
                    if 'plaintextsports' in line.lower():
                        break
                    if len(line) > 2:
                        schedule_lines.append(line)

            return '\n'.join(schedule_lines)

        except Exception:
            return None

    def parse_team_schedule(self, raw_text: str) -> Dict:
        """Parse raw schedule into sections"""
        lines = raw_text.strip().split('\n')
        result = {
            'team_name': lines[0].strip() if lines else '',
            'record': lines[1].strip() if len(lines) > 1 else '',
            'playoffs': [], 'postseason': [], 'regular_season': [], 'preseason': []
        }

        current_section = None
        for line in lines[2:]:
            line = line.strip()
            if not line:
                continue
            if 'Playoffs:' in line or 'Postseason:' in line:
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
            color=self.sport.color,
            timestamp=datetime.now(timezone.utc)
        )

        sections = [('playoffs', 'Playoffs'), ('postseason', 'Postseason'),
                    ('regular_season', 'Regular Season'), ('preseason', 'Preseason')]

        for section, name in sections:
            if not schedule_data.get(section):
                continue
            text = '\n'.join(schedule_data[section])
            if section == 'regular_season':
                for i, chunk in enumerate(self._split_text_to_chunks(text, 1020)):
                    embed.add_field(name=name if i == 0 else f"{name} (cont.)",
                                  value=f"```\n{chunk}\n```", inline=False)
            else:
                if len(text) > 1024:
                    text = text[:1021] + "..."
                embed.add_field(name=name, value=f"```\n{text}\n```", inline=False)

        embed.set_footer(text="Data from plaintextsports.com")
        return embed

    async def fetch_games(self) -> Dict | str:
        """Fetch and parse games. Returns dict on success, error string on failure.

        This is the main method that should be customized per sport if needed.
        Default implementation works for NFL-style pages.
        """
        url = f"{self.sport.base_url}/{self.sport.slug}/"

        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    return "Website unavailable (HTTP error). Try again shortly."
                html = await response.text()

            soup = BeautifulSoup(html, 'html.parser')

            # Find the sport section
            sport_found = False
            current_section = None
            for element in soup.find_all(string=True):
                if self.sport.full_name in element:
                    sport_found = True
                    current_section = element.parent
                    break

            if not sport_found:
                return f"{self.sport.name} section not found - website may have changed."

            # Try to find round/week info
            round_info = f"{self.sport.name} Games"
            if current_section:
                next_text = current_section.find_next(string=True)
                if next_text:
                    text = next_text.strip()
                    # Common patterns for various sports
                    if any(kw in text for kw in ['Week', 'Wild Card', 'Divisional', 'Conference',
                                                  'Championship', 'Super Bowl', 'Stanley Cup',
                                                  'World Series', 'Finals', 'Playoffs', 'Round']):
                        round_info = text

            games_by_day = {}
            current_day = "Today"
            processing_sport = False

            for element in soup.find_all(['a', 'h1', 'h2', 'h3', 'p', 'div']):
                text = element.get_text(strip=True)

                if self.sport.full_name in text:
                    processing_sport = True
                    continue

                if processing_sport:
                    # Stop at other leagues
                    if any(league in text for league in self.sport.other_leagues):
                        break
                    # Safety limit
                    if sum(len(games) for games in games_by_day.values()) >= 30:
                        break

                if not processing_sport:
                    continue

                # Check for day headers
                if re.match(r'^(Today|Tomorrow|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', text):
                    day_match = text.split(',')[0]
                    if day_match in ['Today', 'Tomorrow', 'Monday', 'Tuesday', 'Wednesday',
                                    'Thursday', 'Friday', 'Saturday', 'Sunday']:
                        current_day = day_match
                    continue

                # Parse game boxes (look for ASCII box drawing characters)
                if element.name == 'a' and '+-' in element.get_text():
                    game_data = self.parse_game_box(element.get_text())
                    if game_data:
                        if current_day not in games_by_day:
                            games_by_day[current_day] = []
                        games_by_day[current_day].append(game_data)

            if not games_by_day:
                return f"No {self.sport.name} games found. The season may be over or no games scheduled."

            return {'round': round_info, 'games': games_by_day}

        except Exception as e:
            self.log.warning(f"{self.sport.name} parse error: {type(e).__name__}: {e}")
            return "Error processing game data. Try again later."

    def build_day_embed(self, day: str, games: List[Dict], round_info: str) -> discord.Embed:
        """Build embed for a day's games"""
        embed = discord.Embed(
            title=f"{self.sport.name} Games - {day}",
            description=f"**{round_info}**",
            color=self.sport.color,
            timestamp=datetime.now(timezone.utc)
        )

        game_lines = []
        for game in games:
            # Check if it's a live/final game (has scores)
            if 'away_score' in game and 'home_score' in game:
                away = f"**{game.get('away_team', game['away'])}** {game['away_score']}"
                home = f"**{game.get('home_team', game['home'])}** {game['home_score']}"
                line = f"**{game['status']}**\n{away} @ {home}"
            else:
                # Scheduled game
                away = self.format_team_info(game['away'])
                home = self.format_team_info(game['home'])
                line = f"**{game['status']}**\n{away} @ {home}"

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

    async def show_games(self, ctx):
        """Show upcoming games"""
        async with ctx.typing():
            data = await self.fetch_games()

            if isinstance(data, str):
                await ctx.send(data)
                return
            if not data or not data.get('games'):
                await ctx.send(f"Could not fetch {self.sport.name} game information.")
                return

            days_order = ['Today', 'Tomorrow', 'Sunday', 'Monday', 'Tuesday',
                         'Wednesday', 'Thursday', 'Friday', 'Saturday']
            round_info = data.get('round', 'Schedule')

            all_days = [d for d in days_order if d in data['games']] + \
                      [d for d in data['games'] if d not in days_order]

            for day in all_days:
                games = data['games'].get(day, [])
                if games:
                    await ctx.send(embed=self.build_day_embed(day, games, round_info))

    async def show_day(self, ctx, day: str):
        """Show games for a specific day"""
        async with ctx.typing():
            data = await self.fetch_games()

            if isinstance(data, str):
                await ctx.send(data)
                return
            if not data or not data.get('games'):
                await ctx.send(f"Could not fetch {self.sport.name} game information.")
                return

            day_games = data['games'].get(day, [])
            if not day_games:
                await ctx.send(f"No {self.sport.name} games scheduled for {day}.")
                return

            await ctx.send(embed=self.build_day_embed(day, day_games, data.get('round', 'Schedule')))

    async def show_team(self, ctx, team_name: str, year: int = None):
        """Show a team's full season schedule"""
        async with ctx.typing():
            if year is None:
                year = self.get_current_season_year()

            current_year = self.get_current_season_year()
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
                sample_teams = ', '.join(t['name'] for t in teams[:5])
                await ctx.send(f"Team '{team_name}' not found. Try: {sample_teams}, etc.")
                return

            raw_schedule = await self.fetch_team_schedule(year, team_slug)
            if not raw_schedule:
                await ctx.send(f"Could not fetch schedule for {full_name} ({year}).")
                return

            await ctx.send(embed=self.format_team_schedule_embed(
                self.parse_team_schedule(raw_schedule), year))

    async def test_connection(self, ctx):
        """Test connection to PlainTextSports"""
        async with ctx.typing():
            try:
                url = f"{self.sport.base_url}/{self.sport.slug}/"
                async with self.session.get(url, timeout=10) as response:
                    status = response.status
                    content_length = len(await response.text())

                await ctx.send(
                    f"**{self.sport.name} Connection Test**\n"
                    f"Status Code: {status}\n"
                    f"Content Length: {content_length} bytes\n"
                    f"URL: {url}"
                )
            except Exception as e:
                await ctx.send(f"Connection failed: {e}")
