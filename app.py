import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="DAAC Heat Study", layout="wide")

st.title("DAAC Heat Study Dashboard")
st.write("Upload your CSV or Excel file to view surface temperature figures.")

uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])

if uploaded_file is None:
    st.info("Upload your data file to begin.")
    st.stop()

if uploaded_file.name.endswith(".csv"):
    df = pd.read_csv(uploaded_file)
else:
    df = pd.read_excel(uploaded_file)

st.success("Data loaded successfully!")
st.dataframe(df.head())

df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
    .str.replace("/", "", regex=False)
)

rename_map = {
    "date": "date",
    "time_of_day": "time",
    "ambient_air_temperature": "ambient_temp",
    "cloud_cover": "cloud_cover",
    "wind_speed": "wind_speed",
    "black_aggregate__asphalt": "black_asphalt",
    "black_aggregate_asphalt": "black_asphalt",
    "light_gray_aggregate": "light_gray",
    "2_coats_white_cooling_sealant": "white_2_coats",
    "4_coats_white_cooling_sealant": "white_4_coats",
    "dirt": "dirt",
    "vegetation": "vegetation"
}

df.rename(columns=rename_map, inplace=True)

surface_cols = [
    "black_asphalt",
    "light_gray",
    "white_2_coats",
    "white_4_coats",
    "dirt",
    "vegetation"
]

surface_cols = [c for c in surface_cols if c in df.columns]

df["date"] = pd.to_datetime(df["date"], errors="coerce")

for col in ["ambient_temp"] + surface_cols:
    if col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace("F", "", regex=False)
            .str.strip()
        )
        df[col] = pd.to_numeric(df[col], errors="coerce")

if "time" in df.columns:
    df["time"] = df["time"].astype(str).str.strip().str.lower()
    df["time"] = pd.Categorical(
        df["time"],
        categories=["8a", "3p", "7p"],
        ordered=True
    )

id_vars = [c for c in ["date", "time", "ambient_temp", "cloud_cover", "wind_speed"] if c in df.columns]

long_df = df.melt(
    id_vars=id_vars,
    value_vars=surface_cols,
    var_name="surface",
    value_name="surface_temp"
)

surface_names = {
    "black_asphalt": "Black Aggregate / Asphalt",
    "light_gray": "Light Gray Aggregate",
    "white_2_coats": "2 Coats White Cooling Sealant",
    "white_4_coats": "4 Coats White Cooling Sealant",
    "dirt": "Dirt",
    "vegetation": "Vegetation"
}

long_df["surface"] = long_df["surface"].map(surface_names)
long_df = long_df.dropna(subset=["surface", "surface_temp"])

def style_figure(fig):
    fig.update_layout(
        title=None,
        font=dict(size=15),
        legend_title_text="Surface Type",
        margin=dict(t=40, b=80),
        hovermode="closest"
    )
    fig.update_xaxes(title_font=dict(size=16), tickfont=dict(size=13))
    fig.update_yaxes(title_font=dict(size=16), tickfont=dict(size=13))
    return fig

def top_bottom_text(data, value_col):
    if data.empty:
        return "No data available.", "No data available."
    top = data.loc[data[value_col].idxmax()]
    bottom = data.loc[data[value_col].idxmin()]
    return top, bottom

def show_figure(title, fig, purpose, finding):
    st.header(title)
    fig = style_figure(fig)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### What this figure shows")
    st.write(purpose)

    st.markdown("### Key Findings / Why This Figure Is Important")
    st.write(finding)

    try:
        jpg = fig.to_image(format="jpg", scale=3)
        st.download_button(
            label="Download figure as JPG",
            data=jpg,
            file_name=title.replace(" ", "_").replace("/", "_") + ".jpg",
            mime="image/jpeg"
        )
    except Exception:
        st.warning("JPG download is unavailable. Make sure kaleido is listed in requirements.txt.")

figure_choice = st.selectbox(
    "Choose a figure",
    [
        "1. 3 PM Average Surface Temperature",
        "2. Surface Temperatures by Cloud Cover",
        "3. Surface Temperatures by Wind Speed",
        "4. Surface Temperatures by Day",
        "5. Surface Temperatures by Time of Day",
        "6. Temperature Trends with Variability",
        "7. Asphalt Compared to Cooling Sealant",
        "8. Surface Temperature Above Air Temperature",
        "9. Surface Temperature Trends by Date",
        "10. Temperature Spread by Surface",
        "11. Ambient Air Temperature vs Surface Temperature",
        "12. Heatmap Table"
    ]
)

