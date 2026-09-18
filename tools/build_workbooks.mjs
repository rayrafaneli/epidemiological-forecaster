import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const projectRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(.:)/, "$1")), "..");
const dataDir = path.join(projectRoot, "data", "processed");
const previewDir = path.join(projectRoot, "docs", "previews");

const allSpecs = [
  {
    csv: "populacao_censo_2022_processada.csv",
    xlsx: "populacao_censo_2022_processada.xlsx",
    sheet: "Populacao",
    description: "Populacao canonica dos 94 bairros; exclusivamente Censo 2022.",
  },
  {
    csv: "dengue_2015_2021_processada.csv",
    xlsx: "dengue_2015_2021_processada.xlsx",
    sheet: "Dengue",
    description: "Casos elegiveis de 2015 a 2021 depois de filtros, mapeamento e deduplicacao.",
  },
  {
    csv: "clima_2015_2021_processado.csv",
    xlsx: "clima_2015_2021_processado.xlsx",
    sheet: "Clima",
    description: "Clima semanal com ausencias preenchidas pela mediana da mesma semana em 2015-2020.",
  },
  {
    csv: "painel_semanal_2015_2021_h1.csv",
    xlsx: "painel_semanal_2015_2021_h1.xlsx",
    sheet: "Painel_h1",
    description: "Painel bairro-semana, lags e alvo futuro para horizonte de uma semana.",
  },
];
const requested = process.argv[2];
const specs = requested ? allSpecs.filter((spec) => spec.sheet === requested) : allSpecs;
if (requested && specs.length === 0) {
  throw new Error(`Planilha desconhecida: ${requested}`);
}

const booleanColumns = new Set(["precipitacao_imputada", "temperatura_imputada"]);
const dateColumns = new Set(["dt_diagnostico_sintoma"]);

function isNumericColumn(name) {
  if (["ano_censo", "populacao", "ano_arquivo_origem", "linha_origem", "epi_year", "epi_week"].includes(name)) {
    return true;
  }
  return /^(casos_|chuva_|temp_|precipitacao_|temperatura_|time_index|week_|target_|taxa_|horizonte_|mediana_)/.test(name);
}

function columnLetter(index) {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    value = Math.floor((value - 1) / 26);
  }
  return result;
}

function convertTypes(values) {
  const headers = values[0].map((value) => String(value ?? "").replace(/^\uFEFF/, ""));
  values[0] = headers;
  for (let col = 0; col < headers.length; col += 1) {
    const header = headers[col];
    for (let row = 1; row < values.length; row += 1) {
      const current = values[row][col];
      if (current === null || current === undefined || current === "") continue;
      if (booleanColumns.has(header)) {
        values[row][col] = String(current).toLowerCase() === "true";
      } else if (dateColumns.has(header)) {
        const parsed = new Date(`${current}T00:00:00`);
        if (!Number.isNaN(parsed.valueOf())) values[row][col] = parsed;
      } else if (isNumericColumn(header)) {
        const parsed = Number(current);
        if (Number.isFinite(parsed)) values[row][col] = parsed;
      }
    }
  }
  return headers;
}

await fs.mkdir(previewDir, { recursive: true });

