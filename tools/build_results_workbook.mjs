import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const projectRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(.:)/, "$1")), "..");
const resultsDir = path.join(projectRoot, "results", "criticidade_v2");
const previewDir = path.join(resultsDir, "previews_progressiva");
const outputPath = path.join(resultsDir, "resultados_validacao_progressiva_h1_h4.xlsx");
const font = "Aptos";

function parseCSV(text) {
  const rows = [];
  let row = [], field = "", quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (char === '"') {
      if (quoted && text[i + 1] === '"') { field += '"'; i += 1; }
      else quoted = !quoted;
    } else if (char === "," && !quoted) { row.push(field); field = ""; }
    else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && text[i + 1] === "\n") i += 1;
      row.push(field); field = "";
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
    } else field += char;
  }
  if (field !== "" || row.length) { row.push(field); rows.push(row); }
  if (rows.length) rows[0][0] = rows[0][0].replace(/^\uFEFF/, "");
  return rows.map((values, rowIndex) => values.map((value) => {
    if (rowIndex === 0 || value === "") return value;
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : value;
  }));
}

function columnLetter(index) {
  let value = index + 1, result = "";
  while (value > 0) {
    result = String.fromCharCode(65 + ((value - 1) % 26)) + result;
    value = Math.floor((value - 1) / 26);
  }
  return result;
}

async function csvRows(filename) {
  return parseCSV(await fs.readFile(path.join(resultsDir, filename), "utf8"));
}

function selectColumns(rows, selected) {
  const indexes = selected.map((name) => rows[0].indexOf(name));
  return rows.map((row) => indexes.map((index) => row[index]));
}

function addDataSheet(workbook, name, rows, percentHeaders = []) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  const last = columnLetter(rows[0].length - 1);
  sheet.getRange(`A1:${last}${rows.length}`).values = rows;
  sheet.getRange(`A1:${last}1`).format = {
    fill: "#1F4E78", font: { name: font, size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center", verticalAlignment: "center", wrapText: true,
    borders: { preset: "inside", style: "thin", color: "#FFFFFF" },
  };
  sheet.getRange(`A1:${last}1`).format.rowHeight = 48;
  if (rows.length > 1) sheet.getRange(`A2:${last}${rows.length}`).format.font = { name: font, size: 10 };
  sheet.freezePanes.freezeRows(1);
  rows[0].forEach((header, index) => {
    const width = header === "modelo" ? 31 : Math.min(27, Math.max(11, String(header).length + 2));
    sheet.getRangeByIndexes(0, index, rows.length, 1).format.columnWidth = width;
    if (percentHeaders.includes(header) && rows.length > 1) {
      sheet.getRangeByIndexes(1, index, rows.length - 1, 1).setNumberFormat("0.00%");
    }
  });
  return { sheet, last, rows: rows.length };
}

const allMetricsRaw = await csvRows("comparacao_todos_horizontes.csv");
const metricColumns = [
  "modelo", "horizonte_semanas", "n_amostras_teste", "acuracia", "acuracia_balanceada",
  "f1_macro", "f2_macro", "pr_auc_macro", "erro_absoluto_nivel_medio",
  "kappa_quadratico", "subestimacao_grave_taxa", "tipo",
];
const allMetrics = selectColumns(allMetricsRaw, metricColumns);
const means = await csvRows("resumo_medio_horizontes.csv");
const categoriesRaw = await csvRows("comparacao_categorias_todos_horizontes.csv");
const categoryHeader = categoriesRaw[0];
const modelIndex = categoryHeader.indexOf("modelo");
const categoryIndex = categoryHeader.indexOf("categoria");
const severeCategories = [categoryHeader, ...categoriesRaw.slice(1).filter((row) =>
  ["XGBoost", "RNA", "LSTM"].includes(row[modelIndex]) && ["Alto", "Critico"].includes(row[categoryIndex])
)];
const validations = await csvRows("validacao_progressiva_todos_modelos.csv");
const hyperparameters = await csvRows("hiperparametros_xgboost_horizontes.csv");
const optimizationParts = [];
for (let horizon = 1; horizon <= 4; horizon += 1) {
  const rows = await csvRows(`otimizacao_xgboost_h${horizon}.csv`);
  if (optimizationParts.length === 0) optimizationParts.push(["horizonte_semanas", ...rows[0]]);
  optimizationParts.push(...rows.slice(1).map((row) => [horizon, ...row]));
}

