"""Offline default; hosted mode sends only a bearer token, never a claimed identity."""

import argparse
import asyncio
import json
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
    if args.skill and not args.api:
        raise Denied("skill_requires_configured_api")
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

    async def remote(path, body=None, method="POST"):
        response = await client.request(method, path, json=body)
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
            print("Credits: https://github.com/gardlt/az-maf-agent/blob/main/docs/credits.md")
        if client:
            print(
                "Memory: /memory; /remember CATEGORY VALUE explicitly consents to a 30-day save/correction;"
            )
            print(
                "/forget ID or /forget all removes saved preferences. Categories: preferred_genre, preferred_language."
            )
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
                if text == "/memory" or text.startswith(("/remember ", "/forget ")):
                    if not client:
                        raise Denied("memory_requires_configured_api")
                    path = f"/sessions/{sid}/memory"
                    if text == "/memory":
                        print(json.dumps(await remote(path, method="GET"), indent=2))
                    elif text.startswith("/forget "):
                        record_id = text[8:].strip()
                        if not record_id or (record_id != "all" and len(record_id) != 36):
                            raise Denied("memory_invalid")
                        print(
                            json.dumps(
                                await remote(
                                    path if record_id == "all" else path + "/" + record_id,
                                    method="DELETE",
                                )
                            )
                        )
                    else:
                        parts = text.split()
                        if len(parts) != 3:
                            raise Denied("memory_invalid")
                        _, category, value = parts
                        from .memory import Preference

                        try:
                            preference = Preference(category=category, value=value)
                        except ValueError:
                            raise Denied("memory_invalid") from None
                        existing = await remote(path, method="GET")
                        record = next(
                            (r for r in existing["memories"] if r["category"] == category), None
                        )
                        body = {
                            **preference.model_dump(),
                            "consent": True,
                            "expected_generation": existing["generation"],
                        }
                        if record:
                            body["expected_revision"] = record["revision"]
                        saved = await remote(
                            path + "/" + record["id"] if record else path,
                            body,
                            method="PUT" if record else "POST",
                        )
                        print(json.dumps(saved, indent=2))
                    continue
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
                    await remote(
                        f"/sessions/{sid}/chat",
                        {
                            "text": text,
                            "revision": revision,
                            "skill_id": args.skill,
                            "skill_version": args.skill_version if args.skill else None,
                        },
                    )
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
    parser.add_argument("--skill", choices=["movie-research", "movie-night"])
    parser.add_argument("--skill-version", default="1.0.0")
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
