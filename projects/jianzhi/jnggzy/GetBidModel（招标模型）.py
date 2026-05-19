import json
import re
import time
import requests
from typing import Optional, Dict, Any
import logging

from .AmountConverter import MoneyParser


class BiddingModel:
    """
    大模型调用方法
    get_result：调用主方法
    """
    # 正式服务器
    def __init__(self, base_url: str = 'https://www.51qqx.com/extract/ask', timeout: int = 30):

        self.url = base_url
        self.timeout = timeout
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Test-Version': "v2",
            # 正式服务器
            "Custom-Token":'FACBED0693D0F2361DED36C4BDF35E19',
        }

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_result(self, content: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:

        # data = {'question': content}
        data = {'text': content,
                "model": "qwen-doc-turbo"
                }

        for attempt in range(max_retries):
            try:

                response = requests.post(
                    self.url,
                    json=data,
                    headers=self.headers,
                    timeout=self.timeout
                )

                response.raise_for_status()  # 检查HTTP错误

                result = self._clear_data(response.json())
                result_dict = self.deal_result(result)
                return result_dict

            except requests.exceptions.RequestException as e:
                self.logger.warning(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 指数退避
                    self.logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    self.logger.error(f"所有 {max_retries} 次尝试都失败了")
                    return ""
            except Exception as e:
                self.logger.error(f"处理响应时发生错误: {e}")
                return ""

        return ""

    # 调整格式，转换字段
    def deal_result(self,item):
        print(f'原数据：{item}')
        purchasingInfor = []
        projectInfor = []
        if item['采购人名称'] != '' and item['采购人名称'] != None:
            purchasingInfor.append('名称：' + item['采购人名称'])
        if item['项目联系人'] != '' and item['项目联系人'] != None:
            projectInfor.append('项目联系人：' + item['项目联系人'].replace('、',','))
        if item['项目联系方式'] != '' and item['项目联系方式'] != None:
            projectInfor.append('电话：' + item['项目联系方式'].replace('、',','))
        consultationInfo = {
            "purchasingInfor": purchasingInfor,
            'projectInfor': projectInfor,
        }
        money = str(item['预算金额']).replace('（人民币）','').replace(",",'').replace('¥','')
        if money == 'None':
            money = ''
        money = MoneyParser().convert_amount(money)
        projectNum = item['项目编号']
        if projectNum == None:
            projectNum = ''
        projectName = item['项目名称']
        if projectName == None:
            projectName = ''
        procurementMethod = item['采购方式']
        key_list = ['单一来源', '邀请招标', '竞争性谈判', '询价', '竞争性磋商', '公开招标']
        if procurementMethod not in key_list:
            procurementMethod = '其他方式'
        releaseSource = item['采购人名称']
        if releaseSource == None:
            releaseSource = ''
        purchaserAddress = item['采购人地址']
        if purchaserAddress == None:
            purchaserAddress = ''
        data_dict = {
            'projectNum': projectNum,
            'projectName': projectName,
            'budgetAmount': money,
            'procurementMethod': procurementMethod,
            # 发布来源
            'releaseSource': releaseSource,
            # 采购人地址
            'purchaserAddress': purchaserAddress,
            # 联系人信息
            'consultationInfo': consultationInfo
        }
        return data_dict

    # 提取字段
    def _clear_data(self, response_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:

        try:
            print(f'模型响应的数据：{response_data}')
            if 'final_result' in response_data:
                content = response_data.get('final_result', '')
            else:
                content = response_data['result'][0]

            return content

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析错误: {e}")
            self.logger.debug(f"原始内容: {content}")
            return ""
        except KeyError as e:
            self.logger.error(f"响应数据中缺少必要的键: {e}")
            return ""
        except Exception as e:
            self.logger.error(f"清理数据时发生未知错误: {e}")
            return ""
#
if __name__ == '__main__':
    data = """
<div class="detail_text"><h6>项目概况</h6><p>中山市人力资源和社会保障局“广货行天下·中山百货进广州”活动服务项目采购项目的潜在供应商应在广东省政府采购网https://gdgpo.czt.gd.gov.cn/获取采购文件，并于&nbsp;2026年04月21日 09时30分&nbsp;（北京时间）前提交响应文件。</p><h4>一、项目基本情况</h4><p>项目编号：442000-2026-00917</p><p>项目名称：中山市人力资源和社会保障局“广货行天下·中山百货进广州”活动服务项目</p><p>采购方式：竞争性磋商</p><p>预算金额：2,550,000.00元</p><p>采购需求：</p><p>采购包1(“广货行天下·中山百货进广州”活动服务项目):</p><p>采购包预算金额：2,550,000.00元</p><table width="1603" cellspacing="0" style="width: 798px;"><thead style="box-sizing: border-box; margin: 0px; padding: 0px;"></thead><tbody style="box-sizing: border-box; margin: 0px; padding: 0px;"><tr class="firstRow"><td style="box-sizing: border-box; margin: 0px; padding-right: 8px; padding-left: 8px; border-color: rgb(51, 51, 51); text-align: center; word-break: break-all; width: 80px;">品目号</td><td style="box-sizing: border-box; margin: 0px; padding-right: 8px; padding-left: 8px; border-color: rgb(51, 51, 51); text-align: center; word-break: break-all; width: 300px;">品目名称</td><td style="box-sizing: border-box; margin: 0px; padding-right: 8px; padding-left: 8px; border-color: rgb(51, 51, 51); text-align: center; word-break: break-all; width: 300px;">采购标的</td><td style="box-sizing: border-box; margin: 0px; padding-right: 8px; padding-left: 8px; border-color: rgb(51, 51, 51); text-align: center; word-break: break-all; width: 100px;">数量（单位）</td><td style="box-sizing: border-box; margin: 0px; padding-right: 8px; padding-left: 8px; border-color: rgb(51, 51, 51); text-align: center; word-break: break-all; width: 200px;">技术规格、参数及要求</td><td style="box-sizing: border-box; margin: 0px; padding-right: 8px; padding-left: 8px; border-color: rgb(51, 51, 51); text-align: center; word-break: break-all; width: 120px;">品目预算(元)</td><td style="box-sizing: border-box; margin: 0px; padding-right: 8px; padding-left: 8px; border-color: rgb(51, 51, 51); text-align: center; word-break: break-all; width: 120px;">最高限价(元)</td></tr><tr style="box-sizing: border-box; margin: 0px; padding: 0px; height: 32px; word-break: break-all;"><td style="box-sizing: border-box; margin: 0px; padding-right: 8px; padding-left: 8px; border-collapse: collapse; border-color: rgb(51, 51, 51); text-align: center; word-break: break-all;">1-1</td><td style="box-sizing: border-box; margin: 0px; padding-right: 8px; padding-left: 8px; border-collapse: collapse; border-color: rgb(51, 51, 51); text-align: center; word-break: break-all;">其他商务服务</td><td style="box-sizing: border-box; margin: 0px; padding-right: 8px; padding-left: 8px; border-collapse: collapse; border-color: rgb(51, 51, 51); text-align: center; word-break: break-all;">广货行天下·中山百货进广州”活动服务项目</td><td style="box-sizing: border-box; margin: 0px; padding-right: 8px; padding-left: 8px; border-collapse: collapse; border-color: rgb(51, 51, 51); text-align: center; word-break: break-all;">1(项)</td><td style="box-sizing: border-box; margin: 0px; padding-right: 8px; padding-left: 8px; border-collapse: collapse; border-color: rgb(51, 51, 51); text-align: center; word-break: break-all;">详见采购文件</td><td class="alignright" style="box-sizing: border-box; margin: 0px; padding-right: 8px; padding-left: 8px; border-collapse: collapse; border-color: rgb(51, 51, 51); text-align: right; word-break: normal;">2,550,000.00</td><td class="alignright" style="box-sizing: border-box; margin: 0px; padding-right: 8px; padding-left: 8px; border-collapse: collapse; border-color: rgb(51, 51, 51); text-align: right; word-break: normal;">-</td></tr></tbody></table><p>本采购包不接受联合体投标</p><p>合同履行期限：2026年6月30日前完成所有服务内容。</p><h4>二、申请人的资格要求：</h4><p>1.投标供应商应具备《中华人民共和国政府采购法》第二十二条规定的条件，提供下列材料：</p><p>1）具有独立承担民事责任的能力：在中华人民共和国境内注册的法人或其他组织或自然人，响应时提交有效的营业执照（或事业法人登记证或身份证等相关证明）复印件或扫描件。分支机构响应的，须提供总公司和分公司营业执照副本复印件，总公司出具给分支机构的授权书。</p><p>2）有依法缴纳税收和社会保障资金的良好记录：提供《政府采购供应商资格信用承诺函》（承诺函格式见公告附件）或磋商截止时间前12个月内任意1个月依法缴纳税收和社会保障资金的相关材料。如依法免税或不需要缴纳社会保障资金的，提供相应证明材料。若供应商同时提供承诺函和证明材料的，资格审查时以证明材料为准。</p><p>3）具有良好的商业信誉和健全的财务会计制度：提供《政府采购供应商资格信用承诺函》(格式详见公告附件)或提供2024年度财务报告（或磋商截止时间前12个月内任意一个月的财务报表）关键页或由基本开户银行出具的资信证明。若供应商同时提供承诺函和证明材料的，资格审查时以证明材料为准。</p><p>4）履行合同所必需的设备和专业技术能力：提供“具有履行合同所必需的设备和专业技术能力”的声明或承诺，或提供“具有设备和专业技术能力（人员）”的相关证明资料，或提供《设备和专业技术能力（人员）情况表》（格式自拟）。</p><p>5）参加采购活动前3年内，在经营活动中没有重大违法记录：提供《政府采购供应商资格信用承诺函》(格式详见公告附件)或参照响应承诺函相关承诺格式内容。重大违法记录，是指供应商因违法经营受到刑事处罚或者责令停产停业、吊销许可证或者执照、较大数额罚款等行政处罚。（根据财库〔2022〕3号文，“较大数额罚款”认定为200万元以上的罚款，法律、行政法规以及国务院有关部门明确规定相关领域“较大数额罚款”标准高于200万元的，从其规定）。</p><p><br></p><p>2.落实政府采购政策需满足的资格要求：</p><p>采购包1(“广货行天下·中山百货进广州”活动服务项目)落实政府采购政策需满足的资格要求如下:</p><p>本采购包整体专门面向中小企业，供应商须是符合本项目所属行业（租赁和商务服务业）政策划分标准的中型、小型、微型企业，监狱企业、残疾人福利单位视同小型、微型企业。注：中小企业以供应商填写的《中小企业声明函（工程、服务）》（格式见采购文件第六章）为判定标准，残疾人福利性单位以供应商填写的《残疾人福利性单位声明函》（格式见采购文件第六章）为判定标准，监狱企业须供应商提供由省级以上监狱管理局、戒毒管理局（含新疆生产建设兵团）出具的属于监狱企业的证明文件，否则不予认定。</p><p><br></p><p>3.本项目的特定资格要求：</p><p>采购包1(“广货行天下·中山百货进广州”活动服务项目)特定资格要求如下:</p><p>(1)供应商未被列入“信用中国”网站(www.creditchina.gov.cn)“失信被执行人或重大税收违法失信主体或政府采购严重违法失信行为记录名单”；不处于中国政府采购网(www.ccgp.gov.cn)“政府采购严重违法失信行为信息记录”中的禁止参加政府采购活动期间。（以采购代理机构于投标（响应）截止时间当天在“信用中国”网站（www.creditchina.gov.cn）及中国政府采购网（http://www.ccgp.gov.cn/） 查询结果为准，如相关失信记录已失效，供应商需提供相关证明资料）。</p><p>(2)单位负责人为同一人或者存在直接控股、 管理关系的不同供应商，不得同时参加本采购项目（或采购包） 投标（响应）。 为本项目提供整体设计、 规范编制或者项目管理、 监理、 检测等服务的供应商， 不得再参与本项目投标（响应）。 响应承诺函相关承诺要求内容。</p><p><br></p><h4>三、获取采购文件</h4><p>时间：&nbsp;2026年04月11日&nbsp;至&nbsp;2026年04月17日&nbsp;，每天上午&nbsp;00:00:00&nbsp;至&nbsp;12:00:00&nbsp;，下午&nbsp;12:00:00&nbsp;至&nbsp;23:59:59&nbsp;（北京时间,法定节假日除外）</p><p>地点：广东省政府采购网https://gdgpo.czt.gd.gov.cn/</p><p>方式：在线获取</p><p>售价：&nbsp;免费获取</p><h4>四、响应文件提交</h4><p>截止时间：&nbsp;2026年04月21日 09时30分00秒&nbsp;（北京时间）</p><p>地点：线上开标，请登录广东省政府采购网https://gdgpo.czt.gd.gov.cn/</p><h4>五、开启</h4><p>时间：&nbsp;2026年04月21日 09时30分00秒&nbsp;（北京时间）</p><p>地点：线上开标，请登录广东省政府采购网https://gdgpo.czt.gd.gov.cn/</p><h4>六、公告期限</h4><p>自本公告发布之日起3个工作日。</p><h4>七、其他补充事宜</h4><p>1.本项目采用电子系统进行招投标，请在投标前详细阅读供应商操作手册，手册获取网址：https://gdgpo.czt.gd.gov.cn/help/transaction/download.html。投标供应商在使用过程中遇到涉及系统使用的问题，可通过020-88696588进行咨询或通过广东政府采购智慧云平台运维服务说明中提供的其他服务方式获取帮助。</p><p>2.供应商参加本项目投标，需要提前办理CA和电子签章，办理方式和注意事项详见供应商操作手册与CA办理指南，指南获取地址：https://gdgpo.czt.gd.gov.cn/help/problem/。</p><p>3.如需缴纳保证金，供应商可通过"广东政府采购智慧云平台金融服务中心"(https://gdgpo.czt.gd.gov.cn/zcdservice/zcd/guangdong/)，申请办理投标（响应）担保函、保险（保证）保函。</p><p><br></p><p>4.本项目支持电子保函，可通过登录项目采购电子交易系统跳转至电子保函系统进行在线办理。电子保函办理办法详见供应商操作手册。</p><p>5.需要落实的政府采购政策：《政府采购促进中小企业发展管理办法》（财库〔2020〕46号）、《关于政府采购支持监狱企业发展有关问题的通知》(财库〔2014〕68号)、《关于促进残疾人就业政府采购政策的通知》（财库〔2017〕141号)、《关于环境标志产品政府采购实施的意见》（财库〔2006〕90号）、《节能产品政府采购实施意见》的通知（财库〔2004〕185号）、《关于调整优化节能产品、环境标志产品政府采购执行机制的通知》（财库〔2020〕9号）等。</p><p>6.发布公告的媒介：中国政府采购网(www.ccgp.gov.cn)，广东省政府采购网(https://gdgpo.czt.gd.gov.cn/)。</p><p><br></p><h4>八、凡对本次采购提出询问，请按以下方式联系。</h4><h6>1.采购人信息</h6><p>名&nbsp;&nbsp;称：中山市人力资源和社会保障局</p><p>地&nbsp;&nbsp;址：中山市中山三路26号</p><p>联系方式：0760-88318992</p><h6>2.采购代理机构信息</h6><p>名&nbsp;&nbsp;称：广东省电信规划设计院有限公司第三分公司</p><p>地&nbsp;&nbsp;址：中山市石岐区南江路3号2栋</p><p>联系方式：13424546924、13211126509</p><h6>3.项目联系方式</h6><p>项目联系人：周冠中、谭耀聪、李娇、黄赐悠</p><p>电&nbsp;&nbsp;话：13424546924、13211126509</p><p style="text-align: right;">广东省电信规划设计院有限公司第三分公司</p><p style="text-align: right;">2026年4月10日</p></div>

    """
    from QGZJGG.Utils.HTMLCleaner import ClearHtml
    data = ClearHtml().clean_html(data)
    print(data)
    print(BiddingModel().get_result(data))
#