const workbook = Workbook.create();
const summary = workbook.worksheets.add("Resumo");
summary.showGridLines = false;
summary.tabColor = "#17365D";
const sheets = [];
sheets.push(addDataSheet(workbook, "Teste 2021", allMetrics, ["acuracia", "acuracia_balanceada", "f1_macro", "f2_macro", "pr_auc_macro", "subestimacao_grave_taxa"]));
sheets.push(addDataSheet(workbook, "Medias", means, ["acuracia", "acuracia_balanceada", "f1_macro", "f2_macro", "pr_auc_macro", "subestimacao_grave_taxa"]));
sheets.push(addDataSheet(workbook, "Classes graves", severeCategories, ["precisao", "recall_sensibilidade", "f1", "f2"]));
sheets.push(addDataSheet(workbook, "Validacao temporal", validations, ["acuracia", "acuracia_balanceada", "f1_macro", "f2_macro", "pr_auc_macro", "acuracia_ate_um_nivel", "subestimacao_grave_taxa"]));
sheets.push(addDataSheet(workbook, "Hiperparametros", hyperparameters));
sheets.push(addDataSheet(workbook, "Otimizacao XGB", optimizationParts, ["validacao_oof_acuracia", "validacao_oof_acuracia_balanceada", "validacao_oof_f1_macro", "validacao_oof_f2_macro", "validacao_oof_f1_ponderado", "validacao_oof_pr_auc_macro", "validacao_oof_acuracia_ate_um_nivel", "validacao_oof_subestimacao_grave_taxa"]));

summary.getRange("A2:F2").merge();
summary.getRange("A2").values = [["Desempenho dos modelos por horizonte de previsão"]];
summary.getRange("A2:F2").format = { font: { name: "Aptos Display", size: 16, bold: true, color: "#17365D" }, verticalAlignment: "center" };
summary.getRange("A3:N3").format.borders = { bottom: { style: "medium", color: "#5B9BD5" } };
summary.getRange("A4").values = [["Teste retrospectivo em 2021. Treinamento final em 2015–2020. Validação progressiva em cinco cortes temporais."]];
summary.getRange("A4:F4").format = { font: { name: font, size: 10, italic: true, color: "#595959" } };

