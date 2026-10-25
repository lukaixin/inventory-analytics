from __future__ import annotations
import hashlib, json
from pathlib import Path
from sqlalchemy import select
from .db import SessionLocal
from .models import DatasetSeries, DatasetVersion, SourceFile
from .services import commit_batch, preview

ROOT = Path(__file__).resolve().parents[2]

def seed_legacy(db):
    path = ROOT / "data" / "private" / "legacy-reviewed.json"
    if not path.exists(): return False
    content = path.read_bytes(); sha = hashlib.sha256(content).hexdigest()
    if db.scalar(select(SourceFile).where(SourceFile.sha256 == sha)): return False
    payload = json.loads(content)
    sf = SourceFile(filename=path.name, sha256=sha, evidence_level="SOURCE_TRANSCRIPTION_DRAFT", metadata_json={"source_kind": payload.get("metadata", {}).get("source_kind"), "limitations": payload.get("metadata", {}).get("limitations", [])})
    db.add(sf); db.flush()
    series = DatasetSeries(code="legacy-transcription", title="历史转录汇总", kind="legacy")
    db.add(series); db.flush()
    dv = DatasetVersion(series_id=series.id, label="V4截图转录初稿", schema_version="legacy_v4_1", evidence_level="SOURCE_TRANSCRIPTION_DRAFT", source_file_id=sf.id, payload=payload, limitations=payload.get("metadata", {}).get("limitations", []))
    db.add(dv); db.flush(); series.current_version_id=dv.id; db.commit(); return True

def seed_management(db):
    """Create the immutable management demo once; never overwrite an old version."""
    path = ROOT / "data" / "management-demo.json"
    if not path.exists(): return False
    content = path.read_bytes(); sha = hashlib.sha256(content).hexdigest(); payload = json.loads(content)
    existing = db.scalar(select(DatasetVersion).join(SourceFile, DatasetVersion.source_file_id == SourceFile.id).where(SourceFile.sha256 == sha))
    if existing: return False
    series_code = payload.get("series", {}).get("code", "management-demo-v6")
    series_title = payload.get("series", {}).get("title", "库存管理合成演示")
    series = db.scalar(select(DatasetSeries).where(DatasetSeries.code == series_code))
    if not series:
        series = DatasetSeries(code=series_code, title=series_title, kind="management_demo")
        db.add(series); db.flush()
    sf = SourceFile(filename=path.name, sha256=sha, evidence_level="SYNTHETIC_MANAGEMENT_DEMO", metadata_json={"source_kind":"deterministic_synthetic_management_demo","limitations":["合成管理演示，不代表真实V6业务数据"]})
    db.add(sf); db.flush()
    label = payload.get("version_label", "V6功能重构合成管理演示")
    dv = DatasetVersion(series_id=series.id, label=label, schema_version="management_demo_v1", evidence_level="SYNTHETIC_MANAGEMENT_DEMO", source_file_id=sf.id, payload=payload, limitations=payload.get("limitations", ["合成管理演示，不代表真实V6业务数据"]))
    db.add(dv); db.flush()
    if series.current_version_id is None: series.current_version_id=dv.id
    db.commit(); return True

def main():
    db=SessionLocal()
    try:
        legacy=seed_legacy(db); path=ROOT / "data" / "synthetic-inventory.json"; synthetic=False
        if path.exists():
            batch=preview(db, path.name, path.read_bytes())
            if batch.status=="preview": commit_batch(db,batch,True); synthetic=True
        management=seed_management(db)
        print(json.dumps({"legacy_seeded":legacy,"synthetic_imported":synthetic,"management_seeded":management},ensure_ascii=False))
    finally: db.close()

if __name__=="__main__": main()