for (const spec of specs) {
  const csvPath = path.join(dataDir, spec.csv);
  const fullCsvText = await fs.readFile(csvPath, "utf8");
  const sampleRows = Number(process.env.SAMPLE_ROWS || 0);
  const csvText = sampleRows > 0
    ? fullCsvText.split(/\r?\n/).slice(0, sampleRows + 1).join("\n")
    : fullCsvText;
  const workbook = await Workbook.fromCSV(csvText, { sheetName: spec.sheet });
  const dataSheet = workbook.worksheets.getItem(spec.sheet);
  const used = dataSheet.getUsedRange();
  const values = used.values;
  const headers = convertTypes(values);
  used.values = values;

  const rowCount = values.length;
  const colCount = headers.length;
  const lastColumn = columnLetter(colCount - 1);
  const header = dataSheet.getRange(`A1:${lastColumn}1`);
  header.format = {
    fill: "#1F4E78",
    font: { name: "Aptos", size: 11, bold: true, color: "#FFFFFF" },
    wrapText: true,
    verticalAlignment: "center",
  };
  header.format.rowHeight = 32;
  dataSheet.freezePanes.freezeRows(1);
  dataSheet.showGridLines = false;

  for (let col = 0; col < colCount; col += 1) {
    const name = headers[col];
    const columnRange = dataSheet.getRangeByIndexes(0, col, rowCount, 1);
    columnRange.format.font = { name: "Aptos", size: 10 };
    columnRange.format.columnWidth = Math.min(
      28,
      Math.max(11, name.length > 20 ? 22 : name.length + 2),
    );
    if (rowCount > 1 && dateColumns.has(name)) {
      dataSheet.getRangeByIndexes(1, col, rowCount - 1, 1).setNumberFormat("yyyy-mm-dd");
    } else if (rowCount > 1 && isNumericColumn(name)) {
      const decimals = /(taxa_|week_|precipitacao_|temp_|chuva_|mediana_)/.test(name) ? "0.000" : "0";
      dataSheet.getRangeByIndexes(1, col, rowCount - 1, 1).setNumberFormat(decimals);
    }
  }

  const summary = workbook.worksheets.add("Resumo");
  summary.showGridLines = false;
  summary.getRange("A1:F1").merge();
  summary.getRange("A1").values = [["Base processada para o experimento de dengue"]];
  summary.getRange("A1:F1").format = {
    fill: "#1F4E78",
    font: { name: "Aptos Display", size: 18, bold: true, color: "#FFFFFF" },
    verticalAlignment: "center",
  };
  summary.getRange("A1:F1").format.rowHeight = 34;
  summary.getRange("A3:B8").values = [
    ["Arquivo", spec.xlsx],
    ["Planilha de dados", spec.sheet],
    ["Linhas de dados", rowCount - 1],
    ["Colunas", colCount],
    ["Descricao", spec.description],
    ["Observacao", "Fonte bruta preservada; transformacoes e auditorias ficam no projeto."],
  ];
  summary.getRange("A3:A8").format = {
    fill: "#D9EAF7",
    font: { name: "Aptos", bold: true, color: "#1F1F1F" },
  };
  summary.getRange("B3:B8").format = { font: { name: "Aptos", size: 11 }, wrapText: true };
  summary.getRange("A3:B8").format.borders = { preset: "all", style: "thin", color: "#C9D4DF" };
  summary.getRange("A:A").format.columnWidth = 22;
  summary.getRange("B:B").format.columnWidth = 68;
  summary.getRange("A10:F10").merge();
  summary.getRange("A10").values = [["Consulte os CSVs de auditoria para os registros removidos, bairros nao mapeados e imputacoes climaticas."]];
  summary.getRange("A10:F10").format = {
    fill: "#FFF2CC",
    font: { name: "Aptos", italic: true, color: "#7F6000" },
    wrapText: true,
  };
  summary.getRange("A10:F10").format.rowHeight = 34;

  workbook.recalculate();
  const inspection = await workbook.inspect({
    kind: "region",
    sheetId: spec.sheet,
    range: `A1:${columnLetter(Math.min(colCount, 8) - 1)}6`,
    maxChars: 3500,
  });
  console.log(`INSPECT ${spec.xlsx}\n${inspection.ndjson}`);
  const errorScan = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 20 },
    maxChars: 2000,
  });
  console.log(`ERROR_SCAN ${spec.xlsx}\n${errorScan.ndjson}`);
  if (process.env.SKIP_RENDER !== "1") {
    const previewSheet = process.env.RENDER_DATA === "1" ? spec.sheet : "Resumo";
    const preview = await workbook.render({ sheetName: previewSheet, autoCrop: "all", scale: 1, format: "png" });
    await fs.writeFile(
      path.join(previewDir, spec.xlsx.replace(/\.xlsx$/, ".png")),
      new Uint8Array(await preview.arrayBuffer()),
    );
  }
  if (process.env.SKIP_EXPORT !== "1") {
    const output = await SpreadsheetFile.exportXlsx(workbook);
    await output.save(path.join(dataDir, spec.xlsx));
    console.log(`SAVED ${path.join(dataDir, spec.xlsx)}`);
  }
}
