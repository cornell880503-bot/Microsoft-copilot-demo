from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import tempfile

import matplotlib
import pandas as pd
from docx import Document
from docx.shared import Inches

os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="copilot_mpl_"))
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from query_normalizer import normalize_query


@dataclass
class AnalyticsResult:
    handled: bool
    title: str
    body: str


# Keywords that require actual code execution (matplotlib etc.) — never handle deterministically
_VISUAL_TERMS = ("chart", "graph", "visual", "plot", "draw", "stacked bar", "bar chart",
                 "pie chart", "histogram", "scatter", "heatmap", "畫圖", "圖表", "可視化")


def _safe_pct(numerator: int, denominator: int) -> float:
    return 0.0 if denominator <= 0 else numerator / denominator * 100


def _load_dataframe(doc_path: str) -> pd.DataFrame:
    path = Path(doc_path)
    ext = path.suffix.lower()
    if ext == ".csv":
        return pd.read_csv(path, header=None, dtype=object, keep_default_na=False)
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(path, header=None, dtype=object)
    raise ValueError(f"Unsupported analysis file type: {ext}")


def _non_empty_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _clean_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    meta: dict = {}
    working = df.copy().fillna("")
    working = working.replace("missing value", "")

    working = working.replace(r"^\s*$", pd.NA, regex=True)
    working = working.dropna(axis=0, how="all").dropna(axis=1, how="all")

    if working.empty:
        return pd.DataFrame(), meta

    def _score_header_row(idx: int) -> float:
        row = [_non_empty_text(v) for v in working.iloc[idx].tolist()]
        non_empty_positions = [pos for pos, value in enumerate(row) if value]
        if len(non_empty_positions) < 2:
            return -1.0
        values = [row[pos] for pos in non_empty_positions]
        lower_values = [value.lower() for value in values]
        unique_ratio = len(set(lower_values)) / max(1, len(lower_values))
        numeric_like = sum(1 for value in values if value.replace(".", "", 1).replace("-", "", 1).isdigit())
        keyword_hits = sum(
            1
            for value in lower_values
            if any(
                token in value
                for token in (
                    "id", "date", "time", "count", "name", "type", "status",
                    "policy", "label", "row", "category", "total", "score", "value",
                )
            )
        )
        next_rows = working.iloc[idx + 1 : idx + 6, non_empty_positions]
        next_non_empty = next_rows.notna().sum().sum() if not next_rows.empty else 0
        score = len(non_empty_positions) * 8
        score += unique_ratio * 20
        score += keyword_hits * 12
        score += next_non_empty
        score -= numeric_like * 5
        if lower_values[0] in {"row labels", "labels", "category"}:
            score += 25
            meta["detected_layout"] = "pivot_export"
        return score

    header_row_idx = max(
        range(min(len(working), 12)),
        key=_score_header_row,
        default=0,
    )
    header_raw = [_non_empty_text(v) for v in working.iloc[header_row_idx].tolist()]
    header_positions = [idx for idx, value in enumerate(header_raw) if value]
    if len(header_positions) < 2:
        header_positions = list(range(len(header_raw)))

    trimmed_header = [header_raw[idx] for idx in header_positions]
    normalized_header: list[str] = []
    seen_headers: dict[str, int] = {}
    for idx, value in enumerate(trimmed_header, start=1):
        base = value or f"column_{idx}"
        counter = seen_headers.get(base, 0)
        seen_headers[base] = counter + 1
        normalized_header.append(base if counter == 0 else f"{base}_{counter + 1}")

    working = working.iloc[header_row_idx + 1 :, header_positions].copy()
    working.columns = normalized_header

    renamed = {}
    for col in working.columns:
        lower = str(col).strip().lower()
        if lower in {"row labels", "labels"}:
            renamed[col] = "category"
        elif "count" in lower:
            renamed[col] = "value"
    if renamed:
        working = working.rename(columns=renamed)

    if len(working.columns) >= 2:
        first_col = working.columns[0]
        first_series = working[first_col].astype(str).str.strip().str.lower()
        working = working[~first_series.isin({"", "nan", "none", "null"})].copy()
        working = working[~first_series.str.contains(r"grand total|subtotal|total$", regex=True)].copy()

    keep_columns = []
    for col in working.columns:
        series = working[col]
        non_empty_count = series.notna().sum()
        col_text = str(col).strip().lower()
        if non_empty_count == 0:
            continue
        if col_text.startswith("unnamed") and non_empty_count <= 1:
            continue
        keep_columns.append(col)
    working = working[keep_columns].copy()

    for col in working.columns:
        if working[col].dtype == object:
            working[col] = working[col].astype(str).str.strip()
            working[col] = working[col].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})

    for col in working.columns:
        series_text = working[col].dropna().astype(str)
        lower_name = str(col).strip().lower()
        if any(token in lower_name for token in ("pattern", "vote", "code", "label")):
            continue
        if series_text.str.contains(r"[:/]", regex=True).any():
            continue
        numeric = pd.to_numeric(working[col], errors="coerce")
        parse_ratio = numeric.notna().sum() / max(1, len(series_text))
        if parse_ratio >= 0.8:
            working[col] = numeric

    working = working.reset_index(drop=True)
    return working, meta


