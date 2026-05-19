import re
import cn2an


class MoneyParser:
    def convert_amount(self,text: str) -> str:
        """
        将各种格式的金额字符串转换为 "阿拉伯数字+元" 的格式
        如果包含特定非金额关键词或斜杠 /，则原样返回
        """
        original_text = text
        text = text.strip()

        # 0. 如果包含斜杠 /，直接原样返回
        if '/' in text:
            return original_text

        # 0.1 如果包含非金额关键词，直接原样返回
        non_amount_keywords = ['下浮率', '上浮率', '费率', '利率', '比例', '折扣', '税率']
        for keyword in non_amount_keywords:
            if keyword in text:
                return original_text

        # 1. 去掉括号及其中的内容（如 (200,000元)）
        text = re.sub(r'[（(][^）)]*[）)]', '', text)

        # 2. 去掉 CNY、RMB 前缀（不区分大小写）
        text = re.sub(r'^(CNY|RMB)\s*', '', text, flags=re.IGNORECASE)

        # 3. 如果已经是纯数字 + 元 格式，直接返回
        if re.match(r'^[\d,]+(\.\d+)?元?$', text):
            clean_num = text.replace(',', '').replace('元', '')
            return f"{clean_num}元"

        # 4. 处理财务大写体（如：人民币贰拾万元整）
        if re.search(r'[壹贰叁肆伍陆柒捌玖拾佰仟万亿元整角分]', text) or '人民币' in text:
            try:
                if text.startswith('人民币'):
                    text = text[3:]
                text = text.replace('整', '')
                num = cn2an.cn2an(text, mode='rmb')
                return f"{int(num)}元" if num.is_integer() else f"{num}元"
            except:
                try:
                    num = cn2an.cn2an(text, mode='up')
                    return f"{int(num)}元" if num.is_integer() else f"{num}元"
                except:
                    pass

        # 5. 处理货币符号式（如：￥210000）
        money_symbol_match = re.match(r'^[¥￥](\d+(?:\.\d+)?)$', text)
        if money_symbol_match:
            return f"{money_symbol_match.group(1)}元"

        # 6. 处理西文千分位式（如：210,000元）
        comma_match = re.match(r'^(\d{1,3}(?:,\d{3})*)(?:\.(\d+))?元?$', text)
        if comma_match:
            integer_part = comma_match.group(1).replace(',', '')
            decimal_part = comma_match.group(2) or ''
            if decimal_part:
                return f"{integer_part}.{decimal_part}元"
            else:
                return f"{integer_part}元"

        # 7. 处理中文口语化（如：21万元）
        chinese_unit_match = re.match(r'^(\d+(?:\.\d+)?)([万千百十])元?$', text)
        if chinese_unit_match:
            num_part = float(chinese_unit_match.group(1))
            unit = chinese_unit_match.group(2)
            multiplier = {'万': 10000, '千': 1000, '百': 100, '十': 10}.get(unit, 1)
            result = num_part * multiplier
            return f"{int(result)}元" if result.is_integer() else f"{result}元"

        # 8. 最后尝试通用解析
        try:
            num = cn2an.cn2an(text, mode='smart')
            return f"{int(num)}元" if isinstance(num, float) and num.is_integer() else f"{num}元"
        except:
            return original_text

if __name__ == '__main__':
    result = MoneyParser().convert_amount("7240.00，大写(人民币)：柒仟贰佰肆拾元整）")
    print(result)


