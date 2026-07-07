"""Batch request validation helpers."""
from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, List, Tuple, Type

from pydantic import BaseModel, ValidationError


class BatchValidator:
    """Validate and process batch payloads."""

    @staticmethod
    def validate_batch_size(items: List[Any], max_size: int = 100) -> None:
        """Validate that the batch does not exceed the configured size."""
        if len(items) > max_size:
            raise ValueError(f"Batch size exceeds maximum of {max_size} items.")

    @staticmethod
    async def validate_batch_items(
        items: List[Dict[str, Any]],
        schema: Type[BaseModel],
    ) -> Tuple[List[BaseModel], List[Dict[str, Any]]]:
        """Validate each batch item and collect any validation errors."""
        valid_items: List[BaseModel] = []
        errors: List[Dict[str, Any]] = []
        for index, item in enumerate(items):
            try:
                valid_items.append(schema.model_validate(item))
            except ValidationError as exc:
                errors.append({"index": index, "errors": exc.errors(), "item": item})
        return valid_items, errors

    @staticmethod
    async def process_batch(
        items: List[Dict[str, Any]],
        processor: Callable[[BaseModel], Any],
        schema: Type[BaseModel],
        max_size: int = 100,
    ) -> Dict[str, Any]:
        """Validate a batch and process valid items with the supplied processor."""
        BatchValidator.validate_batch_size(items, max_size=max_size)
        valid_items, errors = await BatchValidator.validate_batch_items(items, schema)
        results: List[Any] = []
        for index, item in enumerate(valid_items):
            try:
                outcome = processor(item)
                if inspect.isawaitable(outcome):
                    outcome = await outcome
                results.append({"index": index, "result": outcome})
            except Exception as exc:
                errors.append(
                    {
                        "index": index,
                        "errors": ["Processing failed for this item."],
                        "error_type": type(exc).__name__,
                        "item": item.model_dump(),
                    }
                )
        return {
            "processed": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors,
        }