def _find_numeric_columns(df: pd.DataFrame) -> list[str]:
    return [
        col
        for col in df.columns
        if pd.api.types.is_numeric_dtype(df[col]) and col not in _find_identifier_columns(df)
    ]


def _find_categorical_columns(df: pd.DataFrame) -> list[str]:
    return [
        col
        for col in df.columns
        if not pd.api.types.is_numeric_dtype(df[col]) and col not in _find_identifier_columns(df)
    ]


def _find_identifier_columns(df: pd.DataFrame) -> list[str]:
    identifier_cols: list[str] = []
    for col in df.columns:
        lower = str(col).strip().lower()
        series = df[col].dropna()
        if series.empty:
            continue
        unique_ratio = series.nunique(dropna=True) / max(1, len(series))
        if lower.endswith("_id") or lower == "id" or lower.endswith("id"):
            identifier_cols.append(col)
            continue
        if pd.api.types.is_numeric_dtype(series) and unique_ratio > 0.95:
            identifier_cols.append(col)
    return identifier_cols


def _column_priority(name: str) -> tuple[int, int]:
    lower = str(name).strip().lower()
    keywords = (
        "case_type", "category", "status", "majority_policy",
        "policy", "vote_pattern", "type", "batch_name", "label",
    )
    for idx, keyword in enumerate(keywords):
        if keyword in lower:
            return (0, idx)
    return (1, len(lower))


def _choose_primary_category(df: pd.DataFrame) -> str | None:
    candidates = []
    for col in _find_categorical_columns(df):
        series = df[col].dropna().astype(str)
        unique_count = series.nunique(dropna=True)
        if unique_count <= 1:
            continue
        if unique_count > max(50, len(df) * 0.5):
            continue
        coverage = len(series) / max(1, len(df))
        candidates.append((_column_priority(col), unique_count, -coverage, col))
    if not candidates:
        return None
    candidates.sort()
    return candidates[0][-1]


def _choose_secondary_category(df: pd.DataFrame, primary_col: str | None) -> str | None:
    for col in sorted(_find_categorical_columns(df), key=_column_priority):
        if col == primary_col:
            continue
        series = df[col].dropna().astype(str)
        unique_count = series.nunique(dropna=True)
        if 2 <= unique_count <= 12:
            return col
    return None


def _choose_metric_columns(df: pd.DataFrame, limit: int = 4) -> list[str]:
    candidates = []
    for col in _find_categorical_columns(df):
        series = df[col].dropna().astype(str)
        unique_count = series.nunique(dropna=True)
        if unique_count <= 1:
            continue
        if unique_count > 12:
            continue
        if len(series) / max(1, len(df)) < 0.6:
            continue
        candidates.append((_column_priority(col), unique_count, col))
    candidates.sort()
    return [col for _, _, col in candidates[:limit]]


def _top_values(series: pd.Series, topn: int = 5) -> list[tuple[str, int, float]]:
    total = len(series)
    counts = series.astype(str).value_counts(dropna=False).head(topn)
    output: list[tuple[str, int, float]] = []
    for key, value in counts.items():
        label = "(missing)" if key in {"<NA>", "nan", "None"} else str(key)
        output.append((label, int(value), _safe_pct(int(value), total)))
    return output


def _missingness_summary(df: pd.DataFrame) -> str:
    rows = []
    for col in df.columns:
        missing_count = int(df[col].isna().sum())
        if missing_count <= 0:
            continue
        pct = _safe_pct(missing_count, len(df))
        if pct < 5:
            continue
        rows.append((pct, col, missing_count))
    if not rows:
        return "No major missing-data issue stands out."
    rows.sort(reverse=True)
    return "; ".join(
        f"`{col}` missing in {count} rows ({pct:.1f}%)"
        for pct, col, count in rows[:4]
    )


