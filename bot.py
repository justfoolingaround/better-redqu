import os
import time
from typing import List

import aiohttp
import discord
import dotenv
from discord import app_commands
from discord.ext import commands

from redqu import CONTENT_CATEGORY_KEY_MAPPINGS, SESSION_HEADERS, TIME_KEY_MAPPINGS
from redqu import redqu as redqu_async_generator
from utils import RedditSVC

dotenv.load_dotenv()


TOKEN = os.getenv("TOKEN")
assert TOKEN is not None, "TOKEN environment variable not set"

INTENTS = discord.Intents.default()
RTT_EDIT_TIMES = 3


SORT_CHOICES = {
    name: app_commands.Choice(name=value.capitalize(), value=value)
    for name, value in CONTENT_CATEGORY_KEY_MAPPINGS.items()
}
TIME_CHOICES = {
    name: app_commands.Choice(name=value.capitalize(), value=value)
    for name, value in TIME_KEY_MAPPINGS.items()
}


DEFAULT_SORT = SORT_CHOICES["t"]
DEFAULT_TIME = TIME_CHOICES["w"]


waifu = commands.Bot(command_prefix="?", intents=INTENTS)


# This is awkward, see discord.py Cogs
@waifu.event
async def on_ready():
    await waifu.wait_until_ready()
    await waifu.tree.sync()

    # We usually put this in a derived bot class!
    waifu.http_session = aiohttp.ClientSession(headers=SESSION_HEADERS)
    waifu.reddit_svc = RedditSVC(waifu.http_session)
    await waifu.reddit_svc.refresh_ratelimit()

    print(f"You let me inside as {waifu.user} uwu.")


@waifu.tree.command(description="latency to reach my heart")
async def ping(interaction: discord.Interaction, detailed: bool = False):
    if not detailed:
        return await interaction.response.send_message(
            f"Pong! `{waifu.latency * 1000:.3f}`ms",
            ephemeral=True,
        )

    times = []

    start = time.time()
    message = await interaction.channel.send(f"Calculating round trip time!")
    times.append(((time.time() - start) * 1000, "sent"))

    for _ in range(RTT_EDIT_TIMES):
        start = time.time()
        message = await message.edit(
            content=f"Calculating round trip time: \n"
            + "\n".join(
                f"{n}. `{time:.3f}`ms ({reason})"
                for n, (time, reason) in enumerate(times, 1)
            )
        )
        times.append(
            (
                (time.time() - start) * 1000,
                "edited",
            )
        )

    start = time.time()
    await message.delete()
    times.append(((time.time() - start) * 1000, "deleted"))

    average = sum(seconds for seconds, _ in times) / len(times)
    stddev = (sum((seconds - average) ** 2 for seconds, _ in times) / len(times)) ** 0.5

    return await interaction.response.send_message(
        f"Average round trip time: `{average:.3f} ± {stddev:.3f}`ms\n"
        + "\n".join(
            f"{n}. `{time:.3f}`ms ({reason})"
            for n, (time, reason) in enumerate(times, 1)
        ),
        ephemeral=True,
    )


@waifu.tree.command(description="reddit media")
@app_commands.describe(
    subreddit="subreddit to search",
    sort="sort order",
    time="time period",
)
@app_commands.choices(
    sort=list(SORT_CHOICES.values()),
    time=list(TIME_CHOICES.values()),
)
async def redqu(
    interaction: discord.Interaction,
    subreddit: str,
    sort: app_commands.Choice[str] = None,
    time: app_commands.Choice[str] = None,
    page: int = 0,
):
    # TODO: Proper pagination with discord.Embed, (see jishaku)

    items = []

    async for item in redqu_async_generator(
        waifu.http_session,
        subreddit,
        (sort or DEFAULT_SORT).value,
        (time or DEFAULT_TIME).value,
        in_bot_context=True,
    ):
        items.append(item)

    return await interaction.response.send_message(
        "\n".join(items[5 * page : 5 * (page + 1)]) or "No results found.",
        ephemeral=True,
    )


@redqu.autocomplete("subreddit")
async def autocomplete_subreddit(
    interaction: discord.Interaction, current: str
) -> List[app_commands.Choice[str]]:
    if not current:
        # Implement some sort of caching here to
        # show previous selections from same user
        # or guild.
        return []

    data = []

    async for subreddit in waifu.reddit_svc.iter_subreddits(current):
        data.append(app_commands.Choice(name=subreddit, value=subreddit))

    return data


if __name__ == "__main__":
    waifu.run(TOKEN)
