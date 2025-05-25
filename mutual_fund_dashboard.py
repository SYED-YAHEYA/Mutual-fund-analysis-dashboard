import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# Set page configuration
st.set_page_config(page_title="Mutual Fund Analysis Dashboard", layout="wide")

# Title
st.title("Mutual Fund Analysis Dashboard")

# Load data from Excel with the correct sheet names
try:
    sheet1 = pd.read_excel("cleaned_data.xlsx", sheet_name="Fund_Data")
    sheet2 = pd.read_excel("cleaned_data.xlsx", sheet_name="Historical_NAV")
    sheet3 = pd.read_excel("cleaned_data.xlsx", sheet_name="Top_Holdings")
except FileNotFoundError:
    st.error("Error: 'cleaned_data.xlsx' not found. Please ensure the file is in the same directory as this script.")
    st.stop()
except ValueError as ve:
    st.error(f"Error: {str(ve)}. Please check the sheet names in 'cleaned_data.xlsx' and update the script accordingly.")
    excel_file = pd.ExcelFile("cleaned_data.xlsx")
    st.write("Available sheet names in the Excel file:", excel_file.sheet_names)
    st.stop()
except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.stop()

# Clean and process Sheet1 (Fund_Data)
sheet1 = sheet1.dropna(subset=["name", "aum", "nav"])
sheet1["aum"] = pd.to_numeric(sheet1["aum"], errors="coerce").fillna(0)
sheet1["nav"] = pd.to_numeric(sheet1["nav"], errors="coerce").fillna(0)
sheet1["rating"] = pd.to_numeric(sheet1["rating"], errors="coerce").fillna(0)
sheet1["minimum_investment"] = pd.to_numeric(sheet1["minimum_investment"], errors="coerce").fillna(0)
sheet1["minimum_sip_investment"] = pd.to_numeric(sheet1["minimum_sip_investment"], errors="coerce").fillna(0)
sheet1["debt_per"] = pd.to_numeric(sheet1["debt_per"], errors="coerce").fillna(0)
sheet1["equity_per"] = pd.to_numeric(sheet1["equity_per"], errors="coerce").fillna(0)
sheet1["equity_aum"] = pd.to_numeric(sheet1["equity_aum"], errors="coerce").fillna(0)
sheet1["asset_equity"] = pd.to_numeric(sheet1["asset_equity"], errors="coerce").fillna(0)
sheet1["asset_debt"] = pd.to_numeric(sheet1["asset_debt"], errors="coerce").fillna(0)
sheet1["asset_cash"] = pd.to_numeric(sheet1["asset_cash"], errors="coerce").fillna(0)
sheet1["risk"] = sheet1["risk"].fillna("Unknown")
sheet1["type"] = sheet1["type"].fillna("Unknown")
sheet1["one_year_return"] = pd.to_numeric(sheet1["one_year_return"], errors="coerce").fillna(0)
sheet1["three_year_return"] = pd.to_numeric(sheet1["three_year_return"], errors="coerce").fillna(0)
sheet1["five_year_return"] = pd.to_numeric(sheet1["five_year_return"], errors="coerce").fillna(0)
sheet1["exit_load"] = pd.to_numeric(sheet1["exit_load"], errors="coerce").fillna(0)
sheet1["pe"] = pd.to_numeric(sheet1["pe"], errors="coerce").fillna(0)
sheet1["pb"] = pd.to_numeric(sheet1["pb"], errors="coerce").fillna(0)
sheet1["average_maturity"] = pd.to_numeric(sheet1["average_maturity"], errors="coerce").fillna(0)
sheet1["yield_to_maturity"] = pd.to_numeric(sheet1["yield_to_maturity"], errors="coerce").fillna(0)

