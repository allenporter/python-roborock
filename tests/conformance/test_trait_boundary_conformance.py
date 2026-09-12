"""Conformance tests for trait boundary purity.

As defined in AGENTS.md, Traits receive only abstract communication channels
(e.g., `Channel`, `RpcChannel`) or domain models/feature flags. They must NEVER
accept raw transport sockets, IP addresses, credentials, local keys, or AES encryption keys.
"""

from __future__ import annotations

import inspect

import pytest

import roborock.devices.traits
from roborock.devices.traits import Trait
from roborock.devices.traits.v1.common import V1TraitMixin
from tests.conformance.discovery import discover_classes, to_pytest_params

FORBIDDEN_PARAMS = {
    "local_key",
    "token",
    "ip",
    "ip_address",
    "host",
    "socket",
    "transport",
    "aes_key",
    "password",
    "secret",
}


def _is_trait_class(cls: type) -> bool:
    if cls in (Trait, V1TraitMixin):
        return False
    return issubclass(cls, (Trait, V1TraitMixin)) or cls.__name__.endswith(("Trait", "Api"))


@pytest.mark.parametrize(
    "trait_cls",
    to_pytest_params(discover_classes(roborock.devices.traits, _is_trait_class)),
)
def test_trait_constructor_does_not_leak_transport_or_credentials(trait_cls: type) -> None:
    """Trait constructor parameters must never include transport sockets, IPs, or credentials."""
    sig = inspect.signature(trait_cls)
    param_names = set(sig.parameters.keys()) - {"self", "args", "kwargs"}
    violations = param_names & FORBIDDEN_PARAMS
    assert not violations, (
        f"{trait_cls.__module__}.{trait_cls.__name__}.__init__ accepts forbidden transport/credential "
        f"parameters {violations}. Per AGENTS.md, traits must receive only abstract channels or domain models."
    )
