"""MongoDB 入库逻辑。"""

from pymongo import MongoClient

from doctor_hnyygh.items import HospitalHnyyghItem


class MongoPipeline:
    def __init__(self, mongo_uri, mongo_database, doctor_collection_name, hospital_collection_name):
        self.mongo_uri = mongo_uri
        self.mongo_database = mongo_database
        self.doctor_collection_name = doctor_collection_name
        self.hospital_collection_name = hospital_collection_name
        self.client = None
        self.database = None
        self.doctor_collection = None
        self.hospital_collection = None

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get("MONGO_URI"),
            mongo_database=crawler.settings.get("MONGO_DATABASE"),
            doctor_collection_name=crawler.settings.get("MONGO_DOCTOR_COLLECTION"),
            hospital_collection_name=crawler.settings.get("MONGO_HOSPITAL_COLLECTION"),
        )

    def open_spider(self, spider):
        self.client = MongoClient(self.mongo_uri)
        self.database = self.client[self.mongo_database]
        self.doctor_collection = self.database[self.doctor_collection_name]
        self.hospital_collection = self.database[self.hospital_collection_name]

    def close_spider(self, spider):
        if self.client:
            self.client.close()

    def process_item(self, item, spider):
        if isinstance(item, HospitalHnyyghItem):
            self.hospital_collection.replace_one({"_id": item["_id"]}, dict(item), upsert=True)
        else:
            self.doctor_collection.replace_one({"_id": item["_id"]}, dict(item), upsert=True)

        if spider is not None and getattr(spider, "logger", None) is not None:
            spider.logger.info("HNYYGH 入库成功: %s", item.get("_id", ""))
        return item
