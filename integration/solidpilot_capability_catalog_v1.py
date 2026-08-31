from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .aidesigner_assets import CAPABILITIES, CapabilitySpec


@dataclass(frozen=True)
class CapabilityRecord:
    capability_id: str
    tool: str
    status: str
    source: str
    input_schema: Mapping[str, Any] | None = None
    evidence_required: str = "live semantic verification"


class SolidPilotCapabilityCatalogV1:
    """Capability lifecycle facade: proven evidence plus backend candidates.

    Discovery never promotes a capability to proven. This mirrors the
    Ai_Designer separation between discovery, lowering and evidence promotion.
    """

    def __init__(self, proven: Sequence[CapabilitySpec] = CAPABILITIES):
        self._records: dict[str, CapabilityRecord] = {
            item.capability_id: CapabilityRecord(
                capability_id=item.capability_id,
                tool=item.tool,
                status="proven",
                source=item.evidence,
                input_schema=None,
            )
            for item in proven
        }

    @property
    def records(self) -> tuple[CapabilityRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda item: item.capability_id))

    def get(self, capability_id: str) -> CapabilityRecord | None:
        return self._records.get(capability_id)

    def add_candidate(self, *, capability_id: str, tool: str, input_schema: Mapping[str, Any] | None = None) -> CapabilityRecord:
        existing = self._records.get(capability_id)
        if existing is not None and existing.status == "proven":
            return existing
        record = CapabilityRecord(
            capability_id=capability_id,
            tool=tool,
            status="candidate",
            source="SolidPilot backend discovery",
            input_schema=input_schema,
        )
        self._records[capability_id] = record
        return record

    async def discover_from_session(self, session: Any) -> tuple[CapabilityRecord, ...]:
        """Discover backend tools as candidates without inventing semantic mappings."""
        if not hasattr(session, "list_tools"):
            raise TypeError("session must provide list_tools() for capability discovery")
        page = await session.list_tools()
        tools = getattr(page, "tools", page)
        for item in tools or ():
            name = getattr(item, "name", None)
            if not isinstance(name, str) or not name.strip():
                continue
            schema = getattr(item, "inputSchema", None) or getattr(item, "input_schema", None)
            capability_id = f"solidpilot.tool.{name.strip()}"
            self.add_candidate(capability_id=capability_id, tool=name.strip(), input_schema=schema if isinstance(schema, Mapping) else None)
        return self.records

    def require_proven(self, capability_id: str) -> CapabilityRecord:
        record = self._records.get(capability_id)
        if record is None:
            raise KeyError(f"unknown capability: {capability_id}")
        if record.status != "proven":
            raise ValueError(f"capability is not proven: {capability_id} (status={record.status})")
        return record


__all__ = ["CapabilityRecord", "SolidPilotCapabilityCatalogV1"]
