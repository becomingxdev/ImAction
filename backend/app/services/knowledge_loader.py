import os
import json
import logging
from typing import List, Dict, Any
from app.schemas.knowledge import NormalizedKnowledgeRecord

logger = logging.getLogger("imaction")


class KnowledgeLoaderService:
    """
    Service responsible for loading mock enterprise data files,
    normalizing their schemas into a standard format, merging them,
    and returning them ordered chronologically.
    """

    def __init__(self) -> None:
        # Resolve data folder dynamically relative to this service file
        self.data_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data")
        )
        self.slack_path = os.path.join(self.data_dir, "slack_messages.json")
        self.jira_path = os.path.join(self.data_dir, "jira_tickets.json")
        self.support_path = os.path.join(self.data_dir, "support_tickets.json")

    def _read_json_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Reads a JSON file resiliently, logging errors if missing or malformed.
        """
        if not os.path.exists(file_path):
            logger.warning(f"Knowledge file not found: {file_path}. Skipping.")
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    logger.error(f"Invalid JSON root in {file_path}. Expected a list.")
                    return []
                return data
        except json.JSONDecodeError as jde:
            logger.error(f"Malformed JSON in {file_path}: {jde}. Skipping.")
            return []
        except Exception as e:
            logger.error(f"Unexpected error reading {file_path}: {e}. Skipping.")
            return []

    def _normalize_slack(self, raw: Dict[str, Any]) -> NormalizedKnowledgeRecord:
        """
        Maps a raw Slack message to the standard NormalizedKnowledgeRecord schema.
        """
        channel = raw.get("channel", "unknown-channel")
        username = raw.get("username", raw.get("user", "unknown-user"))
        text = raw.get("text", "")
        ts = raw.get("ts", "")

        return NormalizedKnowledgeRecord(
            source="slack",
            title=f"Slack Message in #{channel} by {username}",
            content=text,
            timestamp=ts,
            raw_metadata={
                "channel": channel,
                "user": raw.get("user"),
                "username": username
            }
        )

    def _normalize_jira(self, raw: Dict[str, Any]) -> NormalizedKnowledgeRecord:
        """
        Maps a raw Jira ticket to the standard NormalizedKnowledgeRecord schema.
        """
        key = raw.get("key", "UNKNOWN-KEY")
        fields = raw.get("fields", {})
        summary = fields.get("summary", "")
        description = fields.get("description", "")
        created = fields.get("created", "")

        status_info = fields.get("status", {})
        status_name = status_info.get("name") if isinstance(status_info, dict) else "unknown"

        priority_info = fields.get("priority", {})
        priority_name = priority_info.get("name") if isinstance(priority_info, dict) else "unknown"

        assignee_info = fields.get("assignee", {})
        assignee_name = assignee_info.get("name") if isinstance(assignee_info, dict) else None

        return NormalizedKnowledgeRecord(
            source="jira",
            title=f"Jira [{key}]: {summary}",
            content=f"Summary: {summary}\n\nDescription: {description}",
            timestamp=created,
            raw_metadata={
                "key": key,
                "status": status_name,
                "priority": priority_name,
                "assignee": assignee_name
            }
        )

    def _normalize_support(self, raw: Dict[str, Any]) -> NormalizedKnowledgeRecord:
        """
        Maps a raw support ticket to the standard NormalizedKnowledgeRecord schema.
        """
        ticket_id = raw.get("ticket_id", "UNKNOWN-TICKET")
        subject = raw.get("subject", "")
        body = raw.get("body", "")
        created_at = raw.get("created_at", "")

        return NormalizedKnowledgeRecord(
            source="support_ticket",
            title=f"Support Ticket #{ticket_id}: {subject}",
            content=f"Subject: {subject}\n\nBody: {body}",
            timestamp=created_at,
            raw_metadata={
                "ticket_id": ticket_id,
                "customer_email": raw.get("customer_email"),
                "status": raw.get("status"),
                "priority": raw.get("priority")
            }
        )

    def load_and_merge_all(self) -> List[NormalizedKnowledgeRecord]:
        """
        Loads all raw mock datasets, normalizes them, and merges them
        into a chronologically sorted list (newest first).
        """
        logger.info("Starting ingestion of enterprise knowledge records...")
        normalized_records: List[NormalizedKnowledgeRecord] = []

        # 1. Load and normalize Slack messages
        slack_raw = self._read_json_file(self.slack_path)
        logger.info(f"Loaded {len(slack_raw)} raw Slack messages.")
        for item in slack_raw:
            try:
                normalized_records.append(self._normalize_slack(item))
            except Exception as e:
                logger.error(f"Failed to normalize Slack message {item.get('ts')}: {e}")

        # 2. Load and normalize Jira tickets
        jira_raw = self._read_json_file(self.jira_path)
        logger.info(f"Loaded {len(jira_raw)} raw Jira tickets.")
        for item in jira_raw:
            try:
                normalized_records.append(self._normalize_jira(item))
            except Exception as e:
                logger.error(f"Failed to normalize Jira ticket {item.get('key')}: {e}")

        # 3. Load and normalize Support tickets
        support_raw = self._read_json_file(self.support_path)
        logger.info(f"Loaded {len(support_raw)} raw Support tickets.")
        for item in support_raw:
            try:
                normalized_records.append(self._normalize_support(item))
            except Exception as e:
                logger.error(f"Failed to normalize Support ticket {item.get('ticket_id')}: {e}")

        # 4. Sort records chronologically (newest first)
        # Use timestamp string sorting since they are ISO-8601 formatted
        normalized_records.sort(key=lambda x: x.timestamp, reverse=True)

        logger.info(f"Merged and normalized a total of {len(normalized_records)} knowledge records.")
        return normalized_records


# Singleton instance for simple endpoint lifecycle utilization
knowledge_loader = KnowledgeLoaderService()
