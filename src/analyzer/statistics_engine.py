"""과년도 기출 구조화 JSON을 Python으로 통계 분석합니다."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from config.config import CONFIG


class StatisticsEngine:
    """LLM 없이 pandas/Counter 기반으로 기출 통계를 계산합니다."""

    def __init__(self, chart_dir: Path | None = None) -> None:
        """그래프 저장 경로를 초기화합니다."""
        self.chart_dir = chart_dir or CONFIG.exam_index_dir / "charts"

    def analyze(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        """구조화 기출 레코드의 통계를 계산합니다."""
        pd = self._pandas()
        df = pd.DataFrame(records)
        if df.empty:
            return self._empty_result()

        for column in ("year", "round", "subject", "category", "subcategory", "question_type", "difficulty", "language"):
            if column not in df.columns:
                df[column] = ""
        df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
        df["round"] = pd.to_numeric(df["round"], errors="coerce").fillna(0).astype(int)

        recent3 = self._recent_year_df(df, 3)
        recent5 = self._recent_year_df(df, 5)
        older3 = df[~df.index.isin(recent3.index)]
        older5 = df[~df.index.isin(recent5.index)]

        return {
            "total_count": int(len(df)),
            "subject_counts": self._value_counts(df, "subject"),
            "category_counts": self._value_counts(df, "category"),
            "category_ratios": self._ratios(df, "category"),
            "subcategory_counts": self._value_counts(df, "subcategory"),
            "subcategory_ratios": self._ratios(df, "subcategory"),
            "primary_counts": self._value_counts(df, "primary") if "primary" in df.columns else self._value_counts(df, "subcategory"),
            "secondary_counts": self._list_value_counts(df, "secondary"),
            "intent_counts": self._list_value_counts(df, "intent"),
            "mistakes_counts": self._list_value_counts(df, "mistakes"),
            "language_counts": self._value_counts(df[df["language"].isin(["C", "Java", "Python", "SQL"])], "language"),
            "sql_type_counts": self._value_counts(df[df["category"].eq("SQL") | df["subject"].eq("SQL 응용")], "subcategory"),
            "yearly_subject": self._pivot(df, "year", "subject"),
            "round_subject": self._pivot(df, "round", "subject"),
            "yearly_subcategory": self._pivot(df, "year", "subcategory"),
            "recent3_change": self._change(recent3, older3, "subcategory"),
            "recent5_change": self._change(recent5, older5, "subcategory"),
            "recent3_decrease": self._decrease(recent3, older3, "subcategory"),
            "recent5_decrease": self._decrease(recent5, older5, "subcategory"),
        }

    def format_report(self, analysis: dict[str, Any]) -> str:
        """통계 분석 결과를 GUI 출력용 문자열로 변환합니다."""
        return "\n".join(
            [
                f"분석 문제 수: {analysis['total_count']}",
                "\n① 과목별 빈도",
                self._format_counter(analysis["subject_counts"]),
                "\n② 카테고리별 빈도",
                self._format_counter(analysis["category_counts"]),
                "\n③ 세부유형별 빈도",
                self._format_counter(analysis["subcategory_counts"]),
                "\n③-1 Primary 개념별 빈도",
                self._format_counter(analysis["primary_counts"]),
                "\n③-2 Secondary 개념별 빈도",
                self._format_counter(analysis["secondary_counts"]),
                "\n④ 코드 언어별 출제 횟수",
                self._format_counter(analysis["language_counts"]),
                "\n⑤ SQL 유형별 출제 횟수",
                self._format_counter(analysis["sql_type_counts"]),
                "\n⑥ 출제 의도별 빈도",
                self._format_counter(analysis["intent_counts"]),
                "\n⑦ 자주 틀리는 포인트별 빈도",
                self._format_counter(analysis["mistakes_counts"]),
                "\n⑧ 최근 3개년 증가",
                self._format_counter(analysis["recent3_change"]),
                "\n⑨ 최근 3개년 감소",
                self._format_counter(analysis["recent3_decrease"]),
                "\n⑩ 최근 5개년 증가",
                self._format_counter(analysis["recent5_change"]),
                "\n⑪ 최근 5개년 감소",
                self._format_counter(analysis["recent5_decrease"]),
            ]
        )

    def generate_charts(self, analysis: dict[str, Any]) -> list[Path]:
        """통계 그래프 PNG 파일을 생성합니다."""
        plt = self._matplotlib()
        self.chart_dir.mkdir(parents=True, exist_ok=True)
        chart_specs = [
            ("subject_counts", "과목별 출제횟수", "subject_counts.png", "bar"),
            ("recent3_change", "최근 증가 유형", "recent3_change.png", "bar"),
            ("language_counts", "코드언어 출제비율", "language_counts.png", "pie"),
            ("sql_type_counts", "SQL 유형 비율", "sql_type_counts.png", "pie"),
        ]
        paths: list[Path] = []
        for key, title, filename, kind in chart_specs:
            counter = analysis.get(key, Counter())
            if not counter:
                continue
            labels, values = zip(*counter.most_common(10), strict=False)
            fig, ax = plt.subplots(figsize=(8, 4.5))
            if kind == "pie":
                ax.pie(values, labels=labels, autopct="%1.1f%%")
            else:
                ax.bar(labels, values)
                ax.tick_params(axis="x", labelrotation=35)
            ax.set_title(title)
            fig.tight_layout()
            path = self.chart_dir / filename
            fig.savefig(path)
            plt.close(fig)
            paths.append(path)
        heatmap_path = self._subcategory_heatmap(analysis, plt)
        if heatmap_path:
            paths.append(heatmap_path)
        return paths

    def _subcategory_heatmap(self, analysis: dict[str, Any], plt) -> Path | None:
        """연도별 세부유형 히트맵을 생성합니다."""
        yearly = analysis.get("yearly_subcategory", {})
        if not yearly:
            return None
        top_subcategories = [name for name, _ in analysis.get("subcategory_counts", Counter()).most_common(12)]
        years = sorted(yearly.keys())
        if not years or not top_subcategories:
            return None
        matrix = [
            [int(yearly.get(year, {}).get(subcategory, 0)) for subcategory in top_subcategories]
            for year in years
        ]
        fig, ax = plt.subplots(figsize=(10, max(4, len(years) * 0.5)))
        image = ax.imshow(matrix, aspect="auto", cmap="YlOrRd")
        ax.set_xticks(range(len(top_subcategories)), labels=top_subcategories, rotation=35, ha="right")
        ax.set_yticks(range(len(years)), labels=years)
        ax.set_title("연도별 세부유형 히트맵")
        fig.colorbar(image, ax=ax)
        fig.tight_layout()
        path = self.chart_dir / "subcategory_year_heatmap.png"
        fig.savefig(path)
        plt.close(fig)
        return path

    def _recent_year_df(self, df, years: int):
        year_values = sorted([year for year in df["year"].unique() if year], reverse=True)
        return df[df["year"].isin(set(year_values[:years]))]

    def _value_counts(self, df, column: str) -> Counter:
        return Counter({str(key): int(value) for key, value in df[column].dropna().value_counts().items() if str(key)})

    def _ratios(self, df, column: str) -> dict[str, float]:
        counts = self._value_counts(df, column)
        total = sum(counts.values())
        if not total:
            return {}
        return {key: round(value / total * 100, 2) for key, value in counts.items()}

    def _list_value_counts(self, df, column: str) -> Counter:
        counter: Counter = Counter()
        if column not in df.columns:
            return counter
        for value in df[column].dropna():
            if isinstance(value, list):
                items = value
            else:
                items = [item.strip() for item in str(value).split(",")]
            counter.update(str(item).strip() for item in items if str(item).strip())
        return counter

    def _pivot(self, df, index: str, columns: str) -> dict[str, dict[str, int]]:
        table = df.pivot_table(index=index, columns=columns, values="question_number", aggfunc="count", fill_value=0)
        return {
            str(row): {str(col): int(value) for col, value in values.items() if int(value)}
            for row, values in table.to_dict(orient="index").items()
        }

    def _change(self, recent, older, column: str) -> Counter:
        recent_counts = Counter(recent[column].dropna())
        older_counts = Counter(older[column].dropna())
        return Counter({key: recent_counts[key] - older_counts.get(key, 0) for key in recent_counts if recent_counts[key] - older_counts.get(key, 0) > 0})

    def _decrease(self, recent, older, column: str) -> Counter:
        recent_counts = Counter(recent[column].dropna())
        older_counts = Counter(older[column].dropna())
        return Counter({key: older_counts[key] - recent_counts.get(key, 0) for key in older_counts if older_counts[key] - recent_counts.get(key, 0) > 0})

    def _format_counter(self, counter: Counter) -> str:
        if not counter:
            return "- 데이터 없음"
        return "\n".join(f"- {key}: {value}" for key, value in counter.most_common(20))

    def _empty_result(self) -> dict[str, Any]:
        empty = Counter()
        return {
            "total_count": 0,
            "subject_counts": empty,
            "category_counts": empty,
            "category_ratios": {},
            "subcategory_counts": empty,
            "subcategory_ratios": {},
            "primary_counts": empty,
            "secondary_counts": empty,
            "intent_counts": empty,
            "mistakes_counts": empty,
            "language_counts": empty,
            "sql_type_counts": empty,
            "yearly_subject": {},
            "round_subject": {},
            "yearly_subcategory": {},
            "recent3_change": empty,
            "recent5_change": empty,
            "recent3_decrease": empty,
            "recent5_decrease": empty,
        }

    def _pandas(self):
        try:
            import pandas as pd
        except ImportError as exc:
            raise RuntimeError("pandas가 필요합니다. requirements.txt를 설치하세요.") from exc
        return pd

    def _matplotlib(self):
        try:
            import os
            import tempfile

            os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "studyrag_matplotlib"))
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError as exc:
            raise RuntimeError("matplotlib이 필요합니다. requirements.txt를 설치하세요.") from exc
        return plt
