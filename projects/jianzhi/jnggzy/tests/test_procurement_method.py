from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from jnggzy import BidModelClient  # noqa: E402


def test_bid_model_client_normalizes_unknown_procurement_method_to_other() -> None:
    client = BidModelClient()
    client.post_model = lambda _content: {  # type: ignore[method-assign]
        "final_result": {
            "项目编号": "MODEL-001",
            "项目名称": "模型项目",
            "预算金额": "998万元",
            "采购方式": "评定分离",
            "采购人名称": "模型采购人",
            "采购人地址": "模型地址",
            "项目联系人": "张三",
            "项目联系方式": "0531-12345678",
        }
    }

    result = client.get_result("正文")

    assert result["procurementMethod"] == "其他类型"


def test_bid_model_client_keeps_empty_procurement_method_empty() -> None:
    client = BidModelClient()
    client.post_model = lambda _content: {  # type: ignore[method-assign]
        "final_result": {
            "项目编号": "MODEL-001",
            "项目名称": "模型项目",
            "预算金额": "998万元",
            "采购方式": "",
            "采购人名称": "模型采购人",
            "采购人地址": "模型地址",
            "项目联系人": "张三",
            "项目联系方式": "0531-12345678",
        }
    }

    result = client.get_result("正文")

    assert result["procurementMethod"] == ""
