from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Literal

OMDB_BASE_URL = "http://www.omdbapi.com/"


def lookup(
    title: str, kind_hint: Literal["movie", "tv"] | None = None
) -> dict | None:
    """Query OMDB for a movie or TV show. Returns normalized metadata or None.

    Returns None if no API key is configured, the lookup failed, or no match was found.
    """
    api_key = os.environ.get("OMDB_API_KEY", "").strip()
    if not api_key:
        return None

    params: dict[str, str] = {"apikey": api_key, "t": title, "plot": "short"}
    if kind_hint == "tv":
        params["type"] = "series"
    elif kind_hint == "movie":
        params["type"] = "movie"

    url = OMDB_BASE_URL + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None

    if data.get("Response") != "True":
        return None
    return _normalize(data)


def _normalize(d: dict) -> dict:
    raw_poster = d.get("Poster", "")
    return {
        "title": d.get("Title", "").strip(),
        "year": _parse_year(d.get("Year", "")),
        "type": d.get("Type", "movie"),
        "imdb_id": d.get("imdbID", ""),
        "imdb_rating": d.get("imdbRating", ""),
        "runtime": d.get("Runtime", ""),
        "poster": raw_poster if raw_poster and raw_poster != "N/A" else "",
        "directors": _split_csv(d.get("Director", "")),
        "genres": _split_csv(d.get("Genre", "")),
        "actors": _split_csv(d.get("Actors", "")),
        "plot": d.get("Plot", ""),
    }


def _split_csv(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip() and x.strip() != "N/A"]


def _parse_year(s: str) -> int | None:
    if not s:
        return None
    try:
        return int(s[:4])
    except ValueError:
        return None
