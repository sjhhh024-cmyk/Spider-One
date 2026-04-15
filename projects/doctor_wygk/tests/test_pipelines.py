from __future__ import annotations

import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from doctor_wygk.pipelines import MongoPipeline  # noqa: E402
from scrapy.exceptions import DropItem  # noqa: E402


class FakeCollection:
    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, str], dict[str, str], bool]] = []

    def replace_one(self, selector: dict[str, str], document: dict[str, str], upsert: bool) -> None:
        self.calls.append((selector, document, upsert))


class FakeSpider:
    class Logger:
        def __init__(self) -> None:
            self.messages: list[str] = []

        def info(self, message: str, *args: object) -> None:
            self.messages.append(message % args if args else message)

    def __init__(self) -> None:
        self.logger = self.Logger()


def test_pipeline_upserts_by_document_id() -> None:
    pipeline = MongoPipeline(
        mongo_uri="mongodb://example",
        mongo_database="Doctor_Database",
        collection_name="doctor_wygk",
    )
    pipeline.collection = FakeCollection()
    spider = FakeSpider()

    item = {
        "_id": "1450269515500",
        "doctor_id": "1450269515500",
        "doctor_name": "张三",
        "hospital_name": "北京积水潭医院",
        "department_name": "脊柱外科",
    }
    result = pipeline.process_item(item, spider)

    assert result == item
    assert pipeline.collection.calls == [
        (
            {"_id": "1450269515500"},
            {
                "_id": "1450269515500",
                "doctor_id": "1450269515500",
                "doctor_name": "张三",
                "hospital_name": "北京积水潭医院",
                "department_name": "脊柱外科",
            },
            True,
        )
    ]
    assert spider.logger.messages == ["WYGK 入库成功: 1450269515500"]


def test_pipeline_drops_item_when_required_fields_are_missing() -> None:
    pipeline = MongoPipeline(
        mongo_uri="mongodb://example",
        mongo_database="Doctor_Database",
        collection_name="doctor_wygk",
    )
    pipeline.collection = FakeCollection()
    spider = FakeSpider()

    item = {
        "_id": "1450269515500",
        "doctor_id": "1450269515500",
        "doctor_name": "张三",
        "hospital_name": "北京积水潭医院",
        "department_name": "",
    }

    with pytest.raises(DropItem, match="department_name"):
        pipeline.process_item(item, spider)

    assert pipeline.collection.calls == []
