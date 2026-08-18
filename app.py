"""Streamlit UI for the POP Trend Intelligence Tool."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from pop_trend_intelligence.paths import DEFAULT_REPORT_FILE
from pop_trend_intelligence.pipeline.collectors import collect_all
from pop_trend_intelligence.pipeline.discovery import TrendNormalizer
from pop_trend_intelligence.pipeline.scoring import TrendScorer


st.set_page_config(
    page_title="POP Trend Intelligence",
    page_icon="🍵",
    layout="wide",
    initial_sidebar_state="expanded",
)


ACTION_COLORS = {
    "BOTH": "#c96b2c",
    "DEVELOP": "#356859",
    "DISTRIBUTE": "#5e5aa6",
    "PASS": "#8e4b4b",
}

ACTION_LABELS = {
    "BOTH": "Develop + Distribute",
    "DEVELOP": "Develop",
    "DISTRIBUTE": "Distribute",
    "PASS": "Pass",
}

MARKET_STAGE_TONES = {
    "emerging": "Window Opening",
    "growing": "Market Climbing",
    "peaking": "Timing Sensitive",
    "declining": "Window Closing",
}


def inject_styles() -> None:
    """Apply the visual system for the dashboard."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

        :root {
            --paper: #f4ead8;
            --paper-strong: #eadcc7;
            --ink: #1f1a17;
            --muted: #685a4d;
            --ginger: #bb5c2a;
            --ginger-soft: rgba(187, 92, 42, 0.14);
            --jade: #28594d;
            --brass: #9f7b2f;
            --wine: #6f3640;
            --line: rgba(31, 26, 23, 0.12);
            --card-shadow: 0 24px 60px rgba(77, 52, 31, 0.12);
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(201, 107, 44, 0.14), transparent 22%),
                radial-gradient(circle at 90% 10%, rgba(40, 89, 77, 0.12), transparent 18%),
                linear-gradient(180deg, #f7eedf 0%, #f2e6d4 48%, #efe1cf 100%);
            color: var(--ink);
            font-family: "IBM Plex Sans", sans-serif;
        }

        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            opacity: 0.18;
            background-image:
                linear-gradient(rgba(40, 32, 25, 0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(40, 32, 25, 0.035) 1px, transparent 1px);
            background-size: 24px 24px;
            mask-image: linear-gradient(180deg, black, transparent 92%);
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(180deg, rgba(246, 236, 219, 0.98), rgba(238, 225, 204, 0.98));
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] * {
            color: var(--ink) !important;
            font-family: "IBM Plex Sans", sans-serif;
        }

        h1, h2, h3 {
            font-family: "Fraunces", serif !important;
            letter-spacing: -0.03em;
            color: var(--ink);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }

        .hero-shell {
            position: relative;
            overflow: hidden;
            padding: 2rem 2.2rem;
            border: 1px solid rgba(31, 26, 23, 0.12);
            border-radius: 28px;
            background:
                linear-gradient(135deg, rgba(255, 250, 242, 0.92), rgba(240, 226, 203, 0.92));
            box-shadow: var(--card-shadow);
        }

        .hero-shell::after {
            content: "TREND INTELLIGENCE";
            position: absolute;
            right: -1.2rem;
            top: -0.2rem;
            font-family: "IBM Plex Sans", sans-serif;
            font-size: 0.74rem;
            letter-spacing: 0.4em;
            color: rgba(31, 26, 23, 0.10);
            transform: rotate(90deg);
            transform-origin: top right;
        }

        .hero-kicker {
            display: inline-flex;
            align-items: center;
            gap: 0.6rem;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.24em;
            text-transform: uppercase;
            color: var(--jade);
        }

        .hero-title {
            margin: 0.6rem 0 0;
            font-size: clamp(2.6rem, 5vw, 4.8rem);
            line-height: 0.94;
            max-width: 12ch;
        }

        .hero-copy {
            max-width: 52rem;
            margin: 1rem 0 1.3rem;
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.7;
        }

        .hero-ribbon {
            display: inline-block;
            margin-top: 0.25rem;
            padding: 0.58rem 0.9rem;
            border-radius: 999px;
            border: 1px solid rgba(40, 89, 77, 0.18);
            background: rgba(40, 89, 77, 0.08);
            color: var(--jade);
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }

        .metric-row {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 1rem;
            margin-top: 1.6rem;
        }

        .metric-card {
            padding: 1rem 1rem 1.1rem;
            border-radius: 18px;
            border: 1px solid rgba(31, 26, 23, 0.10);
            background: rgba(255, 251, 245, 0.75);
            backdrop-filter: blur(6px);
        }

        .metric-label {
            font-size: 0.77rem;
            text-transform: uppercase;
            letter-spacing: 0.2em;
            color: var(--muted);
        }

        .metric-value {
            margin-top: 0.35rem;
            font-family: "Fraunces", serif;
            font-size: 2rem;
            line-height: 1;
        }

        .metric-note {
            margin-top: 0.5rem;
            font-size: 0.87rem;
            color: var(--muted);
        }

        .section-label {
            margin: 1.8rem 0 0.65rem;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.22em;
            color: var(--wine);
        }

        .spotlight-card, .trend-card {
            border: 1px solid rgba(31, 26, 23, 0.10);
            border-radius: 24px;
            background: rgba(255, 250, 243, 0.88);
            box-shadow: var(--card-shadow);
        }

        .spotlight-card {
            padding: 1.35rem 1.3rem 1.25rem;
            min-height: 235px;
        }

        .spotlight-tag, .trend-tag {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.32rem 0.65rem;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.12em;
        }

        .spotlight-title, .trend-title {
            margin: 0.85rem 0 0.2rem;
            font-family: "Fraunces", serif;
            line-height: 1;
        }

        .spotlight-title {
            font-size: 2rem;
        }

        .trend-title {
            font-size: 1.55rem;
        }

        .spotlight-meta, .trend-meta {
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.6;
        }

        .score-strip {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.8rem;
            margin: 1rem 0 0.8rem;
        }

        .score-big {
            font-family: "Fraunces", serif;
            font-size: 2.3rem;
            line-height: 1;
        }

        .score-caption {
            font-size: 0.78rem;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.18em;
        }

        .pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.85rem;
        }

        .mini-pill {
            padding: 0.33rem 0.6rem;
            border-radius: 999px;
            background: rgba(31, 26, 23, 0.05);
            font-size: 0.76rem;
            color: var(--ink);
        }

        .trend-card {
            padding: 1.1rem 1.1rem 1rem;
            margin-bottom: 1rem;
        }

        .evidence-box {
            margin-top: 0.95rem;
            padding: 0.9rem 0.95rem;
            border-radius: 16px;
            background: rgba(31, 26, 23, 0.045);
            color: var(--muted);
            font-size: 0.9rem;
            line-height: 1.55;
        }

        .ledger-head {
            display: flex;
            align-items: end;
            justify-content: space-between;
            gap: 1rem;
            margin: 1.8rem 0 0.8rem;
        }

        .ledger-title {
            margin: 0;
            font-size: 2rem;
        }

        .ledger-note {
            max-width: 36rem;
            color: var(--muted);
            font-size: 0.94rem;
            line-height: 1.6;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.55rem;
        }

        .stTabs [data-baseweb="tab"] {
            height: 3rem;
            border-radius: 999px;
            padding: 0 1.1rem;
            background: rgba(255, 251, 245, 0.7);
            border: 1px solid rgba(31, 26, 23, 0.1);
            color: var(--ink);
            font-weight: 600;
        }

        .stTabs [aria-selected="true"] {
            background: rgba(187, 92, 42, 0.12) !important;
            border-color: rgba(187, 92, 42, 0.25) !important;
        }

        .stDataFrame, div[data-testid="stDownloadButton"] button {
            border-radius: 16px !important;
        }

        @media (max-width: 1100px) {
            .metric-row {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }

        @media (max-width: 680px) {
            .metric-row {
                grid-template-columns: 1fr;
            }

            .hero-shell {
                padding: 1.5rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def run_pipeline() -> pd.DataFrame:
    """Build the report live from the pipeline."""
    signals = collect_all()
    trends = TrendNormalizer().normalize(signals)
    scored = TrendScorer().score(trends)
    return TrendScorer().export_to_csv(scored, str(DEFAULT_REPORT_FILE))


@st.cache_data(show_spinner=False)
def load_existing_report(path: str) -> pd.DataFrame:
    """Load a saved report from disk."""
    return pd.read_csv(path)


def load_report(refresh: bool) -> tuple[pd.DataFrame, str]:
    """Load the latest trend report."""
    report_path = Path(DEFAULT_REPORT_FILE)
    if refresh:
        return run_pipeline(), "Live pipeline run"
    if report_path.exists():
        return load_existing_report(str(report_path)), "Cached export"
    return run_pipeline(), "Live pipeline run"


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize field types for display."""
    frame = df.copy()
    frame["compliance_ok"] = frame["compliance_ok"].fillna(False).astype(bool)
    for column in [
        "action",
        "category",
        "market_stage",
        "name",
        "primary_source_country",
        "format",
        "compliance_note",
        "top_evidence",
        "pop_line_matches",
        "sources",
        "fda_watch",
    ]:
        frame[column] = frame[column].fillna("")

    numeric_columns = [
        "composite_score",
        "growth_rate_pct",
        "recency_score",
        "competition_density",
        "signal_strength",
        "pop_fit_score",
        "trade_risk_score",
        "avg_gt_interest",
        "source_count",
        "rising_query_count",
        "shelf_life_months",
    ]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)

    frame["compliance_label"] = frame["compliance_ok"].map(
        {True: "Compliant", False: "Blocked"}
    )
    frame["opportunity_mode"] = frame["action"].map(ACTION_LABELS).fillna(frame["action"])
    return frame


def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply sidebar filters."""
    st.sidebar.markdown("## Buyer Controls")

    action_options = sorted(df["action"].dropna().unique().tolist())
    category_options = sorted(df["category"].dropna().unique().tolist())
    stage_options = sorted(df["market_stage"].dropna().unique().tolist())

    selected_actions = st.sidebar.multiselect(
        "Action",
        action_options,
        default=[item for item in action_options if item != "PASS"] or action_options,
    )
    selected_categories = st.sidebar.multiselect(
        "Category",
        category_options,
        default=category_options,
    )
    selected_stages = st.sidebar.multiselect(
        "Market Stage",
        stage_options,
        default=stage_options,
    )
    compliant_only = st.sidebar.toggle("Only show compliant trends", value=True)
    min_score = st.sidebar.slider("Minimum composite score", 0, 100, 20)
    sort_by = st.sidebar.selectbox(
        "Sort by",
        [
            "Composite score",
            "Signal strength",
            "POP-Fit",
            "Growth rate",
            "Recency",
        ],
        index=0,
    )

    filtered = df[
        df["action"].isin(selected_actions)
        & df["category"].isin(selected_categories)
        & df["market_stage"].isin(selected_stages)
        & (df["composite_score"] >= min_score)
    ].copy()

    if compliant_only:
        filtered = filtered[filtered["compliance_ok"]]

    sort_map = {
        "Composite score": "composite_score",
        "Signal strength": "signal_strength",
        "POP-Fit": "pop_fit_score",
        "Growth rate": "growth_rate_pct",
        "Recency": "recency_score",
    }
    filtered = filtered.sort_values(sort_map[sort_by], ascending=False)
    return filtered


def render_hero(df: pd.DataFrame, source_label: str) -> None:
    """Render the hero band and headline metrics."""
    compliant = int(df["compliance_ok"].sum())
    top_actions = df[df["action"].isin(["BOTH", "DEVELOP", "DISTRIBUTE"])]
    avg_score = df["composite_score"].mean() if not df.empty else 0.0
    fastest = df.sort_values("growth_rate_pct", ascending=False).head(1)
    fastest_label = fastest["name"].iloc[0] if not fastest.empty else "No data"

    st.markdown(
        f"""
        <section class="hero-shell">
            <div class="hero-kicker">Prince of Peace Enterprises • Hack the Coast 2026</div>
            <h1 class="hero-title">The buyer's early-window command deck.</h1>
            <p class="hero-copy">
                A trend intelligence room built for POP's buyers: signal first, compliance second,
                action recommendation always visible. This interface is designed to answer one question fast:
                <strong>what should POP move on before the shelf closes?</strong>
            </p>
            <div class="hero-ribbon">Source mode: {source_label}</div>
            <div class="metric-row">
                <div class="metric-card">
                    <div class="metric-label">Qualified Opportunities</div>
                    <div class="metric-value">{len(top_actions)}</div>
                    <div class="metric-note">Trends flagged for develop, distribute, or both.</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Compliant Trends</div>
                    <div class="metric-value">{compliant}</div>
                    <div class="metric-note">Passed shelf life, FDA, and country-risk gates.</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Average Score</div>
                    <div class="metric-value">{avg_score:.1f}</div>
                    <div class="metric-note">Composite blend of signal strength and POP-fit.</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Fastest Climber</div>
                    <div class="metric-value" style="font-size:1.35rem;">{fastest_label}</div>
                    <div class="metric-note">Highest growth velocity in the current slate.</div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def action_tag(action: str) -> str:
    color = ACTION_COLORS.get(action, "#685a4d")
    label = ACTION_LABELS.get(action, action)
    return (
        f"background:{color}1A;color:{color};border:1px solid {color}40;"
        f'" class="trend-tag">{label}</span>'
    )


def render_spotlights(df: pd.DataFrame) -> None:
    """Render three spotlight cards for the highest-value trends."""
    st.markdown('<div class="section-label">Front of Shelf</div>', unsafe_allow_html=True)

    picks = []
    for action in ["BOTH", "DEVELOP", "DISTRIBUTE"]:
        subset = df[df["action"] == action]
        if not subset.empty:
            picks.append(subset.iloc[0])

    if not picks:
        st.info("No trends match the current filters.")
        return

    cols = st.columns(len(picks))
    for column, trend in zip(cols, picks):
        color = ACTION_COLORS.get(trend["action"], "#685a4d")
        tag_style = (
            f'background:{color}1A;color:{color};border:1px solid {color}40;'
        )
        stage_tone = MARKET_STAGE_TONES.get(trend["market_stage"], trend["market_stage"])
        pills = "".join(
            f'<span class="mini-pill">{item}</span>'
            for item in [
                trend["category"],
                f"POP-Fit {trend['pop_fit_score']:.0f}",
                f"Signal {trend['signal_strength']:.0f}",
            ]
        )
        with column:
            st.markdown(
                f"""
                <article class="spotlight-card">
                    <span class="spotlight-tag" style="{tag_style}">{ACTION_LABELS.get(trend["action"], trend["action"])}</span>
                    <h3 class="spotlight-title">{trend["name"]}</h3>
                    <div class="spotlight-meta">{stage_tone} • {trend["primary_source_country"]} • {trend["format"]}</div>
                    <div class="score-strip">
                        <div>
                            <div class="score-caption">Composite Score</div>
                            <div class="score-big">{trend["composite_score"]:.1f}</div>
                        </div>
                        <div style="text-align:right;">
                            <div class="score-caption">Evidence</div>
                            <div style="font-weight:700;">{int(trend["source_count"])} source(s)</div>
                        </div>
                    </div>
                    <div class="pill-row">{pills}</div>
                    <div class="evidence-box">{trend["top_evidence"] or trend["compliance_note"]}</div>
                </article>
                """,
                unsafe_allow_html=True,
            )


def render_trend_card(trend: pd.Series) -> None:
    """Render one trend card in the ledger."""
    color = ACTION_COLORS.get(trend["action"], "#685a4d")
    tag_style = f"background:{color}1A;color:{color};border:1px solid {color}40;"
    compliance_text = "Compliant" if trend["compliance_ok"] else "Blocked"
    line_matches = trend["pop_line_matches"] or "No existing POP adjacency detected"

    pills = [
        f"Growth {trend['growth_rate_pct']:.0f}%",
        f"Recency {trend['recency_score']:.2f}",
        f"Risk {trend['trade_risk_score']:.2f}",
        f"Sources {int(trend['source_count'])}",
        f"Rising queries {int(trend['rising_query_count'])}",
    ]
    pill_markup = "".join(f'<span class="mini-pill">{pill}</span>' for pill in pills)

    st.markdown(
        f"""
        <article class="trend-card">
            <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;">
                <div>
                    <span class="trend-tag" style="{tag_style}">{ACTION_LABELS.get(trend["action"], trend["action"])}</span>
                    <h3 class="trend-title">{trend["name"]}</h3>
                    <div class="trend-meta">{trend["category"]} • {MARKET_STAGE_TONES.get(trend["market_stage"], trend["market_stage"])} • {trend["primary_source_country"]}</div>
                </div>
                <div style="text-align:right; min-width: 7rem;">
                    <div class="score-caption">Composite</div>
                    <div class="score-big" style="font-size:1.9rem;">{trend["composite_score"]:.1f}</div>
                </div>
            </div>
            <div class="pill-row">{pill_markup}</div>
            <div class="evidence-box">
                <strong>POP fit:</strong> {line_matches}<br/>
                <strong>Compliance:</strong> {compliance_text}. {trend["compliance_note"]}<br/>
                <strong>Top evidence:</strong> {trend["top_evidence"] or "No evidence snippet available."}
            </div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    """Return an Excel workbook for download."""
    try:
        import openpyxl  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("Excel export requires openpyxl to be installed.") from exc

    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="POP Trends")
    return buffer.getvalue()


def main() -> None:
    inject_styles()

    st.sidebar.markdown("## Pipeline")
    refresh_requested = st.sidebar.button("Run Live Pipeline", use_container_width=True)
    st.sidebar.caption("Use cached export for speed, or refresh from public sources.")

    report, source_label = load_report(refresh_requested)
    df = clean_dataframe(report)
    filtered = filter_dataframe(df)

    render_hero(df, source_label)
    render_spotlights(filtered)

    tabs = st.tabs(["Trend Ledger", "Buyer Export", "Method"])

    with tabs[0]:
        st.markdown(
            f"""
            <div class="ledger-head">
                <div>
                    <div class="section-label">Decision Ledger</div>
                    <h2 class="ledger-title">What POP should move on now.</h2>
                </div>
                <div class="ledger-note">
                    The ledger keeps action, compliance, and proof in one view so a buyer can scan,
                    defend a recommendation, and move to supplier outreach without losing context.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if filtered.empty:
            st.warning("No trends match the current filter stack.")
        else:
            for _, trend in filtered.iterrows():
                render_trend_card(trend)

    with tabs[1]:
        st.markdown(
            '<div class="section-label">Spreadsheet Ready</div><h2 class="ledger-title">Export for the buying team.</h2>',
            unsafe_allow_html=True,
        )
        buyer_view = filtered[
            [
                "action",
                "composite_score",
                "name",
                "category",
                "market_stage",
                "signal_strength",
                "pop_fit_score",
                "compliance_label",
                "primary_source_country",
                "format",
                "top_evidence",
            ]
        ].rename(
            columns={
                "composite_score": "Composite Score",
                "market_stage": "Market Stage",
                "signal_strength": "Signal Strength",
                "pop_fit_score": "POP-Fit",
                "compliance_label": "Compliance",
                "primary_source_country": "Source Country",
                "top_evidence": "Top Evidence",
            }
        )
        st.dataframe(buyer_view, use_container_width=True, hide_index=True)

        csv_bytes = filtered.to_csv(index=False).encode("utf-8")
        try:
            excel_bytes = to_excel_bytes(filtered)
            excel_error = None
        except RuntimeError as exc:
            excel_bytes = None
            excel_error = str(exc)
        left, right = st.columns(2)
        with left:
            st.download_button(
                "Download CSV",
                data=csv_bytes,
                file_name="pop_trend_report_filtered.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with right:
            if excel_bytes is not None:
                st.download_button(
                    "Download Excel",
                    data=excel_bytes,
                    file_name="pop_trend_report_filtered.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            else:
                st.button("Download Excel", disabled=True, use_container_width=True)
                st.caption(excel_error)

    with tabs[2]:
        st.markdown(
            """
            <div class="section-label">How To Read This</div>
            <h2 class="ledger-title">Designed for POP's buyer workflow.</h2>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            - `BOTH` means the trend is strong enough to pursue as a distributed product and close enough to POP's current lines to inspire an owned product.
            - `DEVELOP` favors adjacency to POP's ginger, ginseng, and tea strengths even if the shelf is still lightly proven.
            - `DISTRIBUTE` favors market pull and shelf readiness even when POP-fit is low.
            - `PASS` keeps blocked or late-stage opportunities visible so buyers can explain why they were rejected.
            - Compliance is always shown alongside opportunity because POP's real bottleneck is not spotting trends, it is acting on the right ones early enough.
            """
        )


if __name__ == "__main__":
    main()
