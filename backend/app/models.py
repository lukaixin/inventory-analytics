from __future__ import annotations
import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase): pass
class DatasetSeries(Base):
    __tablename__="dataset_series"
    id: Mapped[uuid.UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid.uuid4)
    code: Mapped[str]=mapped_column(String(100),unique=True,index=True)
    title: Mapped[str]=mapped_column(String(200))
    kind: Mapped[str]=mapped_column(String(32),index=True)
    current_version_id: Mapped[uuid.UUID|None]=mapped_column(Uuid(as_uuid=True),nullable=True)
class SourceFile(Base):
    __tablename__="source_file"
    id: Mapped[uuid.UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid.uuid4)
    filename: Mapped[str]=mapped_column(String(300))
    sha256: Mapped[str]=mapped_column(String(64),unique=True,index=True)
    evidence_level: Mapped[str]=mapped_column(String(48))
    metadata_json: Mapped[dict]=mapped_column("metadata",JSON,default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class DatasetVersion(Base):
    __tablename__="dataset_version"
    id: Mapped[uuid.UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid.uuid4)
    series_id: Mapped[uuid.UUID]=mapped_column(Uuid(as_uuid=True),ForeignKey("dataset_series.id"),index=True)
    label: Mapped[str]=mapped_column(String(200))
    schema_version: Mapped[str]=mapped_column(String(32))
    evidence_level: Mapped[str]=mapped_column(String(48))
    source_file_id: Mapped[uuid.UUID|None]=mapped_column(Uuid(as_uuid=True),ForeignKey("source_file.id"),nullable=True)
    payload: Mapped[dict]=mapped_column(JSON,default=dict)
    limitations: Mapped[list]=mapped_column(JSON,default=list)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    __table_args__=(UniqueConstraint("series_id","label",name="uq_version_series_label"),)
class ImportBatch(Base):
    __tablename__="import_batch"
    id: Mapped[uuid.UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid.uuid4)
    sha256: Mapped[str]=mapped_column(String(64),index=True)
    filename: Mapped[str]=mapped_column(String(300))
    payload: Mapped[dict]=mapped_column(JSON,default=dict)
    validation: Mapped[dict]=mapped_column(JSON,default=dict)
    status: Mapped[str]=mapped_column(String(24),index=True)
    committed_version_id: Mapped[uuid.UUID|None]=mapped_column(Uuid(as_uuid=True),ForeignKey("dataset_version.id"),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
class InventorySnapshot(Base):
    __tablename__="inventory_snapshot"
    id: Mapped[uuid.UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid.uuid4)
    version_id: Mapped[uuid.UUID]=mapped_column(Uuid(as_uuid=True),ForeignKey("dataset_version.id"),index=True)
    label: Mapped[str]=mapped_column(String(100))
    exact_date: Mapped[date]=mapped_column(Date)
    ordinal: Mapped[int]=mapped_column(Integer)
    __table_args__=(UniqueConstraint("version_id","ordinal",name="uq_snapshot_version_ordinal"),)
class InventoryItem(Base):
    __tablename__="inventory_item"
    id: Mapped[uuid.UUID]=mapped_column(Uuid(as_uuid=True),primary_key=True,default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID]=mapped_column(Uuid(as_uuid=True),ForeignKey("inventory_snapshot.id"),index=True)
    record_key: Mapped[str]=mapped_column(String(160))
    material_code: Mapped[str]=mapped_column(String(120),index=True)
    material_description: Mapped[str]=mapped_column(Text)
    pdt: Mapped[str|None]=mapped_column(String(120),nullable=True,index=True)
    customer: Mapped[str|None]=mapped_column(String(160),nullable=True,index=True)
    project: Mapped[str|None]=mapped_column(String(160),nullable=True,index=True)
    material_category: Mapped[str|None]=mapped_column(String(120),nullable=True,index=True)
    subinventory_code: Mapped[str|None]=mapped_column(String(120),nullable=True)
    quantity: Mapped[Decimal|None]=mapped_column(Numeric(20,4),nullable=True)
    unit_cost: Mapped[Decimal|None]=mapped_column(Numeric(20,4),nullable=True)
    total_cost_amount: Mapped[Decimal|None]=mapped_column(Numeric(20,4),nullable=True)
    __table_args__=(UniqueConstraint("snapshot_id","record_key",name="uq_item_snapshot_key"),)