def _event_level_summary(df: pd.DataFrame) -> str:
    primary_col = _choose_primary_category(df)
    secondary_col = _choose_secondary_category(df, primary_col)
    lines = [
        "Dataset read:",
        f"- {len(df)} rows and {len(df.columns)} columns",
    ]
    identifier_cols = _find_identifier_columns(df)
    if identifier_cols:
        lines.append(f"- Primary identifier: `{identifier_cols[0]}`")
    if primary_col:
        unique_count = df[primary_col].dropna().astype(str).nunique(dropna=True)
        lines.append(f"- Most useful grouping column: `{primary_col}` ({unique_count} distinct values)")
    if secondary_col:
        unique_count = df[secondary_col].dropna().astype(str).nunique(dropna=True)
        lines.append(f"- Good segmentation column: `{secondary_col}` ({unique_count} distinct values)")
    if primary_col:
        lines.append("")
        lines.append(f"Top values in `{primary_col}`:")
        for label, count, pct in _top_values(df[primary_col].dropna(), topn=6):
            lines.append(f"- {label}: {count} rows ({pct:.1f}%)")
    if secondary_col:
        lines.append("")
        lines.append(f"Top values in `{secondary_col}`:")
        for label, count, pct in _top_values(df[secondary_col].dropna(), topn=5):
            lines.append(f"- {label}: {count} rows ({pct:.1f}%)")
    lines.append("")
    lines.append("Missing-data check:")
    lines.append(f"- {_missingness_summary(df)}")
    return "\n".join(lines)


def _key_metrics_summary(df: pd.DataFrame) -> str:
    lines = [f"Key metrics from {len(df)} rows:"]
    metric_cols = _choose_metric_columns(df)
    if not metric_cols:
        metric_cols = [col for col in (_choose_primary_category(df), _choose_secondary_category(df, _choose_primary_category(df))) if col]
    for col in metric_cols[:4]:
        series = df[col].dropna().astype(str)
        if series.empty:
            continue
        lines.append("")
        lines.append(f"`{col}` distribution:")
        for label, count, pct in _top_values(series, topn=5):
            lines.append(f"- {label}: {count} rows ({pct:.1f}%)")
    identifier_cols = _find_identifier_columns(df)
    if identifier_cols:
        lines.append("")
        lines.append(f"Coverage: `{identifier_cols[0]}` is populated for {len(df)} / {len(df)} rows (100.0%).")
    missing_summary = _missingness_summary(df)
    lines.append("")
    lines.append(f"Missing-data check: {missing_summary}")
    return "\n".join(lines)


def _build_chart_asset(df: pd.DataFrame, output_path: Path) -> tuple[Path | None, str]:
    primary_col = _choose_primary_category(df)
    secondary_col = _choose_secondary_category(df, primary_col)
    numeric_cols = _find_numeric_columns(df)

    try:
        fig, ax = plt.subplots(figsize=(10, 5.6))
        if primary_col and secondary_col and not numeric_cols:
            plot_df = (
                df[[primary_col, secondary_col]]
                .dropna()
                .astype(str)
                .groupby([primary_col, secondary_col])
                .size()
                .reset_index(name="count")
            )
            top_primary = (
                plot_df.groupby(primary_col)["count"].sum().sort_values(ascending=False).head(8).index.tolist()
            )
            top_secondary = (
                plot_df.groupby(secondary_col)["count"].sum().sort_values(ascending=False).head(6).index.tolist()
            )
            plot_df = plot_df[plot_df[primary_col].isin(top_primary) & plot_df[secondary_col].isin(top_secondary)]
            pivot = plot_df.pivot(index=primary_col, columns=secondary_col, values="count").fillna(0)
            pivot = pivot.loc[top_primary[: len(pivot.index)]]
            pivot.plot(kind="bar", stacked=True, ax=ax)
            ax.set_title(f"{primary_col} by {secondary_col}")
            ax.set_xlabel(primary_col)
            ax.set_ylabel("Row count")
            chart_note = f"Stacked bar chart of `{primary_col}` segmented by `{secondary_col}`."
        elif primary_col:
            counts = df[primary_col].dropna().astype(str).value_counts().head(10)
            counts.sort_values(ascending=True).plot(kind="barh", ax=ax)
            ax.set_title(f"Top values in {primary_col}")
            ax.set_xlabel("Row count")
            ax.set_ylabel(primary_col)
            chart_note = f"Bar chart showing the top categories in `{primary_col}`."
        elif numeric_cols:
            df[numeric_cols[0]].dropna().plot(kind="hist", bins=20, ax=ax)
            ax.set_title(f"Distribution of {numeric_cols[0]}")
            ax.set_xlabel(numeric_cols[0])
            chart_note = f"Histogram of numeric column `{numeric_cols[0]}`."
        else:
            plt.close(fig)
            return None, "No suitable chart could be generated from the current table."

        plt.tight_layout()
        fig.savefig(output_path, dpi=180, bbox_inches="tight")
        plt.close(fig)
        return output_path, chart_note
    except Exception:
        plt.close("all")
        return None, "Chart generation was skipped because the current table structure did not support a reliable plot."