time_choice = None
if figure_choice in [
    "2. Surface Temperatures by Cloud Cover",
    "3. Surface Temperatures by Wind Speed",
    "6. Temperature Trends with Variability",
    "8. Surface Temperature Above Air Temperature",
    "9. Surface Temperature Trends by Date",
    "10. Temperature Spread by Surface"
]:
    time_choice = st.selectbox("Choose time", ["all", "8a", "3p", "7p"])

if figure_choice == "1. 3 PM Average Surface Temperature":
    title = "3 PM Average Surface Temperature"
    data = long_df[long_df["time"] == "3p"]

    summary = (
        data.groupby("surface", as_index=False)["surface_temp"]
        .mean()
        .sort_values("surface_temp", ascending=False)
    )

    fig = px.bar(
        summary,
        x="surface",
        y="surface_temp",
        text="surface_temp",
        labels={"surface": "Surface Type", "surface_temp": "Average Surface Temperature (°F)"}
    )
    fig.update_traces(texttemplate="%{text:.1f}°F", textposition="outside")
    fig.update_layout(xaxis_tickangle=-35)

    top, bottom = top_bottom_text(summary, "surface_temp")
    purpose = "This figure compares the average surface temperature of each surface at 3 PM."
    finding = f"The hottest surface at 3 PM was {top['surface']} with an average temperature of {top['surface_temp']:.1f}°F. The coolest surface was {bottom['surface']} with an average temperature of {bottom['surface_temp']:.1f}°F."

    show_figure(title, fig, purpose, finding)

elif figure_choice == "2. Surface Temperatures by Cloud Cover":
    title = f"Average Surface Temperature by Cloud Cover ({time_choice})"
    data = long_df.copy()
    if time_choice != "all":
        data = data[data["time"] == time_choice]

    summary = data.groupby(["cloud_cover", "surface"], as_index=False)["surface_temp"].mean()

    fig = px.bar(
        summary,
        x="cloud_cover",
        y="surface_temp",
        color="surface",
        barmode="group",
        labels={"cloud_cover": "Cloud Cover", "surface_temp": "Average Surface Temperature (°F)", "surface": "Surface Type"}
    )

    top, bottom = top_bottom_text(summary, "surface_temp")
    purpose = "This figure shows how average surface temperatures changed under different cloud cover conditions."
    finding = f"The highest average temperature was {top['surface_temp']:.1f}°F for {top['surface']} during {top['cloud_cover']} cloud cover. The lowest average temperature was {bottom['surface_temp']:.1f}°F for {bottom['surface']} during {bottom['cloud_cover']} cloud cover."

    show_figure(title, fig, purpose, finding)

elif figure_choice == "3. Surface Temperatures by Wind Speed":
    title = f"Average Surface Temperature by Wind Speed ({time_choice})"
    data = long_df.copy()
    if time_choice != "all":
        data = data[data["time"] == time_choice]

    summary = data.groupby(["wind_speed", "surface"], as_index=False)["surface_temp"].mean()

    fig = px.bar(
        summary,
        x="wind_speed",
        y="surface_temp",
        color="surface",
        barmode="group",
        labels={"wind_speed": "Wind Speed", "surface_temp": "Average Surface Temperature (°F)", "surface": "Surface Type"}
    )

    top, bottom = top_bottom_text(summary, "surface_temp")
    purpose = "This figure shows how surface temperatures varied by wind speed."
    finding = f"The highest average temperature was {top['surface_temp']:.1f}°F for {top['surface']} at wind speed {top['wind_speed']}. The lowest average temperature was {bottom['surface_temp']:.1f}°F for {bottom['surface']} at wind speed {bottom['wind_speed']}."

    show_figure(title, fig, purpose, finding)

elif figure_choice == "4. Surface Temperatures by Day":
    title = "Surface Temperatures by Day"

    fig = px.bar(
        long_df,
        x="surface",
        y="surface_temp",
        color="surface",
        facet_col="time",
        facet_col_wrap=3,
        labels={"surface": "Surface Type", "surface_temp": "Surface Temperature (°F)", "time": "Time of Day"}
    )
    fig.update_layout(xaxis_tickangle=-35)

    avg = long_df.groupby("surface", as_index=False)["surface_temp"].mean()
    top, bottom = top_bottom_text(avg, "surface_temp")
    purpose = "This figure shows surface temperature measurements across the study days and times."
    finding = f"Across all days and times, {top['surface']} had the highest overall average temperature at {top['surface_temp']:.1f}°F. {bottom['surface']} had the lowest overall average temperature at {bottom['surface_temp']:.1f}°F."

    show_figure(title, fig, purpose, finding)

