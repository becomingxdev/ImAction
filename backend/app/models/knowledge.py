import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class KnowledgeRecord(Base):
    """
    SQLAlchemy model representing an enterprise knowledge entry in CKA.
    Aggregates source material from Slack, Jira, and support tickets,
    storing structured metadata alongside high-dimensional semantic vectors.
    """
    __tablename__ = "knowledge_records"

    # Unique identification
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        description="Internal UUID for the knowledge record."
    )

    # Source tagging (e.g. 'slack', 'jira', 'support_ticket')
    source_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        description="Source system identifier (e.g., slack, jira, support_ticket)."
    )

    # Identifier from the source system (e.g. ticket key, slack message TS)
    external_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        description="Unique identifier from the external source system."
    )

    # The actual semantic text payload
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        description="The content of the knowledge record (slack text, ticket description, etc.)."
    )

    # High-density JSON container for original platform context (author, channel, tags, priority, status)
    meta_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        description="Platform-specific metadata stored in high-performance JSONB format."
    )

    # Semantic Vector Embedding (pgvector)
    # 1536 is standard for OpenAI embeddings. Dimension can be adapted as needed.
    embedding: Mapped[Optional[list]] = mapped_column(
        Vector(1536),
        nullable=True,
        description="High-dimensional semantic embedding vector (pgvector)."
    )

    # Resilient enterprise auditing
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        description="Timestamp when recorded locally."
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        description="Timestamp when last updated locally."
    )

    def __repr__(self) -> str:
        return f"<KnowledgeRecord(id={self.id}, source_type='{self.source_type}', external_id='{self.external_id}')>"
