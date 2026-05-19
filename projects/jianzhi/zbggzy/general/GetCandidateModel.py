import requests
from typing import Optional, Dict, Any
import logging
import asyncio


class CandidateModel:
    """
    大模型调用方法
    get_result：调用主方法
    """

    def __init__(self, base_url: str = "https://www.51qqx.com/extract/askHxr", timeout: int = 600):

        self.url = base_url
        self.timeout = timeout
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Test-Version': "v2",
            "Custom-Token": 'FACBED0693D0F2361DED36C4BDF35E19',
        }

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.content = None

    async def get_result_async(self, content: str, max_retries: int = 10) -> Optional[Dict[str, Any]]:
        self.content = content

        for attempt in range(max_retries):
            try:

                response_data = await self._normal_mode()

                if not response_data:
                    self.logger.warning(f"第{attempt + 1}次尝试：获取响应数据为空")
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 30)
                        self.logger.info(f"等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)
                    continue

                result = self._clear_data(response_data)
                if not result:
                    self.logger.warning(f"第{attempt + 1}次尝试：清理数据返回空结果")
                    if attempt < max_retries - 1:
                        wait_time = min(2 ** attempt, 30)
                        self.logger.info(f"等待 {wait_time} 秒后重试...")
                        await asyncio.sleep(wait_time)
                    continue

                result_dict = self.deal_result(result)
                return result_dict

            except requests.exceptions.Timeout as e:
                self.logger.warning(f"请求超时 (尝试 {attempt + 1}/{max_retries}): {e}")
            except requests.exceptions.ConnectionError as e:
                self.logger.warning(f"连接错误 (尝试 {attempt + 1}/{max_retries}): {e}")
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            except Exception as e:
                self.logger.error(f"处理响应时发生未预期的错误: {e}", exc_info=True)

            if attempt < max_retries - 1:
                wait_time = min(2 ** attempt, 30)  # 指数退避，最大30秒
                self.logger.info(f"等待 {wait_time} 秒后重试...")
                await asyncio.sleep(wait_time)

        self.logger.error(f"所有 {max_retries} 次尝试都失败了")
        return {}

    async def _normal_mode(self) -> Dict:
        data = {
            'text': self.content,
            "model": "qwen-doc-turbo"
        }
        response = requests.post(
            self.url,
            json=data,
            headers=self.headers,
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()


    # 调整格式，转换字段
    def deal_result(self, item):
        extra = {}
        extra['tenderNumber'] = item.get('项目编号', '')

        output_data = {
            'tenderTitle': item.get('项目名称', ''),
            'procurementUnit': item.get('采购单位', ''),
            'result': [],
            'extra': extra,
        }

        for itm in item.get('候选人结果', []):
            candidateSort = item.get('候选人结果', [])
            transformed_item = {
                'relationCompanyName': itm.get('候选人名称', ''),
                'candidateSort': candidateSort,
            }
            output_data['result'].append(transformed_item)

        return output_data

    # 提取字段
    def _clear_data(self, response_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            if not isinstance(response_data, dict):
                self.logger.error(f"响应不是字典类型: {type(response_data)}")
                return {}

            print(f'模型响应的数据：{response_data}')
            extract_paths = [
                'final_result',
                ('result', 0, 'extract_result'),  # result[0]['extract_result']
                ('result', 'extract_result'),  # result['extract_result']
                'result'
            ]

            for path in extract_paths:
                if isinstance(path, tuple):
                    content = response_data
                    extracted = True
                    for key in path:
                        if isinstance(content, list) and isinstance(key, int):
                            if len(content) > key:
                                content = content[key]
                            else:
                                extracted = False
                                break
                        elif isinstance(content, dict):
                            content = content.get(key)
                            if content is None:
                                extracted = False
                                break
                        else:
                            extracted = False
                            break

                    if extracted and content is not None:
                        # self.logger.info(f"从路径 {path} 提取到内容")
                        return content if isinstance(content, dict) else {}

                elif path in response_data:
                    content = response_data[path]
                    if content:
                        self.logger.info(f"从键 {path} 提取到内容")
                        return content if isinstance(content, dict) else {}

            self.logger.warning(f"无法从响应中提取内容，响应键: {list(response_data.keys())}")
            return {}

        except Exception as e:
            self.logger.error(f"清理数据时发生未知错误: {e}", exc_info=True)
            return {}


    def get_result(self, content: str, max_retries: int = 10) -> Optional[Dict[str, Any]]:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.get_result_async(content, max_retries))
                    return future.result()
            else:
                return asyncio.run(self.get_result_async(content, max_retries))
        except RuntimeError:
            return asyncio.run(self.get_result_async(content, max_retries))
