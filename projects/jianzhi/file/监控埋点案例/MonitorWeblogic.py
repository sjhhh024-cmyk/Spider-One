import redis
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime


class WebsiteRedisStorage:
    """
    监控状态调用的方法
    """

    # 初始化连接
    def __init__(self):
        """
        初始化Redis连接
        """
        try:
            self.redis_client = redis.Redis(
                # 本地测试地址
                host='localhost',
                port=6379,
                db=11,
                password=None,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self.redis_client.ping()
            logging.info("Redis连接成功")
        except Exception as e:
            logging.error(f"Redis连接失败: {e}")
            raise

    def _get_unique_key(self, webname: str, biz_type: str = None) -> str:
        """生成唯一键（WebName:BizType）"""
        if biz_type:
            return f"{webname}:{biz_type}"
        return webname

    def store_website_data(self, province: str, city: str, website_data: Dict) -> bool:
        """
        存储网站数据到Redis

        纯净的三级结构：
        一级：website_data（固定）
        二级：省级名称
        三级：市级名称

        去重逻辑：使用 WebName + BizType 作为联合唯一键
        """
        try:
            webname = website_data["WebName"]
            biz_type = website_data.get("BizType", "")

            level3_key = f"website_data_v3:{province}:{city}"

            storage_data = website_data.copy()
            storage_data["_province"] = province
            storage_data["_city"] = city
            if "BizType" not in storage_data:
                storage_data["BizType"] = biz_type

            website_json = json.dumps(storage_data, ensure_ascii=False)

            unique_key = self._get_unique_key(webname, biz_type)
            result = self.redis_client.hset(level3_key, unique_key, website_json)

            if result > 0:
                logging.info(f"成功存储: website_data_v3/{province}/{city}/{unique_key}")
                return True
            else:
                logging.info(f"数据已存在，已更新: website_data_v3/{province}/{city}/{unique_key}")
                return True

        except Exception as e:
            logging.error(f"存储失败: {province}/{city} - {e}")
            return False

    def update_website_data(self, province: str, city: str, webname: str, updates: Dict) -> bool:
        """
        更新网站数据

        如果网站存在则更新（完全替换），如果不存在则创建

        去重逻辑：使用 WebName + BizType 作为联合唯一键
        """
        try:
            level3_key = f"website_data_v3:{province}:{city}"

            biz_type = updates.get("BizType", "")

            website_data = {
                "WebName": webname,
                "BizType": biz_type,
                "WasSuccessful": updates.get("WasSuccessful", 0),
                "WebsiteError": updates.get("WebsiteError", 0),
                "HasContent": updates.get("HasContent", 0),
                "HasNewData": updates.get("HasNewData", 0),
                "IsValidData": updates.get("IsValidData", 0),
                **updates
            }
            website_data["_province"] = province
            website_data["_city"] = city
            website_data["_last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            website_json = json.dumps(website_data, ensure_ascii=False)

            unique_key = self._get_unique_key(webname, biz_type)
            self.redis_client.hset(level3_key, unique_key, website_json)

            logging.info(f"成功更新网站: website_data_v3/{province}/{city}/{unique_key}")
            return True

        except Exception as e:
            logging.error(f"更新/创建网站失败: {province}/{city}/{webname} - {e}")
            return False

    def get_website_data(self, province: str, city: str, webname: str, biz_type: str = None) -> Optional[Dict]:
        """
        获取特定网站数据

        去重逻辑：使用 WebName + BizType 作为联合唯一键
        """
        try:
            level3_key = f"website_data_v3:{province}:{city}"

            unique_key = self._get_unique_key(webname, biz_type)

            try:
                key_type = self.redis_client.type(level3_key)

                if key_type == 'hash':
                    website_json = self.redis_client.hget(level3_key, unique_key)

                    if website_json:
                        try:
                            website_data = json.loads(website_json)
                            return website_data
                        except json.JSONDecodeError as e:
                            logging.warning(f"JSON解析失败: {website_json} - {e}")
                            return None

                    if biz_type:
                        for potential_key in self.redis_client.hkeys(level3_key):
                            if potential_key.startswith(f"{webname}:"):
                                website_json = self.redis_client.hget(level3_key, potential_key)
                                if website_json:
                                    try:
                                        website_data = json.loads(website_json)
                                        return website_data
                                    except json.JSONDecodeError:
                                        continue
                    return None
                elif key_type == 'set':
                    website_jsons = self.redis_client.smembers(level3_key)

                    for website_json in website_jsons:
                        try:
                            website_data = json.loads(website_json)
                            if website_data.get("WebName") == webname:
                                if not biz_type or website_data.get("BizType") == biz_type:
                                    return website_data
                        except json.JSONDecodeError as e:
                            logging.warning(f"JSON解析失败: {website_json} - {e}")
                            continue

                    return None
                else:
                    logging.warning(f"键类型不支持: {key_type} for {level3_key}")
                    return None
            except Exception as type_error:
                logging.warning(f"检查键类型失败: {type_error}")
                try:
                    website_json = self.redis_client.hget(level3_key, unique_key)
                    if website_json:
                        try:
                            website_data = json.loads(website_json)
                            return website_data
                        except json.JSONDecodeError as e:
                            logging.warning(f"JSON解析失败: {website_json} - {e}")
                            return None
                    return None
                except Exception as hget_error:
                    try:
                        website_jsons = self.redis_client.smembers(level3_key)
                        for website_json in website_jsons:
                            try:
                                website_data = json.loads(website_json)
                                if website_data.get("WebName") == webname:
                                    if not biz_type or website_data.get("BizType") == biz_type:
                                        return website_data
                            except json.JSONDecodeError as e:
                                logging.warning(f"JSON解析失败: {website_json} - {e}")
                                continue
                        return None
                    except Exception as smembers_error:
                        logging.error(f"获取数据失败: {smembers_error}")
                        return None

        except Exception as e:
            logging.error(f"获取网站数据失败: {province}/{city}/{webname} - {e}")
            return None

    # 获取某城市所有网站的数据
    def get_city_websites(self, province: str, city: str) -> List[Dict]:
        """
        获取某个城市的所有网站数据
        """
        try:
            level3_key = f"website_data_v3:{province}:{city}"

            # 检查键的类型
            try:
                key_type = self.redis_client.type(level3_key)

                if key_type == 'hash':
                    # 哈希类型，使用HGETALL
                    website_data_map = self.redis_client.hgetall(level3_key)

                    websites = []
                    for webname, website_json in website_data_map.items():
                        try:
                            website_data = json.loads(website_json)
                            websites.append(website_data)
                        except json.JSONDecodeError as e:
                            logging.warning(f"JSON解析失败: {website_json} - {e}")
                            continue

                    return websites
                elif key_type == 'set':
                    # 集合类型（旧数据），使用SMEMBERS并转换
                    website_jsons = self.redis_client.smembers(level3_key)

                    websites = []
                    for website_json in website_jsons:
                        try:
                            website_data = json.loads(website_json)
                            websites.append(website_data)
                        except json.JSONDecodeError as e:
                            logging.warning(f"JSON解析失败: {website_json} - {e}")
                            continue

                    return websites
                else:
                    # 其他类型，返回空列表
                    logging.warning(f"键类型不支持: {key_type} for {level3_key}")
                    return []
            except Exception as type_error:
                logging.warning(f"检查键类型失败: {type_error}")
                # 尝试直接使用HGETALL
                try:
                    website_data_map = self.redis_client.hgetall(level3_key)
                    websites = []
                    for webname, website_json in website_data_map.items():
                        try:
                            website_data = json.loads(website_json)
                            websites.append(website_data)
                        except json.JSONDecodeError as e:
                            logging.warning(f"JSON解析失败: {website_json} - {e}")
                            continue
                    return websites
                except Exception as hgetall_error:
                    # 尝试使用SMEMBERS
                    try:
                        website_jsons = self.redis_client.smembers(level3_key)
                        websites = []
                        for website_json in website_jsons:
                            try:
                                website_data = json.loads(website_json)
                                websites.append(website_data)
                            except json.JSONDecodeError as e:
                                logging.warning(f"JSON解析失败: {website_json} - {e}")
                                continue
                        return websites
                    except Exception as smembers_error:
                        logging.error(f"获取数据失败: {smembers_error}")
                        return []

        except Exception as e:
            logging.error(f"获取城市网站失败: {province}/{city} - {e}")
            return []

    # 获取所有省份
    def get_all_provinces(self) -> List[str]:
        """
        获取所有省份（通过扫描键名自动发现）
        """
        try:
            provinces = set()
            # 扫描所有以 website_data_v3: 开头的键
            cursor = 0
            pattern = "website_data_v3:*:*"

            while True:
                cursor, keys = self.redis_client.scan(cursor=cursor, match=pattern, count=100)
                for key in keys:
                    # 解析省份名称（第二个部分）
                    parts = key.split(':')
                    if len(parts) >= 3:
                        provinces.add(parts[1])
                if cursor == 0:
                    break

            return list(provinces)

        except Exception as e:
            logging.error(f"获取省份列表失败: {e}")
            return []

    # 获取某省份包含的所有城市
    def get_cities_in_province(self, province: str) -> List[str]:
        """
        获取某个省份下的所有城市（通过扫描键名自动发现）
        """
        try:
            cities = set()
            # 扫描特定省份的所有键
            cursor = 0
            pattern = f"website_data_v3:{province}:*"

            while True:
                cursor, keys = self.redis_client.scan(cursor=cursor, match=pattern, count=100)
                for key in keys:
                    # 解析城市名称（第三个部分）
                    parts = key.split(':')
                    if len(parts) >= 3:
                        cities.add(parts[2])
                if cursor == 0:
                    break

            return list(cities)

        except Exception as e:
            logging.error(f"获取城市列表失败: {province} - {e}")
            return []

    def delete_website(self, province: str, city: str, webname: str, biz_type: str = None) -> bool:
        """删除特定网站数据

        去重逻辑：使用 WebName + BizType 作为联合唯一键
        """
        try:
            level3_key = f"website_data_v3:{province}:{city}"
            unique_key = self._get_unique_key(webname, biz_type)

            try:
                key_type = self.redis_client.type(level3_key)

                if key_type == 'hash':
                    result = self.redis_client.hdel(level3_key, unique_key)

                    if result > 0:
                        logging.info(f"成功删除: website_data_v3/{province}/{city}/{unique_key}")
                        return True
                    else:
                        if biz_type:
                            for potential_key in self.redis_client.hkeys(level3_key):
                                if potential_key.startswith(f"{webname}:"):
                                    result = self.redis_client.hdel(level3_key, potential_key)
                                    if result > 0:
                                        logging.info(f"成功删除: website_data_v3/{province}/{city}/{potential_key}")
                                        return True
                        logging.warning(f"要删除的网站不存在: {province}/{city}/{unique_key}")
                        return False
                elif key_type == 'set':
                    website_jsons = self.redis_client.smembers(level3_key)

                    target_data_json = None
                    for website_json in website_jsons:
                        try:
                            website_data = json.loads(website_json)
                            if website_data.get("WebName") == webname:
                                if not biz_type or website_data.get("BizType") == biz_type:
                                    target_data_json = website_json
                                    break
                        except json.JSONDecodeError as e:
                            logging.warning(f"JSON解析失败: {website_json} - {e}")
                            continue

                    if not target_data_json:
                        logging.warning(f"要删除的网站不存在: {province}/{city}/{unique_key}")
                        return False

                    result = self.redis_client.srem(level3_key, target_data_json)

                    if result > 0:
                        logging.info(f"成功删除: website_data_v3/{province}/{city}/{unique_key}")
                        return True
                    else:
                        logging.warning(f"删除失败: website_data_v3/{province}/{city}/{unique_key}")
                        return False
                else:
                    logging.warning(f"键类型不支持: {key_type} for {level3_key}")
                    return False
            except Exception as type_error:
                logging.warning(f"检查键类型失败: {type_error}")
                try:
                    result = self.redis_client.hdel(level3_key, unique_key)
                    if result > 0:
                        logging.info(f"成功删除: website_data_v3/{province}/{city}/{unique_key}")
                        return True
                except Exception as hdel_error:
                    try:
                        website_jsons = self.redis_client.smembers(level3_key)
                        target_data_json = None
                        for website_json in website_jsons:
                            try:
                                website_data = json.loads(website_json)
                                if website_data.get("WebName") == webname:
                                    if not biz_type or website_data.get("BizType") == biz_type:
                                        target_data_json = website_json
                                        break
                            except json.JSONDecodeError:
                                continue
                        if target_data_json:
                            result = self.redis_client.srem(level3_key, target_data_json)
                            if result > 0:
                                logging.info(f"成功删除: website_data_v3/{province}/{city}/{unique_key}")
                                return True
                    except Exception as smembers_error:
                        logging.error(f"删除数据失败: {smembers_error}")
                logging.warning(f"要删除的网站不存在: {province}/{city}/{unique_key}")
                return False

        except Exception as e:
            logging.error(f"删除网站失败: {province}/{city}/{webname} - {e}")
            return False

    # 统计信息
    def get_website_stats(self, province: str = None, city: str = None) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            # 一次性获取所有数据，避免多次查询
            websites = self._get_websites_by_region(province, city)

            total = len(websites)
            if total == 0:
                return {'total_websites': 0, 'message': '没有找到相关网站'}

            # 使用列表推导式提高性能
            successful = sum(1 for w in websites if self._to_bool(w.get('WasSuccessful')))
            website_error = sum(1 for w in websites if self._to_bool(w.get('WebsiteError')))
            has_content = sum(1 for w in websites if self._to_bool(w.get('HasContent')))
            has_new_data = sum(1 for w in websites if self._to_bool(w.get('HasNewData')))
            is_valid_data = sum(1 for w in websites if self._to_bool(w.get('IsValidData')))

            return self._format_stats(total, successful, website_error,
                                      has_content, has_new_data, is_valid_data)

        except Exception as e:
            logging.error(f"获取统计信息失败: {e}")
            return {'error': str(e)}

    def _get_websites_by_region(self, province: str = None, city: str = None) -> List[Dict]:
        """根据区域获取网站列表"""
        if province and city:
            return self.get_city_websites(province, city)
        elif province:
            websites = []
            cities = self.get_cities_in_province(province)
            for city_name in cities:
                websites.extend(self.get_city_websites(province, city_name))
            return websites
        else:
            websites = []
            provinces = self.get_all_provinces()
            for prov in provinces:
                cities = self.get_cities_in_province(prov)
                for city_name in cities:
                    websites.extend(self.get_city_websites(prov, city_name))
            return websites

    def _to_bool(self, value) -> bool:
        """将多种格式转换为布尔值"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value == 1
        if isinstance(value, str):
            return value.lower() in ['1', 'true', 'yes', 'on']
        return False

    def _format_stats(self, total: int, successful: int, website_error: int,
                      has_content: int, has_new_data: int, is_valid_data: int) -> Dict:
        """格式化统计结果"""
        stats = {
            'total_websites': total,
            'successful_websites': successful,
            'website_error_websites': website_error,
            'websites_with_content': has_content,
            'websites_with_new_data': has_new_data,
            'websites_with_valid_data': is_valid_data,
        }

        # 添加百分比统计（避免除零错误）
        if total > 0:
            stats.update({
                'success_rate': round(successful / total * 100, 2),
                'error_rate': round(website_error / total * 100, 2),
                'content_rate': round(has_content / total * 100, 2),
                'new_data_rate': round(has_new_data / total * 100, 2),
                'valid_data_rate': round(is_valid_data / total * 100, 2)
            })
        else:
            stats.update({
                'success_rate': 0,
                'error_rate': 0,
                'content_rate': 0,
                'new_data_rate': 0,
                'valid_data_rate': 0
            })

        return stats

# if __name__ == '__main__':
    # # # 应用实例
    # storage = WebsiteRedisStorage()
    # # 更新数据
    # storage.update_website_data(
    #     province="福建省",
    #     city="漳州市",
    #     webname="漳州市公共资源交易中心",
    #     updates={'WasSuccessful': 1, 'WebsiteError': 1, 'HasContent': 1, 'HasNewData': 0, 'IsValidData': 1, 'WebName': '漳州市公共资源交易中心',"BizType":'政府采购'}
    # )
    # storage.update_website_data(
    #     province="福建省",
    #     city="漳州市",
    #     webname="漳州市公共资源交易中心",
    #     updates={'WasSuccessful': 1, 'WebsiteError': 1, 'HasContent': 1, 'HasNewData': 0, 'IsValidData': 1, 'WebName': '漳州市公共资源交易中心',"BizType":'建设工程'}
    # )
    # storage.update_website_data(
    #     province="福建省",
    #     city="福州市",
    #     webname="福州市公共资源交易中心",
    #     updates={'WasSuccessful': 1, 'WebsiteError': 1, 'HasContent': 1, 'HasNewData': 0, 'IsValidData': 1, 'WebName': '福州市公共资源交易中心',"BizType":'政府采购'}
    # )
    # storage.update_website_data(
    #     province="福建省",
    #     city="福州市",
    #     webname="福州市公共资源交易中心",
    #     updates={'WasSuccessful': 1, 'WebsiteError': 1, 'HasContent': 1, 'HasNewData': 0, 'IsValidData': 1, 'WebName': '福州市公共资源交易中心',"BizType":'建设工程'}
    # )
    # storage.update_website_data(
    #     province="福建省",
    #     city="福州市",
    #     webname="福州市公共资源交易中心",
    #     updates={'WasSuccessful': 1, 'WebsiteError': 1, 'HasContent': 1, 'HasNewData': 0, 'IsValidData': 1, 'WebName': '福州市公共资源交易中心',"BizType":'中介服务'}
    # )
