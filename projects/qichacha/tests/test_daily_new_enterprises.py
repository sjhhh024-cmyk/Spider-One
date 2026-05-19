from __future__ import annotations

import csv
import io
from datetime import date

import pytest

from daily_new_enterprises import (
    DatasetAsset,
    decode_csv_rows,
    extract_dataset_assets,
    filter_records_by_date,
    normalize_record,
)


DETAIL_HTML = """
<a href="javascript:;" class="downloadFileLink" id="rdf-token">
    <span style="color: #1B8EF8;" class="file-name">个人独资企业设立登记信息_0.rdf</span>
</a>
<a href="javascript:;" class="downloadFileLink" id="csv-token">
    <span style="color: #1B8EF8;" class="file-name">个人独资企业设立登记信息_0.csv</span>
</a>
<a href="javascript:;" class="downloadFileLink" id="xls-token">
    <span style="color: #1B8EF8;" class="file-name">个人独资企业设立登记信息_0.xls</span>
</a>
"""


def build_csv_bytes(rows: list[list[str]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerows(rows)
    return buffer.getvalue().encode("gb18030")


def test_extract_dataset_assets_returns_named_tokens() -> None:
    assets = extract_dataset_assets(DETAIL_HTML)

    assert assets["csv"] == DatasetAsset(format="csv", filename="个人独资企业设立登记信息_0.csv", token="csv-token")
    assert assets["rdf"] == DatasetAsset(format="rdf", filename="个人独资企业设立登记信息_0.rdf", token="rdf-token")
    assert assets["xls"] == DatasetAsset(format="xls", filename="个人独资企业设立登记信息_0.xls", token="xls-token")


def test_decode_csv_rows_supports_gb18030_and_maps_headers() -> None:
    csv_bytes = build_csv_bytes(
        [
            ["企业名称", "统一社会信用代码", "法定代表人、负责人、经营者", "住所", "注册资本（万）", "生产经营地、个体户经营场所", "成立日期", "核准日期", "业务类型"],
            ["泰州测试企业", "91320000TEST000001", "张三", "泰州市海陵区测试路 1 号", "100", "泰州市海陵区测试路 1 号", "2026-04-30", "2026-04-30", ""],
        ]
    )

    rows = decode_csv_rows(csv_bytes)

    assert rows == [
        {
            "企业名称": "泰州测试企业",
            "统一社会信用代码": "91320000TEST000001",
            "法定代表人、负责人、经营者": "张三",
            "住所": "泰州市海陵区测试路 1 号",
            "注册资本（万）": "100",
            "生产经营地、个体户经营场所": "泰州市海陵区测试路 1 号",
            "成立日期": "2026-04-30",
            "核准日期": "2026-04-30",
            "业务类型": "",
        }
    ]


def test_filter_records_by_date_dedupes_on_credit_code() -> None:
    raw_records = [
        {
            "企业名称": "泰州测试企业",
            "统一社会信用代码": "91320000TEST000001",
            "法定代表人、负责人、经营者": "张三",
            "住所": "地址 A",
            "注册资本（万）": "100",
            "生产经营地、个体户经营场所": "经营地 A",
            "成立日期": "2026-04-30",
            "核准日期": "2026-04-30",
            "业务类型": "",
            "_dataset_name": "市场主体登记信息",
            "_catalog_id": "20266",
        },
        {
            "企业名称": "泰州测试企业",
            "统一社会信用代码": "91320000TEST000001",
            "法定代表人、负责人、经营者": "张三",
            "住所": "地址 A",
            "注册资本（万）": "100",
            "生产经营地、个体户经营场所": "经营地 A",
            "成立日期": "2026-04-30",
            "核准日期": "2026-04-30",
            "业务类型": "",
            "_dataset_name": "合伙企业设立登记信息",
            "_catalog_id": "20277",
        },
        {
            "企业名称": "不应入表企业",
            "统一社会信用代码": "91320000TEST000002",
            "法定代表人、负责人、经营者": "李四",
            "住所": "地址 B",
            "注册资本（万）": "50",
            "生产经营地、个体户经营场所": "经营地 B",
            "成立日期": "2026-04-29",
            "核准日期": "2026-04-29",
            "业务类型": "",
            "_dataset_name": "个人独资企业设立登记信息",
            "_catalog_id": "20330",
        },
    ]

    rows = [normalize_record(record) for record in raw_records]
    filtered = filter_records_by_date(rows, target_date=date(2026, 4, 30))

    assert filtered == [
        {
            "company_name": "泰州测试企业",
            "credit_code": "91320000TEST000001",
            "legal_representative": "张三",
            "registered_address": "地址 A",
            "registered_capital_10k_cny": "100",
            "business_address": "经营地 A",
            "establish_date": "2026-04-30",
            "approval_date": "2026-04-30",
            "business_type": "",
            "source_dataset": "市场主体登记信息",
            "source_catalog_id": "20266",
        }
    ]


def test_normalize_record_requires_credit_code() -> None:
    with pytest.raises(ValueError):
        normalize_record(
            {
                "企业名称": "缺少信用代码企业",
                "统一社会信用代码": "",
                "法定代表人、负责人、经营者": "张三",
                "住所": "地址 A",
                "注册资本（万）": "100",
                "生产经营地、个体户经营场所": "经营地 A",
                "成立日期": "2026-04-30",
                "核准日期": "2026-04-30",
                "业务类型": "",
                "_dataset_name": "市场主体登记信息",
                "_catalog_id": "20266",
            }
        )
