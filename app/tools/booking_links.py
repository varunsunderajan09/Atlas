from __future__ import annotations

from urllib.parse import quote_plus


class BookingLinksTool:
    def run(
        self,
        query: str,
        date: str | None = None,
        time: str | None = None,
        party_size: int | None = None,
    ) -> dict:
        term = quote_plus(query.strip())
        links = [
            {
                "label": "OpenTable",
                "url": f"https://www.opentable.com/s?term={term}",
            },
            {
                "label": "Google Maps",
                "url": f"https://www.google.com/maps/search/{term}",
            },
        ]
        if date or time or party_size:
            extras = []
            if date:
                extras.append(f"dateTime={quote_plus(date)}")
            if time:
                extras.append(f"time={quote_plus(time)}")
            if party_size:
                extras.append(f"covers={party_size}")
            suffix = "&".join(extras)
            links[0]["url"] = f"{links[0]['url']}&{suffix}" if suffix else links[0]["url"]
        return {"query": query, "links": links}

