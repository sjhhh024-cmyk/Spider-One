"""MongoDB 入库逻辑。"""

from __future__ import annotations

from pymongo import MongoClient
from scrapy.exceptions import DropItem


class MongoPipeline:
    """把所有 WYGK 医生记录都写入同一个集合。"""

    required_fields = ("doctor_name", "hospital_name", "department_name")

    def __init__(self, mongo_uri, mongo_database, collection_name):
        self.mongo_uri = mongo_uri
        self.mongo_database = mongo_database
        self.collection_name = collection_name
        self.client = None
        self.database = None
        self.collection = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get("MONGO_URI"),
            mongo_database=crawler.settings.get("MONGO_DATABASE"),
            collection_name=crawler.settings.get("MONGO_DOCTOR_COLLECTION"),
        )

    def open_spider(self, spider):
        self.client = MongoClient(self.mongo_uri)
        self.database = self.client[self.mongo_database]
        self.collection = self.database[self.collection_name]

    def close_spider(self, spider):
        if self.client:
            self.client.close()

    def validate_required_fields(self, item: dict[str, object]) -> None:
        missing_fields = [
            field_name for field_name in self.required_fields if not str(item.get(field_name) or "").strip()
        ]
        if not missing_fields:
            return
        raise DropItem(f"缺少必填字段: {', '.join(missing_fields)}")

    def process_item(self, item, spider):
        document = dict(item)
        self.validate_required_fields(document)
        self.collection.replace_one({"_id": document["_id"]}, document, upsert=True)
        spider.logger.info("WYGK 入库成功: %s", item.get("_id", ""))
        return item