# Rename columns for consistency
sheet1 = sheet1.rename(columns={
    "name": "fund_name",
    "aum": "aum_funds_individual_lst",
    "nav": "nav_funds_individual_lst",
    "rating": "rating_of_funds_individual_lst",
    "minimum_investment": "minimum_funds_individual_lst",
    "minimum_sip_investment": "minimum_sip_funds_individual_lst",
    "debt_per": "debt_per",
    "equity_per": "equity_per",
    "equity_aum": "equity_aum",
    "asset_equity": "asset_equity",
    "asset_debt": "asset_debt",
    "asset_cash": "asset_cash",
    "risk": "risk_of_the_fund",
    "type": "type_of_fund",
    "one_year_return": "one_year_returns",
    "three_year_return": "three_year_returns",
    "five_year_return": "five_year_returns",
    "historical_nav_summary": "historical_nav_summary",
    "top_holdings_summary": "top_holdings_summary",
    "asset_allocation_summary": "asset_allocation_summary",
    "sector_allocation_summary": "sector_allocation_summary"
})

# Clean and process Sheet2 (Historical_NAV)
try:
    sheet2 = sheet2.dropna(subset=["fund_name", "date", "nav"])
    sheet2["date"] = pd.to_datetime(sheet2["date"], format="%d-%m-%Y %H:%M:%S", errors="coerce")
    sheet2 = sheet2.dropna(subset=["date"])
    sheet2["nav"] = pd.to_numeric(sheet2["nav"], errors="coerce").fillna(0)
except KeyError as ke:
    st.error(f"Error: {str(ke)}. Please check the column names in 'Historical_NAV' sheet and update the script.")
    st.write("Columns in Historical_NAV sheet:", sheet2.columns.tolist())
    st.stop()

# Clean and process Sheet3 (Top_Holdings)
try:
    sheet3 = sheet3.dropna(subset=["fund_name", "company", "percentage"])
    sheet3["percentage"] = pd.to_numeric(sheet3["percentage"], errors="coerce").fillna(0)
except KeyError as ke:
    st.error(f"Error: {str(ke)}. Please check the column names in 'Top_Holdings' sheet and update the script.")
    st.write("Columns in Top_Holdings sheet:", sheet3.columns.tolist())
    st.stop()

# Sidebar for Filtering
st.sidebar.header("Filter Funds")
type_filter = st.sidebar.multiselect("Fund Type", options=sheet1["type_of_fund"].unique(), default=sheet1["type_of_fund"].unique())
risk_filter = st.sidebar.multiselect("Risk Level", options=sheet1["risk_of_the_fund"].unique(), default=sheet1["risk_of_the_fund"].unique())
min_investment_range = st.sidebar.slider("Minimum Investment (₹)", 
                                         min_value=float(sheet1["minimum_funds_individual_lst"].min()), 
                                         max_value=float(sheet1["minimum_funds_individual_lst"].max()), 
                                         value=(float(sheet1["minimum_funds_individual_lst"].min()), float(sheet1["minimum_funds_individual_lst"].max())))
min_sip_range = st.sidebar.slider("Minimum SIP Investment (₹)", 
                                  min_value=float(sheet1["minimum_sip_funds_individual_lst"].min()), 
                                  max_value=float(sheet1["minimum_sip_funds_individual_lst"].max()), 
                                  value=(float(sheet1["minimum_sip_funds_individual_lst"].min()), float(sheet1["minimum_sip_funds_individual_lst"].max())))

# Apply filters
filtered_data = sheet1[
    (sheet1["type_of_fund"].isin(type_filter)) &
    (sheet1["risk_of_the_fund"].isin(risk_filter)) &
    (sheet1["minimum_funds_individual_lst"] >= min_investment_range[0]) &
    (sheet1["minimum_funds_individual_lst"] <= min_investment_range[1]) &
    (sheet1["minimum_sip_funds_individual_lst"] >= min_sip_range[0]) &
    (sheet1["minimum_sip_funds_individual_lst"] <= min_sip_range[1])
]

# Summary Metrics
st.header("Summary Metrics")
col1, col2, col3, col4 = st.columns(4)
with col1:
    avg_5yr_returns = filtered_data["five_year_returns"].mean()
    st.metric("Average 5-Year Returns", f"{avg_5yr_returns:.2f}%")
with col2:
    total_aum = filtered_data["aum_funds_individual_lst"].sum() / 1000
    st.metric("Total AUM", f"{total_aum:.2f}K Cr")
