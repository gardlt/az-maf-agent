"""Service-owned identity and denial contracts."""

from dataclasses import dataclass


class Denied(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class WorkloadIdentity:
    subject: str
    role: str
