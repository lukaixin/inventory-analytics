"""Rebuild deterministic demo fixtures; never read or change legacy source data."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATES = ("2026-01-01", "2026-06-30", "2026-09-01", "2026-09-09")
CATEGORIES = ("原材料", "半成品", "成品")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def build() -> dict:
    snapshots = [
        {"key": f"demo-{day}", "label": day, "exact_date": day, "ordinal": n + 1}
        for n, day in enumerate(DATES)
    ]
    records = []
    ranges = (range(1, 61), range(1, 63), range(3, 65), range(5, 67))
    for index, identifiers in enumerate(ranges):
        for material in identifiers:
            quantity = Decimal(80 + material * 19 + index * (13 + material % 7))
            if index == 2 and material == 10:
                quantity = Decimal(0)  # Known zero, distinct from the null amount below.
            unit_cost = (Decimal("7.25") + Decimal(material % 17) * Decimal("11.50"))
            amount = quantity * unit_cost
            unknown = index == 3 and material == 66
            records.append({
                "snapshot_key": snapshots[index]["key"],
                "record_key": f"DEMO-R{material:03d}-WH{material % 4 + 1:02d}",
                "material_code": f"DEMO-M{material:03d}",
                "material_description": f"演示物料 {material:03d}",
                "pdt": f"DEMO-PDT-{chr(65 + (material // 7) % 3)}",
                "customer": f"DEMO-客户{material % 6 + 1:02d}",
                "project": f"DEMO-项目{material % 9 + 1:02d}",
                "material_category": CATEGORIES[(material // 3) % 3],
                "subinventory_code": f"DEMO-WH{material % 4 + 1:02d}",
                "quantity": f"{quantity:.2f}",
                "unit_cost": None if unknown else f"{unit_cost:.2f}",
                "total_cost_amount": None if unknown else f"{amount:.2f}",
            })
    return {
        "schema_version": "1.0",
        "domain": "inventory_detail",
        "series": {"code": "synthetic-inventory", "title": "合成库存明细"},
        "evidence_level": "SYNTHETIC_DEMO",
        "version_label": "四时点演示 v1",
        "snapshots": snapshots,
        "records": records,
    }


def validate_and_summarize(payload: dict) -> dict:
    keys = {s["key"] for s in payload["snapshots"]}
    assert len(keys) == len(payload["snapshots"])
    unique = set()
    for row in payload["records"]:
        assert row["snapshot_key"] in keys
        key = (row["snapshot_key"], row["record_key"])
        assert key not in unique
        unique.add(key)
        amount = row["total_cost_amount"]
        if amount is not None:
            assert Decimal(row["quantity"]) * Decimal(row["unit_cost"]) == Decimal(amount)
            assert Decimal(amount) >= 0
        assert row["material_code"].startswith("DEMO-")
    summaries = []
    for snapshot in payload["snapshots"]:
        rows = [r for r in payload["records"] if r["snapshot_key"] == snapshot["key"]]
        known = [Decimal(r["total_cost_amount"]) for r in rows if r["total_cost_amount"] is not None]
        summaries.append({
            "snapshot_key": snapshot["key"],
            "row_count": len(rows),
            "known_total": f"{sum(known, Decimal(0)):.2f}",
            "unknown_amount_count": len(rows) - len(known),
            "zero_amount_count": sum(v == 0 for v in known),
            "category_counts": dict(Counter(r["material_category"] for r in rows)),
        })
    return {"row_count": len(payload["records"]), "snapshots": summaries}


def main() -> None:
    payload = build()
    synthetic_path = HERE / "synthetic-inventory.json"
    write_json(synthetic_path, payload)
    example = {
        "schema_version": "1.0",
        "domain": "inventory_detail",
        "series": {"code": "synthetic-upload-demo", "title": "合成导入示例"},
        "evidence_level": "SYNTHETIC_DEMO",
        "version_label": "上传示例 v1",
        "snapshots": [payload["snapshots"][3]],
        "records": [r.copy() for r in payload["records"] if r["snapshot_key"] == "demo-2026-09-09"][:3],
    }
    example_path = HERE / "import-example.json"
    write_json(example_path, example)
    manifest = {
        "generator": "data/generate_synthetic.py",
        "evidence_level": "SYNTHETIC_DEMO",
        "unit": "演示元",
        "synthetic": {"filename": synthetic_path.name, "sha256": hashlib.sha256(synthetic_path.read_bytes()).hexdigest(), **validate_and_summarize(payload)},
        "import_example": {"filename": example_path.name, "sha256": hashlib.sha256(example_path.read_bytes()).hexdigest(), **validate_and_summarize(example)},
        "limitations": ["全部为合成样例，不代表真实客户、组织、物料或业务金额。", "最终快照有1条金额未知，known_total只能称为已知金额小计。", "未生成周转、发货成本、MWD、库龄或风险评级。"],
    }
    write_json(HERE / "synthetic-manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