with col3:
    avg_rating = filtered_data[filtered_data["rating_of_funds_individual_lst"] > 0]["rating_of_funds_individual_lst"].mean()
    st.metric("Average Rating", f"{avg_rating:.1f}")
with col4:
    avg_equity_aum = filtered_data["equity_aum"].sum() / 1000
    st.metric("Total Equity AUM", f"{avg_equity_aum:.2f}K Cr")

# Interesting Fact
st.header("Interesting Fact")
if not filtered_data.empty:
    top_fund = filtered_data.loc[filtered_data["five_year_returns"].idxmax()]
    st.write(
        f"The fund with the highest 5-year returns ({top_fund['five_year_returns']:.2f}%) is "
        f"{top_fund['fund_name']}, a {top_fund['type_of_fund']} fund with a {top_fund['risk_of_the_fund']} "
        "risk level, showcasing exceptional performance despite its risk profile."
    )
else:
    st.write("No funds match the selected filters.")

# Fund Comparison Table
st.header("Fund Comparison Table")
comparison_columns = ["fund_name", "type_of_fund", "risk_of_the_fund", "aum_funds_individual_lst", "nav_funds_individual_lst",
                      "one_year_returns", "three_year_returns", "five_year_returns", "pe", "pb", "exit_load", 
                      "minimum_funds_individual_lst", "minimum_sip_funds_individual_lst", "equity_aum"]
st.dataframe(filtered_data[comparison_columns].style.format({
    "aum_funds_individual_lst": "{:.2f}",
    "nav_funds_individual_lst": "{:.2f}",
    "one_year_returns": "{:.2f}",
    "three_year_returns": "{:.2f}",
    "five_year_returns": "{:.2f}",
    "pe": "{:.2f}",
    "pb": "{:.2f}",
    "exit_load": "{:.2f}",
    "minimum_funds_individual_lst": "{:.2f}",
    "minimum_sip_funds_individual_lst": "{:.2f}",
    "equity_aum": "{:.2f}"
}))

# Export Filtered Data
st.header("Export Filtered Data")
csv = filtered_data[comparison_columns].to_csv(index=False)
st.download_button(label="Download Filtered Data as CSV", data=csv, file_name="filtered_funds.csv", mime="text/csv")

# Returns Comparison by Fund Type
st.header("Returns Comparison by Fund Type")
returns_by_type = filtered_data.groupby("type_of_fund").agg({
    "one_year_returns": "mean",
    "three_year_returns": "mean",
    "five_year_returns": "mean"
}).reset_index()
returns_melted = returns_by_type.melt(id_vars="type_of_fund", 
                                      value_vars=["one_year_returns", "three_year_returns", "five_year_returns"],
                                      var_name="Return Period", value_name="Returns (%)")
fig_returns = px.bar(returns_melted, x="type_of_fund", y="Returns (%)", color="Return Period",
                     title="Returns Comparison by Fund Type",
                     labels={"type_of_fund": "Fund Type", "Returns (%)": "Returns (%)"},
                     barmode="group",
                     color_discrete_sequence=px.colors.sequential.Plasma)
fig_returns.update_layout(legend_title_text="Return Period", height=600)
st.plotly_chart(fig_returns, use_container_width=True)

# Returns Heatmap Across Funds
st.header("Returns Heatmap Across Funds")
returns_heatmap_data = filtered_data[["fund_name", "one_year_returns", "three_year_returns", "five_year_returns"]]
returns_heatmap_melted = returns_heatmap_data.melt(id_vars="fund_name", 
                                                    value_vars=["one_year_returns", "three_year_returns", "five_year_returns"],
                                                    var_name="Return Period", value_name="Returns (%)")

# Create the heatmap with marginal histograms using go.Figure
fig_heatmap = go.Figure()