elif figure_choice == "5. Surface Temperatures by Time of Day":
    title = "Average Surface Temperatures by Time of Day"

    summary = long_df.groupby(["time", "surface"], as_index=False)["surface_temp"].mean()

    fig = px.bar(
        summary,
        x="time",
        y="surface_temp",
        color="surface",
        barmode="group",
        labels={"time": "Time of Day", "surface_temp": "Average Surface Temperature (°F)", "surface": "Surface Type"}
    )

    time_summary = long_df.groupby("time", as_index=False)["surface_temp"].mean()
    top, bottom = top_bottom_text(time_summary, "surface_temp")
    purpose = "This figure compares average surface temperatures in the morning, afternoon, and evening."
    finding = f"The warmest time of day overall was {top['time']} with an average surface temperature of {top['surface_temp']:.1f}°F. The coolest time was {bottom['time']} with an average of {bottom['surface_temp']:.1f}°F."

    show_figure(title, fig, purpose, finding)

elif figure_choice == "6. Temperature Trends with Variability":
    title = f"Temperature Trends with Variability ({time_choice})"
    data = long_df.copy()
    if time_choice != "all":
        data = data[data["time"] == time_choice]

    summary = (
        data.groupby(["surface", "date"], as_index=False)
        .agg(average_temp=("surface_temp", "mean"), std_dev=("surface_temp", "std"))
    )

    fig = px.line(
        summary,
        x="date",
        y="average_temp",
        color="surface",
        error_y="std_dev",
        markers=True,
        labels={"date": "Date", "average_temp": "Average Surface Temperature (°F)", "surface": "Surface Type"}
    )

    avg = summary.groupby("surface", as_index=False)["average_temp"].mean()
    top, bottom = top_bottom_text(avg, "average_temp")
    purpose = "This figure shows temperature trends over time and includes variability using error bars."
    finding = f"{top['surface']} had the highest average trend temperature at {top['average_temp']:.1f}°F. {bottom['surface']} had the lowest average trend temperature at {bottom['average_temp']:.1f}°F."

    show_figure(title, fig, purpose, finding)

elif figure_choice == "7. Asphalt Compared to Cooling Sealant":
    title = "How Much Cooler Is White Cooling Sealant Than Asphalt?"

    if "black_asphalt" not in df.columns or "white_2_coats" not in df.columns:
        st.error("This figure requires black asphalt and 2 coat white sealant columns.")
        st.stop()

    temp = df.copy()
    temp["Asphalt - 2 Coat Sealant"] = temp["black_asphalt"] - temp["white_2_coats"]

    diff_cols = ["Asphalt - 2 Coat Sealant"]

    if "white_4_coats" in temp.columns:
        temp["Asphalt - 4 Coat Sealant"] = temp["black_asphalt"] - temp["white_4_coats"]
        diff_cols.append("Asphalt - 4 Coat Sealant")

    diff = temp.melt(
        id_vars=["date", "time"],
        value_vars=diff_cols,
        var_name="comparison",
        value_name="temperature_difference"
    )

    fig = px.bar(
        diff,
        x="date",
        y="temperature_difference",
        color="comparison",
        facet_col="time",
        barmode="group",
        labels={"temperature_difference": "Temperature Difference (°F)", "date": "Date", "comparison": "Comparison"}
    )

    avg_diff = diff.groupby("comparison", as_index=False)["temperature_difference"].mean()
    top, bottom = top_bottom_text(avg_diff, "temperature_difference")
    purpose = "This figure shows how many degrees hotter asphalt was compared with white cooling sealant."
    finding = f"On average, the largest cooling difference was for {top['comparison']}, with asphalt measuring {top['temperature_difference']:.1f}°F hotter. The smallest average difference was {bottom['temperature_difference']:.1f}°F for {bottom['comparison']}."

    show_figure(title, fig, purpose, finding)

elif figure_choice == "8. Surface Temperature Above Air Temperature":
    title = f"Average Surface Temperature Above Air Temperature ({time_choice})"
    temp = long_df.copy()
    temp["surface_minus_air"] = temp["surface_temp"] - temp["ambient_temp"]

    if time_choice != "all":
        temp = temp[temp["time"] == time_choice]

    summary = (
        temp.groupby("surface", as_index=False)["surface_minus_air"]
        .mean()
        .sort_values("surface_minus_air", ascending=False)
    )

    fig = px.bar(
        summary,
        x="surface",
        y="surface_minus_air",
        text="surface_minus_air",
        labels={"surface": "Surface Type", "surface_minus_air": "Degrees Above Air Temperature (°F)"}
    )
    fig.update_traces(texttemplate="%{text:.1f}°F", textposition="outside")
    fig.update_layout(xaxis_tickangle=-35)

    top, bottom = top_bottom_text(summary, "surface_minus_air")
    purpose = "This figure shows how much hotter each surface became compared with the surrounding air temperature."
    finding = f"{top['surface']} was the most above air temperature, averaging {top['surface_minus_air']:.1f}°F above the air. {bottom['surface']} was closest to air temperature, averaging {bottom['surface_minus_air']:.1f}°F above the air."

    show_figure(title, fig, purpose, finding)

