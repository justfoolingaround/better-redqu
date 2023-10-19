import re

import aiohttp

SUBREDDIT_REGEX = re.compile(r'<a\n.+?href="/r/(.+?)/".+?>', re.S)


REDDIT_URL = "https://www.reddit.com/"


class RedditSVC:
    def __init__(self, session: aiohttp.ClientSession):
        self.ratelimit_remaining = 0
        self.session = session

    async def refresh_ratelimit(self):
        self.session.cookie_jar.clear(
            lambda cookie: cookie.domain.endswith("reddit.com")
        )

        async with self.session.get(REDDIT_URL):
            ...

        self.ratelimit_remaining = 100

    async def iter_subreddits(self, query):
        if not self.ratelimit_remaining:
            await self.refresh_ratelimit()

        async with self.session.get(
            REDDIT_URL + "svc/shreddit/subreddit-results",
            params={"query": query},
        ) as response:
            data = await response.text()

            for match in SUBREDDIT_REGEX.finditer(data):
                yield match.group(1)

        self.ratelimit_remaining -= 1


async def __main__():
    async with aiohttp.ClientSession() as session:
        svc = RedditSVC(session)

        async for subreddit in svc.iter_subreddits("ca"):
            print(subreddit)


if __name__ == "__main__":
    import asyncio

    asyncio.run(__main__())
