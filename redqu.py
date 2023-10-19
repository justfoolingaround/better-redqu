#!/bin/python
import asyncio
import re
import subprocess
import sys

import aiohttp

REPOSITORY_URL = "https://github.com/port19x/redqu"


HELP_TEXT = f"""Usage: redqu sub sort time
Example: redqu cats top week

Valid sort parameters: hot new top rising controversial
Valid time parameters: hour day week month year all
Top of week is the default

To report issues of any kind:
{REPOSITORY_URL}/issues"""


SESSION_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:101.0) Gecko/20100101 Firefox/101.0",
}


TIME_KEY_MAPPINGS = {
    "h": "hour",
    "d": "day",
    "w": "week",
    "m": "month",
    "y": "year",
    "a": "all",
}
CONTENT_CATEGORY_KEY_MAPPINGS = {
    "h": "hot",
    "n": "new",
    "t": "top",
    "r": "rising",
    "c": "controversial",
}


PROTOCOL_RAW_REGEX = r"(?:(?:https?:)?//)?"
REDDIT_URL = "https://reddit.com/"

IMAGE_MATCH_REGEXES = [
    re.compile(PROTOCOL_RAW_REGEX + r"i\.redd\.it/[a-z0-9]+\.(?:png|jpe?g|gif)"),
    re.compile(PROTOCOL_RAW_REGEX + r"i\.imgur\.com/[a-z0-9]+\.(?:png|jpe?g|gif)"),
]

CLI_SPECIFIC_MATCH_REGEXES = [
    re.compile(PROTOCOL_RAW_REGEX + r"v\.redd\.it/[a-z0-9]+"),
    re.compile(PROTOCOL_RAW_REGEX + r"i\.imgur\.com/[a-z0-9]+\.gifv?"),
    re.compile(PROTOCOL_RAW_REGEX + r"redgifs\.com/watch/[a-z]+"),
]


async def redqu(
    session: aiohttp.ClientSession,
    subreddit: str,
    s: str = "t",
    t: str = "w",
    *,
    in_bot_context: bool = False,
):
    async with session.get(
        REDDIT_URL
        + f"/r/{subreddit}/"
        + CONTENT_CATEGORY_KEY_MAPPINGS.get(s[:1], "top")
        + ".rss",
        params={"t": TIME_KEY_MAPPINGS.get(t[:1], "week")},
    ) as response:
        body = await response.text()

        for regex in IMAGE_MATCH_REGEXES + (
            CLI_SPECIFIC_MATCH_REGEXES if in_bot_context else []
        ):
            for match in regex.finditer(body):
                yield match.group(0)


async def __main__(*args):
    session = aiohttp.ClientSession(headers=SESSION_HEADERS)

    urls = []

    async for url in redqu(session, *args):
        urls.append(url)

    await session.close()
    return urls


if __name__ == "__main__":
    args = sys.argv[1:]

    loop = asyncio.new_event_loop()

    if len(args) < 4:
        exit(
            subprocess.run(
                ("mpv", *loop.run_until_complete(__main__(*args)))
            ).returncode
        )

    print(HELP_TEXT)
    exit(1)