# Create the heatmap
heatmap_data = returns_heatmap_melted.pivot(index="Return Period", columns="fund_name", values="Returns (%)")
fig_heatmap.add_trace(
    go.Heatmap(
        x=heatmap_data.columns,
        y=heatmap_data.index,
        z=heatmap_data.values,
        colorscale="RdBu",
        colorbar=dict(
            title=dict(text="Returns (%)", side="right")
        ),
        hovertemplate="Fund: %{x}<br>Return Period: %{y}<br>Returns: %{z:.2f}%<extra></extra>"
    )
)

# Add marginal histogram for x-axis (fund names)
for period in returns_heatmap_melted["Return Period"].unique():
    period_data = returns_heatmap_melted[returns_heatmap_melted["Return Period"] == period]["Returns (%)"]
    fig_heatmap.add_trace(
        go.Histogram(
            y=period_data,
            xaxis="x",
            yaxis="y2",
            marker=dict(color="skyblue"),
            showlegend=False,
            opacity=0.7
        )
    )

# Add marginal histogram for y-axis (return periods)
for fund in returns_heatmap_melted["fund_name"].unique():
    fund_data = returns_heatmap_melted[returns_heatmap_melted["fund_name"] == fund]["Returns (%)"]
    fig_heatmap.add_trace(
        go.Histogram(
            x=fund_data,
            xaxis="x2",
            yaxis="y",
            marker=dict(color="lightcoral"),
            showlegend=False,
            opacity=0.7
        )
    )

# Update layout for subplots with marginal histograms
fig_heatmap.update_layout(
    title="Returns Heatmap Across Funds",
    xaxis=dict(
        domain=[0, 0.9],
        title="Fund Name",
        title_font_size=12,
        tickfont=dict(size=10),
        tickangle=90
    ),
    yaxis=dict(
        domain=[0, 0.9],
        title="Return Period",
        title_font_size=12,
        tickfont=dict(size=10)
    ),
    xaxis2=dict(
        domain=[0.9, 1],
        showticklabels=False
    ),
    yaxis2=dict(
        domain=[0.9, 1],
        showticklabels=False
    ),
    height=800,
    width=1200,
    title_font_size=18,
    margin=dict(l=50, r=50, t=100, b=150),
    bargap=0.1
)

st.plotly_chart(fig_heatmap, use_container_width=True)

# Risk vs. 5-Year Returns
st.header("Risk vs. 5-Year Returns")
risk_order = ["Low", "Low to Moderate", "Moderate", "Moderately High", "High", "Very High", "Unknown"]
filtered_data["risk_numeric"] = filtered_data["risk_of_the_fund"].apply(lambda x: risk_order.index(x) + 1 if x in risk_order else 0)
fig_risk = px.scatter(
    filtered_data, 
    x="risk_numeric", 
    y="five_year_returns",
    color="type_of_fund",
    size="aum_funds_individual_lst",
    hover_data=["fund_name", "risk_of_the_fund", "type_of_fund"],
    labels={"risk_numeric": "Risk Level", "five_year_returns": "5-Year Returns (%)", "type_of_fund": "Fund Type"},
    title="Risk vs. 5-Year Returns",
    color_discrete_sequence=px.colors.sequential.Rainbow,
    height=600,
    width=800
)
fig_risk.update_traces(marker=dict(size=12, opacity=0.8))
fig_risk.update_xaxes(tickvals=list(range(1, len(risk_order) + 1)), ticktext=risk_order)
fig_risk.update_layout(
    title_font_size=18,
    xaxis_title_font_size=14,
    yaxis_title_font_size=14,
    legend_title_font_size=14,
    margin=dict(l=50, r=50, t=100, b=50)
)
st.plotly_chart(fig_risk, use_container_width=True)

# PE vs PB Comparison
st.header("PE vs PB Comparison")
fig_pe_pb = px.scatter(
    filtered_data, 
    x="pe", 
    y="pb",
    color="risk_of_the_fund",
    size="aum_funds_individual_lst",
    hover_data=["fund_name", "risk_of_the_fund", "type_of_fund"],
    labels={"pe": "Price-to-Earnings Ratio", "pb": "Price-to-Book Ratio", "risk_of_the_fund": "Risk Level"},
    title="PE vs PB Comparison",
    color_discrete_sequence=px.colors.sequential.Plasma,
    height=600,
    width=800
)
fig_pe_pb.update_traces(marker=dict(size=12, opacity=0.8))
fig_pe_pb.update_layout(
    title_font_size=18,
    xaxis_title_font_size=14,
    yaxis_title_font_size=14,
    legend_title_font_size=14,
    margin=dict(l=50, r=50, t=100, b=50)
)
st.plotly_chart(fig_pe_pb, use_container_width=True)