elif figure_choice == "9. Surface Temperature Trends by Date":
    title = f"Surface Temperature Trends by Date ({time_choice})"
    data = long_df.copy()
    if time_choice != "all":
        data = data[data["time"] == time_choice]

    fig = px.line(
        data,
        x="date",
        y="surface_temp",
        color="surface",
        markers=True,
        labels={"date": "Date", "surface_temp": "Surface Temperature (°F)", "surface": "Surface Type"}
    )

    avg = data.groupby("surface", as_index=False)["surface_temp"].mean()
    top, bottom = top_bottom_text(avg, "surface_temp")
    purpose = "This figure shows how each surface temperature changed across the study dates."
    finding = f"Across the selected dates, {top['surface']} had the highest average temperature at {top['surface_temp']:.1f}°F. {bottom['surface']} had the lowest average temperature at {bottom['surface_temp']:.1f}°F."

    show_figure(title, fig, purpose, finding)

elif figure_choice == "10. Temperature Spread by Surface":
    title = f"Temperature Spread by Surface ({time_choice})"
    data = long_df.copy()
    if time_choice != "all":
        data = data[data["time"] == time_choice]

    fig = px.box(
        data,
        x="surface",
        y="surface_temp",
        color="surface",
        labels={"surface": "Surface Type", "surface_temp": "Surface Temperature (°F)"}
    )
    fig.update_layout(xaxis_tickangle=-35)

    spread = data.groupby("surface", as_index=False)["surface_temp"].agg(["min", "max"]).reset_index()
    spread["range"] = spread["max"] - spread["min"]
    top, bottom = top_bottom_text(spread, "range")
    purpose = "This figure shows the spread and variability of surface temperatures for each surface type."
    finding = f"{top['surface']} had the widest temperature spread, ranging {top['range']:.1f}°F. {bottom['surface']} had the smallest spread, ranging {bottom['range']:.1f}°F."

    show_figure(title, fig, purpose, finding)

elif figure_choice == "11. Ambient Air Temperature vs Surface Temperature":
    title = "Ambient Air Temperature vs Surface Temperature"

    fig = px.scatter(
        long_df,
        x="ambient_temp",
        y="surface_temp",
        color="surface",
        symbol="time",
        labels={"ambient_temp": "Ambient Air Temperature (°F)", "surface_temp": "Surface Temperature (°F)", "surface": "Surface Type", "time": "Time of Day"}
    )

    corr = long_df[["ambient_temp", "surface_temp"]].dropna().corr().iloc[0, 1]
    avg = long_df.groupby("surface", as_index=False)["surface_temp"].mean()
    top, bottom = top_bottom_text(avg, "surface_temp")
    purpose = "This figure shows the relationship between ambient air temperature and measured surface temperature."
    finding = f"The correlation between air temperature and surface temperature is {corr:.2f}. The highest average surface temperature was for {top['surface']} at {top['surface_temp']:.1f}°F, while the lowest was for {bottom['surface']} at {bottom['surface_temp']:.1f}°F."

    show_figure(title, fig, purpose, finding)

elif figure_choice == "12. Heatmap Table":
    title = "Heatmap Table of Surface Temperatures"

    st.header(title)

    pivot = long_df.pivot_table(
        index=["date", "time"],
        columns="surface",
        values="surface_temp",
        aggfunc="mean"
    )

    st.dataframe(pivot.style.background_gradient(cmap="YlOrRd"))

    max_surface = pivot.mean().idxmax()
    min_surface = pivot.mean().idxmin()

    st.markdown("### What this figure shows")
    st.write("This heatmap table shows the average temperature values for each surface across dates and times.")

    st.markdown("### Key Findings / Why This Figure Is Important")
    st.write(f"Based on the uploaded data, {max_surface} had the highest overall average temperature in the heatmap, while {min_surface} had the lowest overall average temperature.")

    csv = pivot.to_csv().encode("utf-8")
    st.download_button(
        label="Download heatmap table as CSV",
        data=csv,
        file_name="Heatmap_Table.csv",
        mime="text/csv"
    )
