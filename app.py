import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Surface Temperature App", layout="wide")

st.title("Surface Temperature Dashboard")

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

long_df = df.melt(
    id_vars=[c for c in ["date", "time", "ambient_temp", "cloud_cover", "wind_speed"] if c in df.columns],
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

figure_choice = st.selectbox(
    "Choose a figure",
    [
        "3 PM Average Surface Temperature",
        "Average Surface Temperatures by Time of Day",
        "Ambient Air Temperature vs Surface Temperature"
    ]
)

def style_figure(fig):
    fig.update_layout(
        title=None,
        font=dict(size=15),
        legend_title_text="Surface Type",
        margin=dict(t=40, b=80),
        hovermode="closest"
    )
    return fig

def show_figure(title, fig, purpose, conclusion):
    st.header(title)

    fig = style_figure(fig)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### What this figure shows:")
    st.write(f"This **{title}** {purpose}")

    st.markdown("### Key Findings / Why This Figure Is Important:")
    st.write(conclusion)

    jpg = fig.to_image(format="jpg", scale=3)

    st.download_button(
        label="Download figure as JPG",
        data=jpg,
        file_name=title.replace(" ", "_") + ".jpg",
        mime="image/jpeg"
    )

if figure_choice == "3 PM Average Surface Temperature":
    title = "3 PM Average Surface Temperature"
    purpose = "shows which surfaces reached the highest average temperatures during the hottest part of the day."
    conclusion = "If asphalt has the tallest bars, findings conclude that asphalt absorbed and retained more heat than the other surfaces."

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
        labels={
            "surface": "Surface Type",
            "surface_temp": "Average Surface Temperature (°F)"
        }
    )

    fig.update_traces(texttemplate="%{text:.1f}°F", textposition="outside")
    fig.update_layout(xaxis_tickangle=-35)

    show_figure(title, fig, purpose, conclusion)

elif figure_choice == "Average Surface Temperatures by Time of Day":
    title = "Average Surface Temperatures by Time of Day"
    purpose = "shows how temperatures changed from morning to afternoon to evening."
    conclusion = "If afternoon temperatures are highest, findings conclude that surface heating increased throughout the day."

    summary = (
        long_df.groupby(["time", "surface"], as_index=False)["surface_temp"]
        .mean()
    )

    fig = px.bar(
        summary,
        x="time",
        y="surface_temp",
        color="surface",
        barmode="group",
        labels={
            "time": "Time of Day",
            "surface_temp": "Average Surface Temperature (°F)",
            "surface": "Surface Type"
        }
    )

    show_figure(title, fig, purpose, conclusion)

elif figure_choice == "Ambient Air Temperature vs Surface Temperature":
    title = "Ambient Air Temperature vs Surface Temperature"
    purpose = "shows whether hotter air is connected to hotter surfaces."
    conclusion = "If points rise as air temperature rises, surface temperature also increases."

    fig = px.scatter(
        long_df,
        x="ambient_temp",
        y="surface_temp",
        color="surface",
        symbol="time",
        labels={
            "ambient_temp": "Ambient Air Temperature (°F)",
            "surface_temp": "Surface Temperature (°F)",
            "surface": "Surface Type",
            "time": "Time of Day"
        }
    )

    show_figure(title, fig, purpose, conclusion)
