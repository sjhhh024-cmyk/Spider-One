import time
from GDGGZY.Core.imports import *  # 导入项目核心模块的所有组件


class JYGGSpider:
    """漳州市公共资源交易网 - 建设工程招标公告爬虫"""

    def __init__(self):
        """初始化爬虫组件和配置"""

        # 日志记录器：用于记录程序运行过程中的信息和错误
        self.log = SpiderSchedulerLogger().get_logger(__name__)

        # 大模型方法：用于从HTML文本中提取结构化数据（项目编号、名称、预算等）
        self.model = BiddingModel()

        # 去重检查器：避免重复采集同一条公告
        self.checker = URLDuplicateChecker()

        # HTML处理器：清理和规范化HTML内容
        self.html = HtmlContentCleaner()

        # HTML解码器：对HTML内容进行base64转码处理（处理加密内容）
        self.decryp_html = DecryptData()

        # 数据来源网站标识
        self.webSource = '漳州市公共资源交易网'

        # 业务类型：建设工程类别的招标公告
        self.BizType = "建设工程-招标公告"

        # 时间范围获取器：获取需要采集的时间区间（通常从配置读取）
        self.timer = TimeRange().get_range()

        # 随机User-Agent：模拟不同浏览器访问，降低反爬风险
        self.ua = UserAgent().random

        # 带重试机制的请求器：网络请求失败时自动重试
        self.requests = RequestWithRetry()

        # 监控状态信息：用于记录本次采集的各类状态，便于监控系统追踪
        self.logo_info = {
            'WasSuccessful': 1,  # 脚本运行情况：1-成功，0-失败
            'WebsiteError': 1,  # 网站情况：1-正常，0-异常
            'HasContent': 0,  # 有无数据：1-有数据，0-无数据
            'HasNewData': 0,  # 去重后有无新增数据：1-有新增，0-无新增
            'IsValidData': 1,  # 数据是否正常：1-正常，0-异常
            'WebName': self.webSource,  # 网站名称
            'BizType': self.BizType,  # 交易类型+公告类型
        }

        # 状态存储器：将监控状态保存到Redis，供监控系统查询
        self.storage = WebsiteRedisStorage()

        self.num = None  # 总页数，在crawl方法中计算

        # 请求头：模拟浏览器访问
        self.headers = {
            "User-Agent": UserAgent().random
        }

        # API接口地址（该网站使用POST接口返回JSON数据）
        self.url = "http://ggzyjy.xzfwzx.zhangzhou.gov.cn/proxy_api/publicResource/front/viewProjects"

        # POST请求参数：页码、每页数量、项目类型、时间范围等
        self.data = {
            "pageNum": 1,  # 当前页码，后续会动态修改
            "pageSize": 15,  # 每页15条数据
            "projectType": None,
            "cateNum": "001001001",  # 分类编号：建设工程招标公告
            "jurisdictionCode": None,
            # 开始时间：当天00:00:00
            "startDate": datetime.strptime(self.timer['start_time'], '%Y-%m-%d').replace(
                hour=00, minute=00, second=00).strftime('%Y-%m-%d %H:%M:%S'),
            # 结束时间：当天23:59:59
            "endDate": datetime.strptime(self.timer['end_time'], '%Y-%m-%d').replace(
                hour=23, minute=59, second=59).strftime('%Y-%m-%d %H:%M:%S')
        }

    def spider(self, page):
        """
        采集指定页面的公告列表，并处理每条公告的详情
        :param page: 要采集的页码
        """
        print(f'正在采集第{page}页')

        # 设置当前页码
        self.data['pageNum'] = page

        # 将请求参数转换为JSON字符串（紧凑格式，去除空格）
        data = json.dumps(self.data, separators=(',', ':'))

        # 发送POST请求获取公告列表
        response = self.requests.request(self.url, method='post', headers=self.headers, data=data, verify=False)

        if response.status_code == 200:  # 请求成功
            # 遍历当前页的所有公告
            for item in response.json()['data']['resultList']:
                # 获取并清理公告标题（去除HTML标签）
                announcementTitle = item['title']
                announcementTitle = re.sub("<.*?>", '', announcementTitle)

                # 获取项目所在地编码和名称
                regionCode = item['projectaddress']
                regionName = item['projectaddressname']

                # 市本级统一修改为漳州市
                if regionName == '市本级':
                    regionName = '漳州市'

                # 发布时间
                releaseTime = item['infoDate']

                # 招标类型（默认空，后续可能需要扩展）
                bidType = ''

                # 从发布时间中提取年份（用于过滤2025年以前的数据）
                year = releaseTime.split('-')[0]

                # 文件URL（某些场景需要，当前为空）
                file_url = ''

                # 原始网站地址：公告在原网站的详情页链接
                originalWebsiteAddress = f'http://ggzyjy.xzfwzx.zhangzhou.gov.cn/cms/sitemanage/index.shtml?siteId=40669965560550000&templateId=10671870564930000&infoId={item["infoID"]}'

                # 去重检查：如果该URL已经采集过（'fj'表示福建省），则跳过
                if not self.checker.is_duplicate(originalWebsiteAddress, 'fj'):
                    # 过滤条件：标题不包含'变更'/'终止'，且年份>=2025
                    if '变更' not in announcementTitle and '终止' not in announcementTitle and year >= '2025':
                        # 标记有新增数据
                        self.logo_info['HasNewData'] = 1

                        # 构建详情页API接口URL
                        url = f"http://ggzyjy.xzfwzx.zhangzhou.gov.cn/proxy_api/publicResource/front/projectDetail/{item['infoID']}"

                        # 请求详情数据
                        res = self.requests.request(url, method='get', headers=self.headers, verify=False)

                        if res.status_code == 200:
                            try:
                                # 解析详情数据，提取结构化信息
                                data = self.parse(res.json(), announcementTitle, releaseTime,
                                                  originalWebsiteAddress, file_url, bidType, regionCode, regionName)
                                if data is not None:
                                    # 移除不需要的字段
                                    data.pop('_id', None)
                                    data.pop('purchaserAddress', None)

                                    # 发送到MQ消息队列（供其他系统消费）
                                    MqData().get_data(data)

                                    # 存入MongoDB数据库（招标类型集合）
                                    MonData("招标").insert_one(data)

                                    # 将该URL加入去重集合，避免下次重复采集
                                    self.checker.add_url(originalWebsiteAddress, 'fj')
                            except Exception as e:
                                # 记录错误日志
                                self.log.error(f'错误链接：{originalWebsiteAddress}')
                                self.log.error(f'错误信息：{e}')
                                self.logo_info['IsValidData'] = 0  # 标记数据异常
                        else:
                            # 详情接口请求失败，标记网站异常
                            self.logo_info['WebsiteError'] = 0
        else:
            # 列表页请求失败，标记网站异常
            self.logo_info['WebsiteError'] = 0

    def parse(self, item, announcementTitle, releaseTime, originalWebsiteAddress, file_url, bidType, regionCode,
              regionName):
        """
        解析公告详情，提取结构化数据
        :param item: 详情API返回的JSON数据
        :param announcementTitle: 公告标题
        :param releaseTime: 发布时间
        :param originalWebsiteAddress: 原始网站地址
        :param file_url: 文件URL（预留）
        :param bidType: 招标类型（预留）
        :param regionCode: 地区编码
        :param regionName: 地区名称
        :return: 结构化的公告数据字典
        """
        print(originalWebsiteAddress)

        # 确保地区名称有值（默认漳州市）
        if regionName is None:
            regionName = '漳州市'

        # 获取公告正文HTML内容
        content = item['infoContent']

        # 清理HTML，提取纯文本（用于大模型分析）
        html_text = ClearHtml().clean_html(content)

        # 获取附件列表（文件名称和下载地址）
        fileInfo = self.get_file(item)

        # 对HTML内容进行编码转换（处理特殊编码）
        htmlContent = self.decryp_html.deal_html(content)

        # 调用大模型从纯文本中提取关键信息
        # 包括：项目编号(projectNum)、项目名称(projectName)、预算金额(budgetAmount)、
        #       采购方式(procurementMethod)、信息来源(releaseSource)、咨询信息(consultationInfo)
        infomodel = BiddingModel().get_result(html_text)

        # 加载地区编码配置（从fujian.yaml读取）
        codedata = GetCode('fujian.yaml', regionName).load_config()

        # 组装最终的数据结构
        infodata = {
            'projectNum': infomodel['projectNum'],  # 项目编号
            'projectName': infomodel['projectName'],  # 项目名称
            'announcementTitle': announcementTitle,  # 公告标题
            'releaseTime': releaseTime,  # 发布时间
            'budgetAmount': infomodel['budgetAmount'],  # 预算金额
            'procurementMethod': infomodel['procurementMethod'],  # 采购方式
            'releaseSource': infomodel['releaseSource'],  # 信息来源
            'provinceCode': 350000,  # 福建省代码
            'regionCode': codedata['code'],  # 地区代码
            'regionName': codedata['city_name'],  # 地区名称
            'consultationInfo': infomodel['consultationInfo'],  # 咨询信息
            'parentType': '建设工程',  # 父级类型
            'bidType': '',  # 招标类型（预留）
            'announcementType': '招标公告',  # 公告类型
            "contentType": 1,  # 内容类型（1-正文）
            'webSource': self.webSource,  # 来源网站
            'originalWebsiteAddress': originalWebsiteAddress,  # 原始链接
            'fileInfo': fileInfo,  # 附件信息
            'htmlContent': htmlContent,  # HTML内容（编码后）
        }

        print(infodata)  # 打印调试信息
        return infodata

    def get_file(self, item):
        """
        从详情数据中提取附件信息
        :param item: 详情API返回的JSON数据
        :return: 附件列表，每个附件包含文件名和下载地址
        """
        fileInfo = []
        li_list = item['attachFiles']  # 获取附件列表

        for li in li_list:
            if 'attFileName' in li:  # 确保有文件名
                fileInfo.append({
                    'fileType': '',  # 文件类型（预留）
                    'fileName': li['attFileName'],  # 附件名称
                    'fileUrl': li['attUrl']  # 附件下载地址
                })
        return fileInfo

    def crawl(self):
        """
        爬虫主入口方法：获取总页数，并发采集所有页面
        """
        try:
            # 首次请求，获取总记录数以计算总页数
            data = json.dumps(self.data, separators=(',', ':'))
            response = self.requests.request(self.url, method='post', headers=self.headers, data=data, verify=False)

            if response.status_code == 200:
                try:
                    # 获取总记录数，计算总页数（向上取整）
                    num = response.json()['data']['totalSize']
                    self.num = (int(num) + 14) // 15  # 每页15条，计算总页数
                except Exception as e:
                    # 解析总记录数失败，标记网站异常
                    self.logo_info['WebsiteError'] = 0
                    self.log.error(f'获取总页数出错，已保存采集状态！！！')

                # 如果至少有1页数据
                if self.num >= 1:
                    self.logo_info['HasContent'] = 1  # 标记有数据内容

                    # 使用线程池并发采集，最大5个并发线程
                    with ThreadPoolExecutor(max_workers=5) as executor:
                        futures = []
                        # 提交所有页面的采集任务
                        for page in tqdm(range(1, self.num + 1)):  # tqdm显示进度条
                            future = executor.submit(self.spider, page)
                            futures.append(future)

                        # 等待所有任务完成，捕获异常
                        for future in as_completed(futures):
                            try:
                                future.result()
                            except Exception as e:
                                self.log.error(f"线程任务执行失败: {e}")
                else:
                    # 当前时间周期内没有新数据
                    self.log.info(f'{self.timer["start_time"]}--{self.timer["end_time"]}-当前该周期没有新数据！！！')
            else:
                # 首次请求失败，标记网站异常
                self.logo_info['WebsiteError'] = 0

        except Exception as e:
            # 爬虫启动失败（网络、配置等严重错误）
            self.log.error(f"爬虫启动失败: {e}")
            self.logo_info['WasSuccessful'] = 0  # 标记运行失败

        # 打印本次采集的状态统计
        print(f'网站标识统计：{self.logo_info}')

        # 将监控状态保存到Redis（供监控系统展示）
        self.storage.update_website_data(
            province="福建省",
            city="漳州市",
            webname=self.webSource,
            updates=self.logo_info
        )

# 程序入口：仅在直接运行此脚本时执行
if __name__ == '__main__':
    JYGGSpider().crawl()  # 启动爬虫