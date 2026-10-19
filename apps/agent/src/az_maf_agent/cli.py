"""Offline default; hosted mode sends only a bearer token, never a claimed identity."""

import argparse
import asyncio
import logging
import os
import sys

import httpx
from azure.core.exceptions import ClientAuthenticationError

from .client_auth import acquire_stage1_token
from .config import load_settings
from .core import LOCAL, Service, safe_text
from .model import Denied


def show_movie(movie):
    print(
        f"{safe_text(movie['title'])} ({movie['year'] or 'year unavailable'}) — "
        f"{safe_text(movie['id'])}; TMDB rating {movie['tmdb_rating']}/10"
    )
    print(safe_text(movie["synopsis"]))


def device_code_prompt(verification_uri, user_code, expires_on):
    print(f"Open {verification_uri} and enter code {user_code}.", file=sys.stderr)
    print(
        f"The code expires at {expires_on.astimezone().isoformat(timespec='minutes')}",
        file=sys.stderr,
    )


async def run(args):
    settings = load_settings(args.config)
    if not args.api and settings.mode != "fake":
        raise Denied("live_requires_authenticated_api")
    if args.api and (not args.api.startswith("https://") or "@" in args.api):
        raise Denied("https_api_required")
    movie_client = None
    if args.movies and not args.api:
        from .movie_mcp import MovieMCPClient

        movie_client = MovieMCPClient()
    service = None if args.api else Service(settings, movie_client=movie_client)
    client = None
    if args.api:
        token = os.environ.get("AGENT_ACCESS_TOKEN")
        if not token:
            token = acquire_stage1_token(device_code_prompt)
        client = httpx.AsyncClient(
            base_url=args.api,
            headers={"Authorization": "Bearer " + token},
            follow_redirects=False,
            timeout=settings.limits.run_seconds + 10,
        )

    async def remote(path, body=None):
        response = await client.post(path, json=body)
        if response.status_code in (401, 403):
            raise Denied(
                "authenticate_again" if response.status_code == 401 else "permission_denied"
            )
        if response.status_code != 200:
            raise Denied("api_request_failed")
        return response.json()

    try:
        session = await remote("/sessions") if client else service.create(LOCAL)
        sid, revision = session["session_id"], session["revision"]
        print("Text-only chat. /reset clears history; /quit exits. Ctrl-C cancels the active run.")
        if args.movies:
            print("Use /search QUERY or /movie tmdb_<id> for TMDB movie reads.")
            print("This product uses the TMDB API but is not endorsed or certified by TMDB.")
        while True:
            # Blocking input is only used when no model operation is active.
            try:
                text = input("> ")
            except EOFError:
                break
            if text == "/quit":
                break
            if text == "/reset":
                result = (
                    await remote(f"/sessions/{sid}/reset") if client else service.reset(LOCAL, sid)
                )
                revision = result["revision"]
                print("History reset; usage limits remain.")
                continue
            try:
                if args.movies and (text.startswith("/search ") or text.startswith("/movie ")):
                    name, arguments = (
                        ("search_movies", {"query": text[8:]})
                        if text.startswith("/search ")
                        else ("get_movie", {"catalog_id": text[7:]})
                    )
                    result = (
                        await remote(f"/sessions/{sid}/movies/{name}", arguments)
                        if client
                        else await service.movie_read(LOCAL, sid, name, arguments)
                    )
                    if name == "search_movies":
                        for movie in result["movies"]:
                            show_movie(movie)
                        if not result["movies"]:
                            print("No TMDB movies matched.")
                        if result["truncated"]:
                            print("Results truncated.")
                    elif "movie" in result:
                        show_movie(result["movie"])
                    else:
                        print("TMDB movie not found.")
                    continue
                result = (
                    await remote(f"/sessions/{sid}/chat", {"text": text, "revision": revision})
                    if client
                    else await service.chat(LOCAL, sid, text, revision)
                )
                revision = result["revision"]
                print(safe_text(result["text"]))
            except Denied as exc:
                print(exc.code, file=sys.stderr)
            except asyncio.CancelledError:
                if client:
                    # Explicit server cancellation; disconnect alone is not a cancellation receipt.
                    try:
                        await asyncio.shield(remote(f"/sessions/{sid}/cancel"))
                    except Exception:
                        print(
                            "Cancellation unconfirmed; server deadline still applies.",
                            file=sys.stderr,
                        )
                raise
    finally:
        if service:
            await service.close()
        if client:
            await client.aclose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/offline.json")
    parser.add_argument(
        "--api", help="Approved HTTPS API origin; uses an encrypted local Entra token cache"
    )
    parser.add_argument("--movies", action="store_true", help="Enable explicit movie catalog reads")
    args = parser.parse_args()
    # Do not allow third-party diagnostics to emit provider payloads.
    logging.getLogger("agent_framework").setLevel(logging.CRITICAL)
    logging.getLogger("azure").setLevel(logging.CRITICAL)
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        raise SystemExit(130)
    except (ClientAuthenticationError, Denied, OSError, ValueError, httpx.HTTPError):
        print(
            "Unable to start/continue chat; check approved configuration and authentication.",
            file=sys.stderr,
        )
        raise SystemExit(2)


if __name__ == "__main__":
    main()
