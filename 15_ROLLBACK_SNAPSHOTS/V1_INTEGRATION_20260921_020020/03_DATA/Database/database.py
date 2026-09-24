from __future__ import annotations

from copy import deepcopy
from typing import Any


class Database:
    """Small in-process database abstraction for KAIRO."""

    def __init__(self) -> None:
        self._collections: dict[
            str,
            dict[str, dict[str, Any]],
        ] = {}

    def create_collection(
        self,
        name: str,
    ) -> None:

        if not name:
            raise ValueError(
                "Collection name is required"
            )

        self._collections.setdefault(
            name,
            {},
        )

    def insert(
        self,
        collection: str,
        key: str,
        value: dict[str, Any],
    ) -> dict[str, Any]:

        self.create_collection(
            collection
        )

        if not key:
            raise ValueError(
                "Record key is required"
            )

        self._collections[
            collection
        ][key] = deepcopy(value)

        return deepcopy(value)

    def get(
        self,
        collection: str,
        key: str,
    ) -> dict[str, Any] | None:

        records = self._collections.get(
            collection,
            {},
        )

        value = records.get(key)

        if value is None:
            return None

        return deepcopy(value)

    def delete(
        self,
        collection: str,
        key: str,
    ) -> bool:

        records = self._collections.get(
            collection,
            {},
        )

        return (
            records.pop(
                key,
                None,
            )
            is not None
        )

    def list_collection(
        self,
        collection: str,
    ) -> list[dict[str, Any]]:

        records = self._collections.get(
            collection,
            {},
        )

        return [
            deepcopy(value)
            for value in records.values()
        ]

    def collections(self) -> list[str]:
        return sorted(
            self._collections
        )

    def health(self) -> dict:
        return {
            "status": "ONLINE",
            "collections": len(
                self._collections
            ),
            "records": sum(
                len(records)
                for records
                in self._collections.values()
            ),
        }
