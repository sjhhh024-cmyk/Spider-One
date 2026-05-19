from __future__ import annotations

import csv
import io
import json
import re
import ssl
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


BASE_URL = "https://opendata.taizhou.gov.cn/oportal"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"
EXPORTER_SCRIPT = Path(__file__).resolve().parent / "export_daily_new_enterprises.mjs"


DATASETS = (
    {"catalog_id": "20266", "dataset_name": "市场主体登记信息"},
    {"catalog_id": "20277", "dataset_name": "合伙企业设立登记信息"},
    {"catalog_id": "20330", "dataset_name": "个人独资企业设立登记信息"},
)


DOWNLOAD_LINK_RE = re.compile(
    r'class="downloadFileLink"\s+id="(?P<token>[^"]+)"[\s\S]*?class="file-name">(?P<filename>[^<]+)</span>',
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DatasetAsset:
    format: str
    filename: str
    token: str


def extract_dataset_assets(detail_html: str) -> dict[str, DatasetAsset]:
    assets: dict[str, DatasetAsset] = {}
    for match in DOWNLOAD_LINK_RE.finditer(detail_html):
        filename = match.group("filename").strip()
        token = match.group("token").strip()
        extension = filename.rsplit(".", 1)[-1].lower()
        assets[extension] = DatasetAsset(format=extension, filename=filename, token=token)
    return assets


def decode_csv_rows(csv_bytes: bytes) -> list[dict[str, str]]:
    text = csv_bytes.decode("gb18030")
    reader = csv.DictReader(io.StringIO(text))
    return [{key: (value or "").strip() for key, value in row.items() if key} for row in reader]


def normalize_record(record: dict[str, str]) -> dict[str, str]:
    credit_code = record.get("统一社会信用代码", "").strip()
    if not credit_code:
        raise ValueError("missing credit code")

    return {
        "company_name": record.get("企业名称", "").strip(),
        "credit_code": credit_code,
        "legal_representative": record.get("法定代表人、负责人、经营者", "").strip(),
        "registered_address": record.get("住所", "").strip(),
        "registered_capital_10k_cny": record.get("注册资本（万）", "").strip(),
        "business_address": record.get("生产经营地、个体户经营场所", "").strip(),
        "establish_date": _normalize_date_string(record.get("成立日期", "")),
        "approval_date": _normalize_date_string(record.get("核准日期", "")),
        "business_type": record.get("业务类型", "").strip(),
        "source_dataset": record.get("_dataset_name", "").strip(),
        "source_catalog_id": record.get("_catalog_id", "").strip(),
    }


def filter_records_by_date(rows: list[dict[str, str]], target_date: date) -> list[dict[str, str]]:
    target = target_date.isoformat()
    filtered: list[dict[str, str]] = []
    seen_credit_codes: set[str] = set()
    for row in rows:
        if row["establish_date"] != target:
            continue
        if row["credit_code"] in seen_credit_codes:
            continue
        seen_credit_codes.add(row["credit_code"])
        filtered.append(row)
    return filtered


def _normalize_date_string(raw: str) -> str:
    value = raw.strip()
    if not value:
        return ""
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return value


def fetch_detail_html(catalog_id: str) -> str:
    url = f"{BASE_URL}/catalog/{catalog_id}"
    return _fetch_text(url)


def fetch_csv_rows(catalog_id: str, dataset_name: str) -> list[dict[str, str]]:
    detail_html = fetch_detail_html(catalog_id)
    assets = extract_dataset_assets(detail_html)
    csv_asset = assets.get("csv")
    if csv_asset is None:
        raise RuntimeError(f"{dataset_name} 缺少 CSV 下载资产")

    csv_bytes = _fetch_bytes(build_download_url(catalog_id, dataset_name, csv_asset.token))
    rows = decode_csv_rows(csv_bytes)
    for row in rows:
        row["_dataset_name"] = dataset_name
        row["_catalog_id"] = catalog_id
    return rows


def build_download_url(catalog_id: str, dataset_name: str, token: str) -> str:
    return (
        f"{BASE_URL}/catalog/download"
        f"?cataId={urllib.parse.quote(catalog_id, safe='')}"
        f"&cataName={urllib.parse.quote(dataset_name, safe='')}"
        f"&idInRc={urllib.parse.quote(token, safe='')}"
    )


def collect_daily_new_enterprises(target_date: date) -> list[dict[str, str]]:
    normalized_rows: list[dict[str, str]] = []
    for dataset in DATASETS:
        raw_rows = fetch_csv_rows(dataset["catalog_id"], dataset["dataset_name"])
        normalized_rows.extend(normalize_record(row) for row in raw_rows)
    return filter_records_by_date(normalized_rows, target_date=target_date)


def export_daily_new_enterprises(target_date: date, output_dir: Path = DEFAULT_OUTPUT_DIR) -> tuple[Path, Path]:
    rows = collect_daily_new_enterprises(target_date)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    date_label = target_date.isoformat()
    json_path = output_dir / f"taizhou_daily_new_enterprises_{date_label}.json"
    xlsx_path = output_dir / f"taizhou_daily_new_enterprises_{date_label}.xlsx"

    payload = {
        "target_date": date_label,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source_site": BASE_URL,
        "source_catalogs": list(DATASETS),
        "row_count": len(rows),
        "rows": rows,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    _run_exporter(json_path=json_path, xlsx_path=xlsx_path)
    return json_path, xlsx_path


def _run_exporter(json_path: Path, xlsx_path: Path) -> None:
    command = [
        "node",
        str(EXPORTER_SCRIPT),
        "--input",
        str(json_path.resolve()),
        "--output",
        str(xlsx_path.resolve()),
    ]
    subprocess.run(command, check=True, cwd=str(EXPORTER_SCRIPT.parent))


def _build_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        },
    )


def _fetch_text(url: str) -> str:
    return _fetch_bytes(url).decode("utf-8", errors="ignore")


def _fetch_bytes(url: str) -> bytes:
    request = _build_request(url)
    context = ssl._create_unverified_context()
    with urllib.request.urlopen(request, context=context, timeout=60) as response:
        return response.read()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="生成泰州每日新增企业 A 表")
    parser.add_argument("--date", default=date.today().isoformat(), help="目标日期，格式 YYYY-MM-DD")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="输出目录")
    args = parser.parse_args()

    target_date = date.fromisoformat(args.date)
    json_path, xlsx_path = export_daily_new_enterprises(target_date=target_date, output_dir=Path(args.output_dir))
    print(json_path)
    print(xlsx_path)


if __name__ == "__main__":
    main()