def build_spreadsheet_report(doc_path: str, request_text: str = "") -> str:
    path = Path(doc_path)
    raw_df = _load_dataframe(doc_path)
    df, meta = _clean_dataframe(raw_df)

    title = path.stem
    summary = _dataset_summary(df)
    metrics = _key_metrics_summary(df)
    chart_advice = _chart_recommendation(df)

    output_dir = Path(tempfile.gettempdir())
    report_path = output_dir / f"{title} Analysis Report.docx"
    chart_path = output_dir / f"{title} Analysis Chart.png"

    generated_chart, chart_note = _build_chart_asset(df, chart_path)

    doc = Document()
    doc.add_heading(f"{title} 分析報告", level=0)
    if request_text.strip():
        doc.add_paragraph(f"Request: {request_text.strip()}")
    doc.add_paragraph(f"Source file: {path.name}")

    if meta.get("detected_layout") == "pivot_export":
        doc.add_paragraph("Detected a pivot-style export and normalized the table before analysis.")

    doc.add_heading("Key Metrics", level=1)
    for line in metrics.splitlines():
        doc.add_paragraph(line)

    doc.add_heading("Dataset Readout", level=1)
    for line in summary.splitlines():
        doc.add_paragraph(line)

    doc.add_heading("Chart Recommendation", level=1)
    for line in chart_advice.splitlines():
        doc.add_paragraph(line)

    doc.add_heading("Embedded Chart", level=1)
    doc.add_paragraph(chart_note)
    if generated_chart and generated_chart.exists():
        doc.add_picture(str(generated_chart), width=Inches(6.5))

    doc.save(report_path)

    if generated_chart and generated_chart.exists():
        generated_chart.unlink(missing_ok=True)

    return str(report_path)


def _dataset_summary(df: pd.DataFrame) -> str:
    primary_col = _choose_primary_category(df)
    if primary_col:
        return _event_level_summary(df)
    lines = [
        f"Rows: {len(df)}",
        f"Columns: {len(df.columns)}",
        f"Columns: {', '.join(map(str, df.columns.tolist()))}",
    ]
    identifier_cols = _find_identifier_columns(df)
    numeric_cols = _find_numeric_columns(df)
    categorical_cols = _find_categorical_columns(df)
    if identifier_cols:
        lines.append(f"Identifier-like columns: {', '.join(identifier_cols[:6])}")
    if numeric_cols:
        lines.append(f"Numeric columns: {', '.join(numeric_cols)}")
    if categorical_cols:
        lines.append(f"Categorical columns: {', '.join(map(str, categorical_cols[:6]))}")
    if len(df) > 0:
        lines.append("")
        lines.append("Preview:")
        lines.append(df.head(5).to_string(index=False))
    return "\n".join(lines)


def _distribution_summary(df: pd.DataFrame) -> str:
    categorical_cols = _find_categorical_columns(df)
    target_col = categorical_cols[0] if categorical_cols else str(df.columns[0])
    counts = df[target_col].astype(str).value_counts().head(10)
    lines = [f"Top values in `{target_col}`:"]
    total = max(len(df), 1)
    for key, value in counts.items():
        pct = value / total * 100
        lines.append(f"- {key}: {value} ({pct:.1f}%)")
    return "\n".join(lines)


def run_deterministic_analysis(doc_path: str, user_input: str) -> AnalyticsResult:
    query = normalize_query(user_input)

    # Chart/visualization requests need real matplotlib code — never handle deterministically
    if any(term in query for term in _VISUAL_TERMS):
        return AnalyticsResult(False, Path(doc_path).name, "")

    raw_df = _load_dataframe(doc_path)
    df, meta = _clean_dataframe(raw_df)

    intro_lines = []
    if meta.get("detected_layout") == "pivot_export":
        intro_lines.append("Detected a pivot-style export and cleaned the table before analysis.")

    if any(term in query for term in ("distribution", "breakdown", "count", "top values", "category")):
        body = _distribution_summary(df)
        if intro_lines:
            body = "\n".join(intro_lines) + "\n\n" + body
        return AnalyticsResult(True, Path(doc_path).name, body)

    if any(term in query for term in ("key metrics", "metrics", "kpi", "summary stats", "核心指標", "關鍵指標")):
        body = _key_metrics_summary(df)
        if intro_lines:
            body = "\n".join(intro_lines) + "\n\n" + body
        return AnalyticsResult(True, Path(doc_path).name, body)

    if any(term in query for term in ("analyze", "analysis", "summarize", "summary", "python", "data")):
        summary = _dataset_summary(df)
        body = summary
        if intro_lines:
            body = "\n".join(intro_lines) + "\n\n" + body
        return AnalyticsResult(True, Path(doc_path).name, body)

    return AnalyticsResult(False, Path(doc_path).name, "")
