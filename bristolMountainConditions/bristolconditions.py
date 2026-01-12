import discord
from redbot.core import commands
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Tuple, Optional

class BristolConditions(commands.Cog):
    """Get Bristol Mountain ski conditions including lift status and trail information"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        self.bot.loop.create_task(self.session.close())

    async def get_bristol_conditions(self) -> Optional[Tuple[List[Dict], List[Dict]]]:
        """Fetch and parse Bristol Mountain conditions"""
        url = "https://www.bristolmountain.com/conditions/"
        try:
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    return None, None
                html = await response.text()
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None, None

        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')

        if len(tables) < 2:
            print("Could not find both lift and trail tables.")
            return None, None

        # --- 1. EXTRACT LIFTS ---
        lifts = []
        lift_table = tables[0]
        for row in lift_table.find_all('tr')[1:]:  # Skip header
            cols = row.find_all('td')
            if len(cols) >= 2:
                lifts.append({
                    "Name": cols[0].get_text(strip=True),
                    "Status": cols[1].get_text(strip=True).upper()
                })

        # --- 2. EXTRACT TRAILS ---
        trails = []
        # Trail tables are usually the subsequent tables (Alpine Trails)
        for trail_table in tables[1:]:
            # Try to find difficulty from a preceding header or an icon in the table
            current_difficulty = "Unknown"
            header = trail_table.find_previous(['h3', 'h4', 'strong'])
            if header:
                header_text = header.get_text().lower()
                if "easier" in header_text: current_difficulty = "● Easier"
                elif "more difficult" in header_text: current_difficulty = "■ More Difficult"
                elif "most difficult" in header_text: current_difficulty = "♦ Most Difficult"
                elif "extremely difficult" in header_text: current_difficulty = "♦♦ Extremely Difficult"

            for row in trail_table.find_all('tr'):
                cols = row.find_all('td')
                # Look for rows with Trail Name, Status, Surface, Comments
                if len(cols) >= 3:
                    name = cols[0].get_text(strip=True)
                    # Filter out header rows
                    if name.lower() in ["trail", "lift", "status"]:
                        continue

                    status = cols[1].get_text(strip=True).upper()
                    surface = cols[2].get_text(strip=True) if len(cols) > 2 else "N/A"
                    comments = cols[3].get_text(strip=True) if len(cols) > 3 else ""

                    # Double check for difficulty icons in the first cell
                    img = cols[0].find('img')
                    if img and img.get('alt'):
                        current_difficulty = img.get('alt')

                    trails.append({
                        "Name": name,
                        "Difficulty": current_difficulty,
                        "Status": status,
                        "Conditions": f"{surface} {comments}".strip()
                    })

        return lifts, trails

    @commands.bot_has_permissions(embed_links=True)
    @commands.command()
    async def bristol(self, ctx):
        """Show Bristol Mountain lift and trail conditions"""
        async with ctx.typing():
            lifts, trails = await self.get_bristol_conditions()

            if not lifts or not trails:
                await ctx.send("Could not fetch Bristol Mountain conditions. Please try again later.")
                return

            # Create embed for lifts
            lift_embed = discord.Embed(
                title="Bristol Mountain - Ski Lift Status",
                color=0x0066CC,
                url="https://www.bristolmountain.com/conditions/"
            )

            lift_lines = []
            for lift in lifts:
                icon = "✅" if lift['Status'] == "OPEN" else "❌"
                lift_lines.append(f"{icon} **{lift['Name']}** - {lift['Status']}")

            if lift_lines:
                lift_embed.add_field(
                    name="Lifts",
                    value="\n".join(lift_lines),
                    inline=False
                )

            await ctx.send(embed=lift_embed)

            # Create embeds for trails (may need multiple due to field limits)
            trail_embed = discord.Embed(
                title="Bristol Mountain - Trail Conditions",
                color=0x0066CC,
                url="https://www.bristolmountain.com/conditions/"
            )

            # Group trails by status
            open_trails = [t for t in trails if t['Status'] == 'OPEN']
            closed_trails = [t for t in trails if t['Status'] != 'OPEN']

            if open_trails:
                trail_lines = []
                for trail in open_trails[:15]:  # Limit to avoid embed size issues
                    trail_lines.append(
                        f"**{trail['Name']}** {trail['Difficulty']}\n"
                        f"└ {trail['Conditions']}"
                    )

                trail_embed.add_field(
                    name=f"Open Trails ({len(open_trails)})",
                    value="\n".join(trail_lines) if trail_lines else "None",
                    inline=False
                )

            if closed_trails:
                closed_names = [f"~~{t['Name']}~~" for t in closed_trails[:10]]
                trail_embed.add_field(
                    name=f"Closed Trails ({len(closed_trails)})",
                    value=", ".join(closed_names) if closed_names else "None",
                    inline=False
                )

            trail_embed.set_footer(text="Data from bristolmountain.com")

            await ctx.send(embed=trail_embed)

async def setup(bot):
    """Required setup function for Red"""
    await bot.add_cog(BristolConditions(bot))
