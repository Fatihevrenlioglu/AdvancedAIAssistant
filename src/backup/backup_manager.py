"""Backup and restore management helpers."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List


class BackupManager:
    """Create and manage simulated backup metadata files."""

    def __init__(self, backup_dir: str = "./backups", retention_days: int = 30) -> None:
        """Initialize backup storage settings."""
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def create_backup(self, db_name: str) -> str:
        """Create a simulated backup metadata file and return its path."""
        timestamp = datetime.now(timezone.utc)
        backup_name = f"{db_name}_{timestamp.strftime('%Y%m%d%H%M%S')}.json"
        backup_path = self.backup_dir / backup_name
        payload = {
            "db_name": db_name,
            "created_at": timestamp.isoformat(),
            "status": "created",
        }
        await asyncio.to_thread(backup_path.write_text, json.dumps(payload, indent=2), "utf-8")
        return str(backup_path)

    async def restore_backup(self, backup_file: str, db_name: str) -> bool:
        """Validate a backup file and simulate restore success."""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            return False
        content = await asyncio.to_thread(backup_path.read_text, "utf-8")
        payload = json.loads(content)
        if payload.get("db_name") != db_name:
            return False
        restore_marker = self.backup_dir / f"{db_name}_restored.json"
        await asyncio.to_thread(
            restore_marker.write_text,
            json.dumps({"db_name": db_name, "restored_from": str(backup_path), "restored_at": datetime.now(timezone.utc).isoformat()}, indent=2),
            "utf-8",
        )
        return True

    async def cleanup_old_backups(self) -> int:
        """Remove backups older than the retention period."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        removed = 0
        for backup_file in self.backup_dir.glob("*.json"):
            modified = datetime.fromtimestamp(backup_file.stat().st_mtime, tz=timezone.utc)
            if modified < cutoff:
                await asyncio.to_thread(backup_file.unlink)
                removed += 1
        return removed

    async def list_backups(self) -> List[Dict[str, Any]]:
        """List available backup metadata files."""
        backups: List[Dict[str, Any]] = []
        for backup_file in sorted(self.backup_dir.glob("*.json")):
            content = await asyncio.to_thread(backup_file.read_text, "utf-8")
            payload = json.loads(content)
            payload["file"] = str(backup_file)
            backups.append(payload)
        return backups