# Yield to Maturity vs Average Maturity
st.header("Yield to Maturity vs Average Maturity")
fig_ytm_maturity = px.scatter(
    filtered_data, 
    x="average_maturity", 
    y="yield_to_maturity",
    color="type_of_fund",
    size="aum_funds_individual_lst",
    hover_data=["fund_name", "type_of_fund", "risk_of_the_fund"],
    labels={"average_maturity": "Average Maturity (Years)", "yield_to_maturity": "Yield to Maturity (%)", "type_of_fund": "Fund Type"},
    title="Yield to Maturity vs Average Maturity",
    color_discrete_sequence=px.colors.sequential.Viridis,
    height=600,
    width=800
)
fig_ytm_maturity.update_traces(marker=dict(size=12, opacity=0.8))
fig_ytm_maturity.update_layout(
    title_font_size=18,
    xaxis_title_font_size=14,
    yaxis_title_font_size=14,
    legend_title_font_size=14,
    margin=dict(l=50, r=50, t=100, b=50)
)
st.plotly_chart(fig_ytm_maturity, use_container_width=True)

# Risk vs Exit Load Bar Chart
st.header("Risk vs Exit Load Comparison")
risk_exit_load = filtered_data.groupby("risk_of_the_fund").agg({
    "exit_load": "mean"
}).reset_index()
fig_risk_exit = px.bar(
    risk_exit_load, 
    x="risk_of_the_fund", 
    y="exit_load",
    labels={"risk_of_the_fund": "Risk Level", "exit_load": "Average Exit Load (%)"},
    title="Average Exit Load by Risk Level",
    color="risk_of_the_fund",
    color_discrete_sequence=px.colors.sequential.Rainbow,
    height=600
)
fig_risk_exit.update_layout(
    title_font_size=18,
    xaxis_title_font_size=14,
    yaxis_title_font_size=14,
    showlegend=False,
    margin=dict(l=50, r=50, t=100, b=50)
)
st.plotly_chart(fig_risk_exit, use_container_width=True)

# Average Asset Allocation by Fund Type
st.header("Average Asset Allocation by Fund Type")
allocation_by_type = filtered_data.groupby("type_of_fund").agg({
    "debt_per": "mean",
    "equity_per": "mean"
}).reset_index()
allocation_melted = allocation_by_type.melt(id_vars="type_of_fund", 
                                            value_vars=["debt_per", "equity_per"],
                                            var_name="Asset Type", value_name="Percentage")
allocation_melted["Label"] = allocation_melted["type_of_fund"] + " " + allocation_melted["Asset Type"].str.replace("_per", "")
fig_allocation = px.pie(
    allocation_melted, 
    names="Label", 
    values="Percentage",
    title="Average Asset Allocation by Fund Type",
    color_discrete_sequence=px.colors.sequential.Plasma,
    height=600
)
fig_allocation.update_layout(
    title_font_size=18,
    legend_title_font_size=14,
    margin=dict(l=50, r=50, t=100, b=50)
)
st.plotly_chart(fig_allocation, use_container_width=True)

# Fund Type Distribution
st.header("Fund Type Distribution")
fund_type_counts = filtered_data["type_of_fund"].value_counts().reset_index()
fund_type_counts.columns = ["type_of_fund", "count"]
fig_distribution = px.bar(
    fund_type_counts, 
    x="type_of_fund", 
    y="count",
    labels={"type_of_fund": "Fund Type", "count": "Number of Funds"},
    title="Fund Type Distribution",
    color="type_of_fund",
    color_discrete_sequence=px.colors.sequential.Viridis,
    height=600
)
fig_distribution.update_layout(
    title_font_size=18,
    xaxis_title_font_size=14,
    yaxis_title_font_size=14,
    showlegend=False,
    margin=dict(l=50, r=50, t=100, b=50)
)
st.plotly_chart(fig_distribution, use_container_width=True)

