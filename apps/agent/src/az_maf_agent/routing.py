"""Deterministic server-owned routing; selection never grants capabilities."""

import re
from dataclasses import dataclass

from .config import Settings
from .model import Denied

COMPLEX_WORK = re.compile(
    r"\b(compare|contrast|tradeoffs?|trade-offs?|analy[sz]e|analysis)\b", re.I
)


@dataclass(frozen=True)
class RouteDecision:
    name: str
    reason: str
    settings: Settings


def resolve_route(settings, name=None):
    if name is None and settings.routing is None:
        return settings
    if settings.routing is None or name not in ("routine", "reasoning"):
        raise Denied("unapproved_model_route")
    profile = getattr(settings.routing, name)
    data = settings.model_dump()
    data.update(profile.model_dump(), routing=None)
    return Settings.model_validate(data)


def select_route(settings, text, *, reviewed_skill=None):
    policy = settings.routing
    if policy is None:
        return RouteDecision("single", "single_model", settings)
    if policy.mode != "auto":
        name, reason = policy.mode, "operator_override"
    elif reviewed_skill == "movie-research":
        name, reason = "reasoning", "reviewed_research"
    elif COMPLEX_WORK.search(text):
        name, reason = "reasoning", "comparison_or_analysis"
    else:
        name, reason = "routine", "routine_default"
    return RouteDecision(name, reason, resolve_route(settings, name))
