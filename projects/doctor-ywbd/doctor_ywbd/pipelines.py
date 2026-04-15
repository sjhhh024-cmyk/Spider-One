"""MongoDB 入库逻辑。"""

from pymongo import MongoClient


class MongoPipeline:
    """把所有 YWBD 记录都写入同一个集合。"""

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

    def process_item(self, item, spider):
        self.collection.replace_one({"_id": item["_id"]}, dict(item), upsert=True)
        spider.logger.info("YWBD 入库成功: %s", item.get("_id", ""))
        return item