# New Visualization: Minimum SIP Investment by Fund Type
st.header("Minimum SIP Investment by Fund Type")
sip_by_type = filtered_data.groupby("type_of_fund").agg({
    "minimum_sip_funds_individual_lst": "mean"
}).reset_index()
fig_sip = px.bar(
    sip_by_type, 
    x="type_of_fund", 
    y="minimum_sip_funds_individual_lst",
    labels={"type_of_fund": "Fund Type", "minimum_sip_funds_individual_lst": "Average Minimum SIP Investment (₹)"},
    title="Average Minimum SIP Investment by Fund Type",
    color="type_of_fund",
    color_discrete_sequence=px.colors.sequential.Viridis,
    height=600
)
fig_sip.update_layout(
    title_font_size=18,
    xaxis_title_font_size=14,
    yaxis_title_font_size=14,
    showlegend=False,
    margin=dict(l=50, r=50, t=100, b=50)
)
st.plotly_chart(fig_sip, use_container_width=True)

# New Visualization: Equity AUM vs Total AUM
st.header("Equity AUM vs Total AUM")
fig_equity_aum = px.scatter(
    filtered_data, 
    x="aum_funds_individual_lst", 
    y="equity_aum",
    color="type_of_fund",
    size="five_year_returns",
    hover_data=["fund_name", "type_of_fund", "risk_of_the_fund"],
    labels={"aum_funds_individual_lst": "Total AUM (₹ Cr)", "equity_aum": "Equity AUM (₹ Cr)", "type_of_fund": "Fund Type"},
    title="Equity AUM vs Total AUM",
    color_discrete_sequence=px.colors.sequential.Rainbow,
    height=600,
    width=800
)
fig_equity_aum.update_traces(marker=dict(size=12, opacity=0.8))
fig_equity_aum.update_layout(
    title_font_size=18,
    xaxis_title_font_size=14,
    yaxis_title_font_size=14,
    legend_title_font_size=14,
    margin=dict(l=50, r=50, t=100, b=50)
)
st.plotly_chart(fig_equity_aum, use_container_width=True)

# New Visualization: Asset Allocation Breakdown Across Funds
st.header("Asset Allocation Breakdown Across Funds")
asset_allocation_data = filtered_data[["fund_name", "asset_equity", "asset_debt", "asset_cash"]]
asset_allocation_melted = asset_allocation_data.melt(id_vars="fund_name", 
                                                     value_vars=["asset_equity", "asset_debt", "asset_cash"],
                                                     var_name="Asset Type", value_name="Percentage")
fig_asset_breakdown = px.bar(
    asset_allocation_melted, 
    x="fund_name", 
    y="Percentage", 
    color="Asset Type",
    title="Asset Allocation Breakdown Across Funds",
    labels={"fund_name": "Fund Name", "Percentage": "Percentage (%)", "Asset Type": "Asset Type"},
    barmode="stack",
    color_discrete_sequence=px.colors.sequential.Plasma,
    height=600
)
fig_asset_breakdown.update_layout(
    title_font_size=18,
    xaxis_title_font_size=14,
    yaxis_title_font_size=14,
    legend_title_font_size=14,
    xaxis_tickangle=90,
    margin=dict(l=50, r=50, t=100, b=150)
)
st.plotly_chart(fig_asset_breakdown, use_container_width=True)

# Fund Selection for Detailed Analysis
st.header("Select Fund for Detailed Analysis")
selected_fund = st.selectbox("Choose a fund:", filtered_data["fund_name"].unique())

