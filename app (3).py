
%%writefile app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Scientific Visualisation Dashboard",
    layout="wide"
)

st.title("📈 Scientific Visualisation Assignment")
st.subheader(
    "Income, Marriages, and Prison Statistics in Malaysia (2020–2024)"
)

# --------------------------------------------------
# 2. LOAD AND PROCESS DATA
# --------------------------------------------------

@st.cache_data
def load_data():

    income_df = pd.read_csv("income.csv")
    marriages_df = pd.read_csv("marriages_age.csv")
    crime_df = pd.read_csv("crime.csv")

    # Convert date and extract year
    for df in [income_df, marriages_df, crime_df]:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["year"] = df["date"].dt.year

    # Filter data from 2020 to 2024
    income_df = income_df[
        income_df["year"].between(2020, 2024)
    ].copy()

    marriages_df = marriages_df[
        marriages_df["year"].between(2020, 2024)
    ].copy()

    crime_df = crime_df[
        crime_df["year"].between(2020, 2024)
    ].copy()

    # Convert numerical columns
    income_df["income"] = pd.to_numeric(
        income_df["income"].replace("?", pd.NA),
        errors="coerce"
    )

    marriages_df["abs"] = pd.to_numeric(
        marriages_df["abs"], errors="coerce"
    )

    crime_df["prisoners"] = pd.to_numeric(
        crime_df["prisoners"], errors="coerce"
    )

    # Clean text columns
    for df in [income_df, marriages_df, crime_df]:
        for col in ["state", "sex", "age", "variable"]:
            if col in df.columns:
                df[col] = (
                    df[col].astype("string").str.strip()
                )

    # --------------------------------------------------
    # NATIONAL LEVEL AGGREGATION
    # --------------------------------------------------

    # Average income
    income_yearly = (
        income_df[income_df["variable"].str.lower() == "mean"]
        .groupby("year")["income"]
        .mean()
        .reset_index(name="avg_income")
    )

    # Total marriages
    marriages_yearly = (
        marriages_df[
            marriages_df["age"].str.lower() == "all"
        ]
        .groupby("year")["abs"]
        .sum(min_count=1)
        .reset_index(name="total_marriages")
    )

    # Total prisoners
    crime_yearly = (
        crime_df[
            (crime_df["state"].str.lower() == "malaysia") &
            (crime_df["sex"].str.lower() == "both")
        ]
        .groupby("year")["prisoners"]
        .sum(min_count=1)
        .reset_index(name="total_prisoners")
    )

    # Merge yearly datasets
    merged_yearly = income_yearly.merge(
        marriages_yearly, on="year", how="outer"
    )

    merged_yearly = merged_yearly.merge(
        crime_yearly, on="year", how="outer"
    )

    merged_yearly = (
        merged_yearly.sort_values("year").reset_index(drop=True)
    )

    return merged_yearly

try:
    merged_yearly_df = load_data()

except Exception as e:
    st.error(f"Error loading datasets: {e}")
    st.stop()

# --------------------------------------------------
# 3. YEAR SELECTOR
# --------------------------------------------------

all_years = sorted(
    merged_yearly_df["year"].dropna().astype(int).unique()
)

if not all_years:
    st.error("No data available for the selected period.")
    st.stop()

selected_year = st.sidebar.selectbox(
    "Select Year for Summary Metrics",
    all_years,
    index=len(all_years) - 1
)

year_data = merged_yearly_df[
    merged_yearly_df["year"] == selected_year
]

previous_data = merged_yearly_df[
    merged_yearly_df["year"] == selected_year - 1
]

def get_value(data, column):
    if data.empty:
        return None

    value = data[column].iloc[0]

    if pd.isna(value):
        return None

    return float(value)

def calculate_percentage_change(current, previous):

    if current is None or previous is None or previous == 0:
        return None

    return ((current - previous) / abs(previous)) * 100

def format_number(value, prefix="", suffix="", decimals=0):

    if value is None:
        return "N/A"

    return (
        f"{prefix}{value:,.{decimals}f}{suffix}"
    )

# Selected year values
avg_income = get_value(year_data, "avg_income")
total_marriages = get_value(year_data, "total_marriages")
total_prisoners = get_value(year_data, "total_prisoners")

# Previous year values
previous_income = get_value(previous_data, "avg_income")
previous_marriages = get_value(
    previous_data, "total_marriages"
)

# Percentage changes
income_change = calculate_percentage_change(
    avg_income, previous_income
)

marriage_change = calculate_percentage_change(
    total_marriages, previous_marriages
)

# --------------------------------------------------
# 4. CORRELATION ANALYSIS
# --------------------------------------------------

correlation_data = merged_yearly_df[
    ["avg_income", "total_marriages"]
].dropna()

if len(correlation_data) >= 2:
    correlation_value = correlation_data[
        "avg_income"
    ].corr(correlation_data["total_marriages"])
else:
    correlation_value = None

# --------------------------------------------------
# 5. CREATE THREE TABS
# --------------------------------------------------

tab1, tab2, tab3 = st.tabs([
    "Income vs Prisoners",
    "Marriages vs Prisoners",
    "Income vs Marriages"
])

# ==================================================
# TAB 1: LINE CHART
# ==================================================

