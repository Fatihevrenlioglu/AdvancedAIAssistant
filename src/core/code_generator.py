"""Placeholder async code generator with cancellation support."""
from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Dict


class CodeGenerator:
    """Manage code generation tasks and cancellation state."""

    def __init__(self) -> None:
        """Initialize active task storage."""
        self._tasks: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def generate(self, prompt: str, task_id: str, language: str = "python") -> AsyncGenerator[str, None]:
        """Yield simulated code-generation chunks until completion or cancellation."""
        cancellation_event = asyncio.Event()
        async with self._lock:
            self._tasks[task_id] = {
                "status": "running",
                "prompt": prompt,
                "language": language,
                "cancel_event": cancellation_event,
                "chunks_generated": 0,
            }

        chunks = [
            f"# Generated {language} code for: {prompt}\n",
            "def generated_function():\n",
            "    return 'placeholder implementation'\n",
        ]
        try:
            for index, chunk in enumerate(chunks, start=1):
                if cancellation_event.is_set():
                    async with self._lock:
                        self._tasks[task_id]["status"] = "cancelled"
                    return
                await asyncio.sleep(0.05)
                async with self._lock:
                    self._tasks[task_id]["chunks_generated"] = index
                yield chunk
            async with self._lock:
                self._tasks[task_id]["status"] = "completed"
        except Exception:
            async with self._lock:
                self._tasks[task_id]["status"] = "failed"
            raise

    def cancel(self, task_id: str) -> bool:
        """Cancel an active generation task if it exists."""
        task = self._tasks.get(task_id)
        if task is None:
            return False
        cancel_event = task.get("cancel_event")
        if isinstance(cancel_event, asyncio.Event):
            cancel_event.set()
            task["status"] = "cancelled"
            return True
        return False

    async def get_status(self, task_id: str) -> Dict[str, Any]:
        """Return status information for a generation task."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return {"task_id": task_id, "status": "not_found"}
            return {
                "task_id": task_id,
                "status": task.get("status"),
                "language": task.get("language"),
                "chunks_generated": task.get("chunks_generated", 0),
            }