# Fund Details
st.header("Fund Details")
fund_data = filtered_data[filtered_data["fund_name"] == selected_fund].iloc[0]
col1, col2 = st.columns(2)
with col1:
    st.write(f"**Fund Name**: {fund_data['fund_name']}")
    st.write(f"**Type**: {fund_data['type_of_fund']}")
    st.write(f"**Risk Level**: {fund_data['risk_of_the_fund']}")
    st.write(f"**AUM (₹ Cr)**: {fund_data['aum_funds_individual_lst'] / 1000:.2f}K")
    st.write(f"**Equity AUM (₹ Cr)**: {fund_data['equity_aum'] / 1000:.2f}K")
    st.write(f"**NAV (₹)**: {fund_data['nav_funds_individual_lst']:.2f}")
    st.write(f"**Minimum Investment (₹)**: {fund_data['minimum_funds_individual_lst']:.2f}")
    st.write(f"**Minimum SIP Investment (₹)**: {fund_data['minimum_sip_funds_individual_lst']:.2f}")
    st.write(f"**Historical NAV Summary**: {fund_data['historical_nav_summary']}")
with col2:
    st.write(f"**PE Ratio**: {fund_data['pe']:.2f}")
    st.write(f"**PB Ratio**: {fund_data['pb']:.2f}")
    st.write(f"**Exit Load (%)**: {fund_data['exit_load']:.2f}")
    st.write(f"**Average Maturity (Years)**: {fund_data['average_maturity']:.2f}")
    st.write(f"**Yield to Maturity (%)**: {fund_data['yield_to_maturity']:.2f}")
    st.write(f"**Asset Allocation Summary**: {fund_data['asset_allocation_summary']}")
    st.write(f"**Top Holdings Summary**: {fund_data['top_holdings_summary']}")
    if pd.notna(fund_data["link"]):
        st.write(f"**Website**: [Link]({fund_data['link']})")

# Portfolio Allocation for Selected Fund
st.header("Portfolio Allocation for Selected Fund")
allocation_data = [
    {"Asset Type": "Debt", "Percentage": fund_data["debt_per"]},
    {"Asset Type": "Equity", "Percentage": fund_data["equity_per"]}
]
fig_selected_allocation = px.pie(
    pd.DataFrame(allocation_data), 
    names="Asset Type", 
    values="Percentage",
    title=f"Portfolio Allocation for {selected_fund}",
    color_discrete_sequence=px.colors.sequential.Rainbow,
    height=600
)
fig_selected_allocation.update_layout(
    title_font_size=18,
    legend_title_font_size=14,
    margin=dict(l=50, r=50, t=100, b=50)
)
st.plotly_chart(fig_selected_allocation, use_container_width=True)

# New Visualization: Sector Allocation for Selected Fund
st.header("Sector Allocation for Selected Fund")
sector_summary = fund_data["sector_allocation_summary"]
if sector_summary and sector_summary != "N/A":
    # Parse sector allocation summary (e.g., "Energy (39.18%); Capital Goods (28.41%); ...")
    sectors = []
    percentages = []
    for entry in sector_summary.split(";"):
        if "(" in entry and ")" in entry:
            sector = entry.split("(")[0].strip()
            percentage = float(entry.split("(")[1].replace("%)", "").strip())
            sectors.append(sector)
            percentages.append(percentage)
    sector_data = pd.DataFrame({"Sector": sectors, "Percentage": percentages})
    fig_sector = px.treemap(
        sector_data, 
        path=["Sector"], 
        values="Percentage",
        title=f"Sector Allocation for {selected_fund}",
        color="Percentage",
        color_continuous_scale="Viridis",
        height=600
    )
    fig_sector.update_layout(
        title_font_size=18,
        margin=dict(l=50, r=50, t=100, b=50)
    )
    st.plotly_chart(fig_sector, use_container_width=True)
else:
    st.write(f"No sector allocation data available for {selected_fund}.")

# Future Value Prediction Calculator
st.header("Future Value Prediction Calculator")
investment_amount = st.number_input("Investment Amount (₹)", min_value=0.0, value=10000.0)
investment_duration = st.number_input("Investment Duration (Years)", min_value=1, value=5)

