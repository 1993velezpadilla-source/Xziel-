#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Evidence:
    source_id: str
    confidence: float
    state: str = "observed"
    note: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.source_id.strip():
            raise ValueError("evidence source_id must not be empty")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("evidence confidence must be within [0, 1]")
        if not self.state.strip():
            raise ValueError("evidence state must not be empty")


@dataclass
class SourceRecord:
    source_id: str
    uri: str
    provider: str = "user"
    kind: str = "reference"
    usage: str = "unspecified"
    attribution: str = ""
    sha256: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.source_id.strip():
            raise ValueError("source_id must not be empty")
        if not self.uri.strip():
            raise ValueError("source uri must not be empty")


@dataclass
class WorldEntity:
    entity_id: str
    labels: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    capabilities: set[str] = field(default_factory=set)
    evidence: list[Evidence] = field(default_factory=list)
    geometry: dict[str, Any] = field(default_factory=dict)
    coordinate_frame: str = "local"

    def validate(self) -> None:
        if not self.entity_id.strip():
            raise ValueError("entity_id must not be empty")
        for evidence in self.evidence:
            evidence.validate()

    def add_label(self, label: str) -> None:
        value = label.strip()
        if value and value not in self.labels:
            self.labels.append(value)

    def add_alias(self, alias: str) -> None:
        value = alias.strip()
        if value and value not in self.aliases:
            self.aliases.append(value)

    def add_capability(self, capability: str) -> None:
        value = capability.strip()
        if value:
            self.capabilities.add(value)

    def add_evidence(self, evidence: Evidence) -> None:
        evidence.validate()
        self.evidence.append(evidence)


@dataclass
class WorldRelation:
    relation_id: str
    subject_id: str
    predicate: str
    object_id: str
    confidence: float = 1.0
    evidence: list[Evidence] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.relation_id.strip():
            raise ValueError("relation_id must not be empty")
        if not self.subject_id.strip() or not self.object_id.strip():
            raise ValueError("relation endpoints must not be empty")
        if not self.predicate.strip():
            raise ValueError("relation predicate must not be empty")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("relation confidence must be within [0, 1]")
        for evidence in self.evidence:
            evidence.validate()


@dataclass
class WorldGraph:
    graph_id: str
    sources: dict[str, SourceRecord] = field(default_factory=dict)
    entities: dict[str, WorldEntity] = field(default_factory=dict)
    relations: dict[str, WorldRelation] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_source(self, source: SourceRecord) -> None:
        source.validate()
        if source.source_id in self.sources:
            raise ValueError(f"duplicate source_id: {source.source_id}")
        self.sources[source.source_id] = source

    def add_entity(self, entity: WorldEntity) -> None:
        entity.validate()
        if entity.entity_id in self.entities:
            raise ValueError(f"duplicate entity_id: {entity.entity_id}")
        self.entities[entity.entity_id] = entity

    def add_relation(self, relation: WorldRelation) -> None:
        relation.validate()
        if relation.relation_id in self.relations:
            raise ValueError(f"duplicate relation_id: {relation.relation_id}")
        if relation.subject_id not in self.entities:
            raise ValueError(f"unknown relation subject: {relation.subject_id}")
        if relation.object_id not in self.entities:
            raise ValueError(f"unknown relation object: {relation.object_id}")
        self.relations[relation.relation_id] = relation

    def entity(self, entity_id: str) -> WorldEntity:
        return self.entities[entity_id]

    def validate(self) -> None:
        if not self.graph_id.strip():
            raise ValueError("graph_id must not be empty")
        for source in self.sources.values():
            source.validate()
        for entity in self.entities.values():
            entity.validate()
            for evidence in entity.evidence:
                if evidence.source_id not in self.sources:
                    raise ValueError(
                        f"entity {entity.entity_id} references unknown source {evidence.source_id}"
                    )
        for relation in self.relations.values():
            relation.validate()
            if relation.subject_id not in self.entities:
                raise ValueError(f"unknown relation subject: {relation.subject_id}")
            if relation.object_id not in self.entities:
                raise ValueError(f"unknown relation object: {relation.object_id}")
            for evidence in relation.evidence:
                if evidence.source_id not in self.sources:
                    raise ValueError(
                        f"relation {relation.relation_id} references unknown source {evidence.source_id}"
                    )

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema": 1,
            "graph_id": self.graph_id,
            "sources": {key: asdict(value) for key, value in self.sources.items()},
            "entities": {
                key: {
                    **asdict(value),
                    "capabilities": sorted(value.capabilities),
                }
                for key, value in self.entities.items()
            },
            "relations": {key: asdict(value) for key, value in self.relations.items()},
            "metadata": self.metadata,
        }

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