summary.getRange("A6:E6").values = [["Horizonte (semanas)", "XGBoost", "LSTM", "RNA", "Persistência"]];
summary.getRange("A6:E6").format = { fill: "#1F4E78", font: { name: font, size: 10, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center" };
summary.getRange("A7:A10").values = [[1], [2], [3], [4]];
for (let row = 7; row <= 10; row += 1) {
  for (let col = 2; col <= 5; col += 1) {
    const modelHeader = `${columnLetter(col - 1)}$6`;
    const modelFormula = col === 5 ? '"Referencia: persistencia"' : modelHeader;
    summary.getCell(row - 1, col - 1).formulas = [[`=SUMIFS('Teste 2021'!$G$2:$G$21,'Teste 2021'!$A$2:$A$21,${modelFormula},'Teste 2021'!$B$2:$B$21,$A${row})`]];
  }
}
summary.getRange("B7:E10").setNumberFormat("0.00%");
summary.getRange("A6:E10").format.font = { name: font, size: 10 };
summary.getRange("A6:E10").format.borders = { preset: "outside", style: "thin", color: "#B4C6E7" };

summary.getRange("A13:E13").values = [["Modelo", "Acurácia balanceada média", "F1 macro médio", "F2 macro médio", "PR-AUC macro média"]];
summary.getRange("A13:E13").format = { fill: "#4472C4", font: { name: font, size: 10, bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", wrapText: true };
summary.getRange("A14:A16").values = [["XGBoost"], ["LSTM"], ["RNA"]];
for (let row = 14; row <= 16; row += 1) {
  summary.getRange(`B${row}`).formulas = [[`=AVERAGEIFS('Teste 2021'!$E$2:$E$21,'Teste 2021'!$A$2:$A$21,$A${row})`]];
  summary.getRange(`C${row}`).formulas = [[`=AVERAGEIFS('Teste 2021'!$F$2:$F$21,'Teste 2021'!$A$2:$A$21,$A${row})`]];
  summary.getRange(`D${row}`).formulas = [[`=AVERAGEIFS('Teste 2021'!$G$2:$G$21,'Teste 2021'!$A$2:$A$21,$A${row})`]];
  summary.getRange(`E${row}`).formulas = [[`=AVERAGEIFS('Teste 2021'!$H$2:$H$21,'Teste 2021'!$A$2:$A$21,$A${row})`]];
}
summary.getRange("B14:E16").setNumberFormat("0.00%");
summary.getRange("A13:E16").format.font = { name: font, size: 10 };
summary.getRange("A13:E16").format.borders = { preset: "outside", style: "thin", color: "#B4C6E7" };

summary.getRange("A19:F20").merge();
summary.getRange("A19").values = [["O XGBoost liderou F2 macro e acurácia balanceada nos quatro horizontes. A performance cai com o horizonte: o F2 macro do XGBoost passa de 85,93% em uma semana para 44,81% em quatro semanas."]];
summary.getRange("A19:F20").format = { fill: "#E2F0D9", font: { name: font, size: 10, bold: true, color: "#375623" }, wrapText: true, verticalAlignment: "center" };
summary.getRange("A22:F23").merge();
summary.getRange("A22").values = [["No horizonte 4, o recall exato do XGBoost foi 10,20% para Alto e 11,11% para Crítico. Esse horizonte deve ser interpretado como sinal antecipado de risco, não como classificação exata confiável."]];
summary.getRange("A22:F23").format = { fill: "#FFF2CC", font: { name: font, size: 10, color: "#7F6000" }, wrapText: true, verticalAlignment: "center" };
summary.getRange("A25:B28").values = [
  ["Fonte de casos", "Base consolidada de dengue do Recife, 2015–2021"],
  ["Fonte climática", "INMET semanal do Recife"],
  ["População", "Censo IBGE 2022, constante no período"],
  ["Categorias", "Baixo <100; Médio <300; Alto <500; Crítico ≥500 por 100 mil em quatro semanas"],
];
summary.getRange("A25:A28").format = { fill: "#D9EAF7", font: { name: font, size: 10, bold: true } };
summary.getRange("B25:B28").format = { font: { name: font, size: 10 }, wrapText: true };
summary.getRange("A25:B27").format.rowHeight = 30;
summary.getRange("A28:B28").format.rowHeight = 45;
summary.getRange("A:A").format.columnWidth = 24;
summary.getRange("B:E").format.columnWidth = 22;
summary.getRange("F:F").format.columnWidth = 12;

const chart = summary.charts.add("line", summary.getRange("A6:D10"));
chart.title = "F2 macro por horizonte";
chart.titleTextStyle.typeface = font;
chart.legend = { position: "bottom", textStyle: { typeface: font } };
chart.xAxis = { axisType: "textAxis", textStyle: { typeface: font } };
chart.yAxis = { numberFormatCode: "0%", numberFormatSourceLinked: false, textStyle: { typeface: font } };
chart.setPosition("G5", "N17");

await fs.mkdir(previewDir, { recursive: true });
workbook.recalculate();
const inspection = await workbook.inspect({ kind: "table", range: "Resumo!A2:N28", include: "values,formulas", tableMaxRows: 28, tableMaxCols: 14, maxChars: 7000 });
console.log(`INSPECT\n${inspection.ndjson}`);
const errorScan = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!", options: { useRegex: true, maxResults: 100 }, maxChars: 4000 });
console.log(`ERROR_SCAN\n${errorScan.ndjson}`);
const renderSpecs = [{ sheet: summary, name: "resumo", range: "A1:N28" }, ...sheets.map((item) => ({ sheet: item.sheet, name: item.sheet.name.replace(/ /g, "_"), range: `A1:${item.last}${Math.min(item.rows, 18)}` }))];
for (const spec of renderSpecs) {
  const preview = await workbook.render({ sheetName: spec.sheet.name, range: spec.range, scale: 1, format: "png" });
  await fs.writeFile(path.join(previewDir, `${spec.name}.png`), new Uint8Array(await preview.arrayBuffer()));
}
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`SAVED ${outputPath}`);
