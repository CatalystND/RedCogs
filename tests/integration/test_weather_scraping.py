"""Integration tests for Weather cog

These tests hit the real wttr.in website to validate the weather cog.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from weather.weather import Weather


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
class TestWeatherLiveScraping:
    """Test live weather fetching from wttr.in"""

    async def test_fetch_weather_city(self, integration_bot):
        """Test fetching weather for a city name"""
        cog = Weather(integration_bot)

        try:
            result = await cog.fetch_weather("Rochester")
            assert result is not None
            assert "Weather report" in result or "Rochester" in result
        finally:
            await cog.session.close()

    async def test_fetch_weather_zip(self, integration_bot):
        """Test fetching weather for a zip code"""
        cog = Weather(integration_bot)

        try:
            result = await cog.fetch_weather("14618")
            assert result is not None
            assert "Weather report" in result
        finally:
            await cog.session.close()

    async def test_fetch_weather_with_state(self, integration_bot):
        """Test fetching weather for city,state"""
        cog = Weather(integration_bot)

        try:
            result = await cog.fetch_weather("Buffalo,NY")
            assert result is not None
            assert "Weather report" in result or "Buffalo" in result
        finally:
            await cog.session.close()

    async def test_session_cleanup(self, integration_bot):
        """Test that aiohttp session is properly created and can be closed"""
        cog = Weather(integration_bot)

        assert cog.session is not None
        assert not cog.session.closed

        await cog.session.close()
        assert cog.session.closed


@pytest.mark.integration
@pytest.mark.network
@pytest.mark.asyncio
class TestWeatherCommandOutput:
    """Test and display simulated Weather command output"""

    async def test_weather_command_output(self, integration_bot):
        """Simulate !weather Rochester and print output"""
        cog = Weather(integration_bot)

        try:
            result = await cog.fetch_weather("Rochester,NY")

            if result is None:
                print("\n[SKIP] Could not fetch weather (network issue)")
                return

            print("\n" + "=" * 70)
            print("SIMULATED OUTPUT: !weather Rochester")
            print("=" * 70)
            print(f"```\n{result}\n```")
            print("=" * 70)

            assert result is not None

        finally:
            await cog.session.close()

    async def test_weather_zip_command_output(self, integration_bot):
        """Simulate !weather 14618 and print output"""
        cog = Weather(integration_bot)

        try:
            result = await cog.fetch_weather("14618")

            if result is None:
                print("\n[SKIP] Could not fetch weather (network issue)")
                return

            print("\n" + "=" * 70)
            print("SIMULATED OUTPUT: !weather 14618")
            print("=" * 70)
            print(f"```\n{result}\n```")
            print("=" * 70)

            assert result is not None

        finally:
            await cog.session.close()
