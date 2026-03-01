from __future__ import annotations

from urllib.parse import quote_plus


class BookingLinkTool:
    @staticmethod
    def run(query: str) -> dict:
        encoded = quote_plus(query.strip())
        return {
            "query": query.strip(),
            "links": [
                {
                    "label": "Google Maps",
                    "url": f"https://www.google.com/maps/search/{encoded}",
                },
                {
                    "label": "OpenTable",
                    "url": f"https://www.opentable.com/s?term={encoded}",
                },
                {
                    "label": "Calendly",
                    "url": f"https://calendly.com/search?query={encoded}",
                },
            ],
        }

