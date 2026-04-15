"""MongoDB 入库逻辑。"""

from pymongo import MongoClient

from doctor_circle.items import CircleItem, DoctorItem


class MongoPipeline:
    """把圈子和医生数据分别写入 MongoDB。"""

    def __init__(self, mongo_uri, mongo_database, circle_collection, doctor_collection):
        self.mongo_uri = mongo_uri
        self.mongo_database = mongo_database
        self.circle_collection_name = circle_collection
        self.doctor_collection_name = doctor_collection
        self.client = None
        self.database = None
        self.circle_collection = None
        self.doctor_collection = None

    @classmethod
    def from_crawler(cls, crawler):
        """从 Scrapy settings 里读取 MongoDB 配置。"""

        return cls(
            mongo_uri=crawler.settings.get("MONGO_URI"),
            mongo_database=crawler.settings.get("MONGO_DATABASE"),
            circle_collection=crawler.settings.get("MONGO_CIRCLE_COLLECTION"),
            doctor_collection=crawler.settings.get("MONGO_DOCTOR_COLLECTION"),
        )

    def open_spider(self, spider):
        """打开 spider 时初始化 MongoDB 连接。"""

        self.client = MongoClient(self.mongo_uri)
        self.database = self.client[self.mongo_database]
        self.circle_collection = self.database[self.circle_collection_name]
        self.doctor_collection = self.database[self.doctor_collection_name]

    def close_spider(self, spider):
        """关闭 spider 时释放 MongoDB 连接。"""

        if self.client:
            self.client.close()

    def process_item(self, item, spider):
        """按 item 类型分别写入不同集合。"""

        if isinstance(item, CircleItem):
            self.circle_collection.replace_one({"_id": item["_id"]}, dict(item), upsert=True)
            spider.logger.info("圈子入库成功: %s", item.get("_id", ""))
            return item

        if isinstance(item, DoctorItem):
            self.doctor_collection.replace_one({"_id": item["_id"]}, dict(item), upsert=True)
            spider.logger.info("医生入库成功: %s", item.get("_id", ""))
            return item

        return item
