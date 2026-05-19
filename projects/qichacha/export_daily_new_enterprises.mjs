import fs from "node:fs/promises";
import path from "node:path";

import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

function getArg(flag) {
  const index = process.argv.indexOf(flag);
  if (index === -1 || index + 1 >= process.argv.length) {
    throw new Error(`Missing argument: ${flag}`);
  }
  return process.argv[index + 1];
}

function buildRows(payload) {
  return payload.rows.map((row) => [
    row.company_name,
    row.credit_code,
    row.legal_representative,
    row.registered_address,
    row.registered_capital_10k_cny,
    row.business_address,
    row.establish_date,
    row.approval_date,
    row.business_type,
    row.source_dataset,
    row.source_catalog_id,
  ]);
}

async function main() {
  const inputPath = getArg("--input");
  const outputPath = getArg("--output");
  const payload = JSON.parse(await fs.readFile(inputPath, "utf8"));

  const workbook = Workbook.create();
  const sheet = workbook.worksheets.add("A表");
  sheet.showGridLines = false;

  sheet.getRange("A1:K1").merge();
  sheet.getRange("A1").values = [[`泰州每日新增企业主表 - ${payload.target_date}`]];
  sheet.getRange("A2:K2").merge();
  sheet.getRange("A2").values = [[`官方来源：${payload.source_catalogs.map((item) => `${item.catalog_id} ${item.dataset_name}`).join("；")}`]];
  sheet.getRange("A3:K3").merge();
  sheet.getRange("A3").values = [[`生成时间：${payload.generated_at}；记录数：${payload.row_count}`]];

  const headers = [[
    "企业名称",
    "统一社会信用代码",
    "法定代表人/负责人/经营者",
    "住所",
    "注册资本（万）",
    "生产经营地/经营场所",
    "成立日期",
    "核准日期",
    "业务类型",
    "来源目录",
    "目录ID",
  ]];
  sheet.getRange("A5:K5").values = headers;

  const rows = buildRows(payload);
  if (rows.length > 0) {
    sheet.getRangeByIndexes(5, 0, rows.length, 11).values = rows;
  }

  sheet.getRange("A1:K1").format = {
    fill: "#0F4C81",
    font: { color: "#FFFFFF", bold: true, size: 16 },
    horizontalAlignment: "center",
    verticalAlignment: "center",
  };
  sheet.getRange("A2:K3").format = {
    fill: "#EAF2F8",
    font: { color: "#1F2937" },
    horizontalAlignment: "left",
    verticalAlignment: "center",
  };
  sheet.getRange("A5:K5").format = {
    fill: "#D9EAF7",
    font: { bold: true, color: "#0F172A" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
  };
  if (rows.length > 0) {
    sheet.getRangeByIndexes(5, 0, rows.length, 11).format = {
      verticalAlignment: "center",
      wrapText: true,
    };
  }

  sheet.getRange("G6:H2000").setNumberFormat("yyyy-mm-dd");
  sheet.freezePanes.freezeRows(5);
  sheet.getRange("A:K").format.columnWidthPx = 140;
  sheet.getRange("A:A").format.columnWidthPx = 220;
  sheet.getRange("B:B").format.columnWidthPx = 180;
  sheet.getRange("C:C").format.columnWidthPx = 160;
  sheet.getRange("D:F").format.columnWidthPx = 240;
  sheet.getRange("J:K").format.columnWidthPx = 140;

  const inspect = await workbook.inspect({
    kind: "table",
    range: `A表!A1:K${Math.max(rows.length + 5, 8)}`,
    include: "values",
    tableMaxRows: 12,
    tableMaxCols: 11,
  });
  console.log(inspect.ndjson);

  const renderBlob = await workbook.render({
    sheetName: "A表",
    range: `A1:K${Math.max(rows.length + 5, 8)}`,
    scale: 1,
    format: "png",
  });
  const previewPath = outputPath.replace(/\.xlsx$/i, ".png");
  await fs.writeFile(previewPath, new Uint8Array(await renderBlob.arrayBuffer()));

  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);
}

await main();
