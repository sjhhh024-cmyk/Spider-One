from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from jnggzy import build_file_info, extract_attachment_files  # noqa: E402


def test_extract_attachment_files_keeps_real_anchor_text_as_file_name() -> None:
    html = (
        '<html><body>'
        '<a href="/download/file/abc123">开平市塘口镇正坑水库迎水坡坝脚度汛抢险工程结算需求书.pdf</a>'
        '</body></html>'
    )

    attachments = extract_attachment_files(html, "https://example.com/detail")

    assert attachments == [
        {
            "fileUrl": "https://example.com/download/file/abc123",
            "fileType": "",
            "fileName": "开平市塘口镇正坑水库迎水坡坝脚度汛抢险工程结算需求书.pdf",
        }
    ]


def test_build_file_info_uses_real_name_and_url_suffix_fallback() -> None:
    attachments = [
        {
            "fileUrl": "https://example.com/download/file/abc123",
            "fileType": "",
            "fileName": "真实附件名.docx",
        },
        {
            "fileUrl": "https://example.com/files/result.pdf",
            "fileType": "",
            "fileName": "",
        },
    ]

    file_info = build_file_info(attachments)

    assert file_info == [
        {
            "fileUrl": "https://example.com/download/file/abc123",
            "fileType": "docx",
            "fileName": "真实附件名.docx",
        },
        {
            "fileUrl": "https://example.com/files/result.pdf",
            "fileType": "pdf",
            "fileName": "result.pdf",
        },
    ]