fund_nav_data = sheet2[sheet2["fund_name"] == selected_fund].sort_values("date")
if len(fund_nav_data) >= 2:
    first_entry = fund_nav_data.iloc[0]
    last_entry = fund_nav_data.iloc[-1]
    start_nav = first_entry["nav"]
    end_nav = last_entry["nav"]
    start_date = first_entry["date"]
    end_date = last_entry["date"]
    years = (end_date - start_date).days / 365.25
    cagr = (end_nav / start_nav) ** (1 / years) - 1 if years > 0 and start_nav > 0 and end_nav > 0 else 0
else:
    valid_returns = [fund_data["one_year_returns"], fund_data["three_year_returns"], fund_data["five_year_returns"]]
    valid_returns = [r for r in valid_returns if r != 0]
    cagr = np.mean(valid_returns) / 100 if valid_returns else 0

if st.button("Calculate Future Value"):
    future_value = investment_amount * (1 + cagr) ** investment_duration
    st.write(f"Estimated Future Value: ₹{future_value:.2f}")

# Historical NAV Trend
st.header("Historical NAV Trend")
if not fund_nav_data.empty:
    fig_nav = px.line(
        fund_nav_data, 
        x="date", 
        y="nav",
        labels={"date": "Date", "nav": "NAV (₹)"},
        title=f"Historical NAV Trend for {selected_fund}",
        color_discrete_sequence=px.colors.sequential.Plasma,
        height=600
    )
    fig_nav.update_layout(
        title_font_size=18,
        xaxis_title_font_size=14,
        yaxis_title_font_size=14,
        margin=dict(l=50, r=50, t=100, b=50)
    )
    st.plotly_chart(fig_nav, use_container_width=True)
else:
    st.write(f"No historical NAV data available for {selected_fund}.")

# Top Holdings
st.header("Top Holdings")
fund_holdings = sheet3[sheet3["fund_name"] == selected_fund].sort_values("percentage", ascending=False).head(5)
if not fund_holdings.empty:
    fig_holdings = px.bar(
        fund_holdings, 
        x="company", 
        y="percentage",
        labels={"company": "Company", "percentage": "Percentage (%)"},
        title=f"Top Holdings for {selected_fund}",
        color="company",
        color_discrete_sequence=px.colors.sequential.Viridis,
        height=600
    )
    fig_holdings.update_layout(
        title_font_size=18,
        xaxis_title_font_size=14,
        yaxis_title_font_size=14,
        showlegend=False,
        margin=dict(l=50, r=50, t=100, b=50)
    )
    st.plotly_chart(fig_holdings, use_container_width=True)
else:
    st.write(f"No top holdings data available for {selected_fund}.")

# Multi-Fund Comparison
st.header("Compare Multiple Funds")
selected_funds = st.multiselect("Select funds to compare:", filtered_data["fund_name"].unique(), default=[selected_fund])
if selected_funds:
    compare_data = filtered_data[filtered_data["fund_name"].isin(selected_funds)]
    compare_melted = compare_data.melt(id_vars="fund_name", 
                                       value_vars=["one_year_returns", "three_year_returns", "five_year_returns", "pe", "pb", "exit_load", "equity_aum"],
                                       var_name="Metric", value_name="Value")
    fig_compare = px.bar(
        compare_melted, 
        x="fund_name", 
        y="Value", 
        color="Metric",
        title="Comparison of Selected Funds",
        labels={"fund_name": "Fund Name", "Value": "Value", "Metric": "Metric"},
        barmode="group",
        color_discrete_sequence=px.colors.sequential.Rainbow,
        height=600
    )
    fig_compare.update_layout(
        legend_title_text="Metric",
        title_font_size=18,
        xaxis_title_font_size=14,
        yaxis_title_font_size=14,
        margin=dict(l=50, r=50, t=100, b=50)
    )
    st.plotly_chart(fig_compare, use_container_width=True)

# Conclusion
st.header("Conclusion")
st.write(
    "This enhanced dashboard provides a comprehensive analysis of mutual funds, with advanced comparison charts "
    "and filtering capabilities. Explore funds by type, risk, minimum investment, and SIP requirements, compare their "
    "performance, valuation metrics, costs, asset allocations, and sector exposures. The prediction calculator, "
    "historical data, and detailed fund insights help you make informed investment decisions."
)