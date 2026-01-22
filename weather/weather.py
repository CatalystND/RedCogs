import aiohttp
from redbot.core import commands


class Weather(commands.Cog):
    """Get weather forecasts from wttr.in"""

    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    async def fetch_weather(self, location: str) -> str:
        """Fetch weather from wttr.in for a location.

        Uses condensed format with no ANSI codes or follow line.
        """
        # URL encode the location (replace spaces with +)
        encoded_location = location.replace(" ", "+")
        url = f"https://wttr.in/{encoded_location}?T&F&n"

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with self.session.get(url, timeout=timeout) as response:
                if response.status != 200:
                    return None
                text = await response.text()
                # Check if wttr.in returned an error (usually contains "Unknown location")
                if "Unknown location" in text or "ERROR" in text:
                    return None
                return text.strip()
        except Exception:
            return None

    @commands.command()
    async def weather(self, ctx, *, location: str):
        """Get weather forecast for a location.

        Examples:
            !weather Rochester
            !weather 14618
            !weather Buffalo NY

        If a city name alone doesn't work, NY will be assumed.
        """
        async with ctx.typing():
            # Try the location as provided
            result = await self.fetch_weather(location)

            # If no result and location doesn't already have a state/country, try with NY
            if result is None and "," not in location and len(location.split()) < 3:
                result = await self.fetch_weather(f"{location},NY")

            if result is None:
                await ctx.send(f"Could not fetch weather for '{location}'. Please check the location and try again.")
                return

            # Send as code block for monospace formatting
            # Discord has a 2000 char limit per message
            if len(result) > 1990:
                result = result[:1990]

            await ctx.send(f"```\n{result}\n```")


async def setup(bot):
    await bot.add_cog(Weather(bot))
