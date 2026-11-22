from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base


class SampleVoid(Base):
    """A footfall sample whose counts were recorded incorrectly.

    The original observation is kept for traceability; only its status is
    excluded from live analysis.  One row per sample makes re-voiding
    idempotent.
    """

    __tablename__ = 'sample_voids'

    id: Mapped[int] = mapped_column(primary_key=True)
    sample_id: Mapped[int] = mapped_column(
        ForeignKey('footfall_samples.id'), unique=True, index=True
    )
    reason: Mapped[str] = mapped_column(String(500))
    voided_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    prior_status: Mapped[str] = mapped_column(String(20), default='valid')
    prior_issue_reason: Mapped[str] = mapped_column(String(255), default='')


class AnalysisInvalidation(Base):
    """Marks an analysis run as containing a voided sample.

    The run itself is kept intact for audit, but it can no longer produce a
    leasing brief.
    """

    __tablename__ = 'analysis_invalidations'

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey('analysis_runs.id'), unique=True, index=True
    )
    sample_id: Mapped[int] = mapped_column(ForeignKey('footfall_samples.id'))
    reason: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class BriefInvalidation(Base):
    """Retraction of an issued brief, or shutting down a contaminated draft.

    ``kind`` is ``retracted`` for briefs that had already been issued and
    ``blocked`` for drafts that must no longer be issued.  One row per brief
    keeps repeated void attempts from recording duplicate retractions.
    """

    __tablename__ = 'brief_invalidations'

    id: Mapped[int] = mapped_column(primary_key=True)
    brief_id: Mapped[int] = mapped_column(ForeignKey('briefs.id'), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(20), default='retracted')
    reason: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