with tab1:

    st.header("1. National Average Income vs Total Prisoners")

    st.markdown("### 📊 Summary Metrics")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label=f"Average Income ({selected_year})",
            value=format_number(
                avg_income, prefix="RM ", decimals=2
            )
        )

    with col2:
        st.metric(
            label=f"Total Prisoners ({selected_year})",
            value=format_number(total_prisoners)
        )

    with col3:
        st.metric(
            label="Income Change (%)",
            value=format_number(
                income_change, suffix="%", decimals=2
            ),
            delta=(
                f"{income_change:+.2f}%"
                if income_change is not None else None
            )
        )

    st.caption(
        "Income change compares the selected year with the previous year."
    )

    st.divider()

    # Line chart data
    plot_yearly = merged_yearly_df.dropna(
        subset=["avg_income", "total_prisoners"]
    ).sort_values("year")

    fig_line = make_subplots(
        specs=[[{"secondary_y": True}]]
    )

    fig_line.add_trace(
        go.Scatter(
            x=plot_yearly["year"],
            y=plot_yearly["avg_income"],
            name="Average Income (RM)",
            mode="lines+markers",
            line=dict(color="blue", width=3)
        ),
        secondary_y=False
    )

    fig_line.add_trace(
        go.Scatter(
            x=plot_yearly["year"],
            y=plot_yearly["total_prisoners"],
            name="Total Prisoners",
            mode="lines+markers",
            line=dict(color="red", width=3)
        ),
        secondary_y=True
    )

    fig_line.update_layout(
        xaxis_title="Year",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(x=0.01, y=0.99)
    )

    fig_line.update_yaxes(
        title_text="Average Income (RM)",
        secondary_y=False,
        color="blue"
    )

    fig_line.update_yaxes(
        title_text="Total Prisoners",
        secondary_y=True,
        color="red"
    )

    st.plotly_chart(
        fig_line,
        use_container_width=True
    )

# ==================================================
# TAB 2: BAR CHART
# ==================================================

with tab2:

    st.header("2. National Yearly Marriages vs Total Prisoners")

    st.markdown("### 📊 Summary Metrics")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label=f"Total Marriages ({selected_year})",
            value=format_number(total_marriages)
        )

    with col2:
        st.metric(
            label=f"Total Prisoners ({selected_year})",
            value=format_number(total_prisoners)
        )

    with col3:
        st.metric(
            label="Marriage Change (%)",
            value=format_number(
                marriage_change, suffix="%", decimals=2
            ),
            delta=(
                f"{marriage_change:+.2f}%"
                if marriage_change is not None else None
            )
        )

    st.caption(
        "Marriage change compares the selected year with the previous year."
    )

    st.divider()

    # Bar chart
    plot_bar = merged_yearly_df.sort_values("year")

    fig_bar = make_subplots(
        specs=[[{"secondary_y": True}]]
    )

    fig_bar.add_trace(
        go.Bar(
            x=plot_bar["year"],
            y=plot_bar["total_marriages"],
            name="Total Marriages",
            marker_color="rgb(158,202,225)"
        ),
        secondary_y=False
    )

    fig_bar.add_trace(
        go.Bar(
            x=plot_bar["year"],
            y=plot_bar["total_prisoners"],
            name="Total Prisoners",
            marker_color="rgb(227,119,194)"
        ),
        secondary_y=True
    )

    fig_bar.update_layout(
        xaxis_title="Year",
        barmode="group",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(x=0.01, y=0.99)
    )

    fig_bar.update_yaxes(
        title_text="Total Marriages",
        secondary_y=False
    )

    fig_bar.update_yaxes(
        title_text="Total Prisoners",
        secondary_y=True
    )

    st.plotly_chart(
        fig_bar,
        use_container_width=True
    )

# ==================================================
# TAB 3: HEATMAP
# ==================================================

with tab3:

    st.header("3. Correlation Heatmap: Income vs Marriages")

    st.markdown("### 📊 Summary Metrics")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label=f"Average Income ({selected_year})",
            value=format_number(
                avg_income, prefix="RM ", decimals=2
            )
        )

    with col2:
        st.metric(
            label=f"Total Marriages ({selected_year})",
            value=format_number(total_marriages)
        )

    with col3:
        st.metric(
            label="Correlation Coefficient",
            value=format_number(
                correlation_value, decimals=3
            )
        )

    st.caption(
        "Correlation is calculated using the available annual "
        "income and marriage observations from 2020 to 2024."
    )

    st.divider()

    # Correlation heatmap
    if len(correlation_data) >= 2:

        corr_matrix = correlation_data.corr()

        fig_heatmap = px.imshow(
            corr_matrix,
            text_auto=".3f",
            aspect="auto",
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
            labels=dict(color="Correlation Coefficient"),
            x=["Average Income", "Total Marriages"],
            y=["Average Income", "Total Marriages"]
        )

        fig_heatmap.update_layout(
            template="plotly_white",
            title="Correlation between Income and Marriages"
        )

        st.plotly_chart(
            fig_heatmap,
            use_container_width=True
        )

    else:
        st.warning(
            "Not enough matching yearly observations "
            "to calculate correlation."
        )

# --------------------------------------------------
# 6. FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "Data Source: Department of Statistics Malaysia (DOSM) "
    "and Malaysia Open Data."
)

st.caption(
    "Scientific Visualisation Assignment | 2020–2024"
)
