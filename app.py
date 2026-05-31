from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image, ImageDraw, ImageFont


st.set_page_config(page_title="DAAC Heat Study", layout="wide")

st.title("DAAC Heat Study Dashboard")
st.write("Upload your CSV or Excel file to view surface temperature figures.")

uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])

if uploaded_file is None:
    st.info("Upload your data file to begin.")
    st.stop()


# -----------------------------
# Load data
# -----------------------------
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

if "date" in df.columns:
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

id_vars = [
    c for c in ["date", "time", "ambient_temp", "cloud_cover", "wind_speed"]
    if c in df.columns
]

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


# -----------------------------
# Helper functions
# -----------------------------
def style_figure(fig):
    fig.update_layout(
        title=dict(text=""),
        font=dict(size=15),
        legend_title_text="Surface Type",
        margin=dict(t=20, b=170),
        hovermode="closest",
        height=750
    )

    fig.update_xaxes(
        title_font=dict(size=16),
        tickfont=dict(size=12),
        tickangle=0,
        automargin=True
    )

    fig.update_yaxes(
        title_font=dict(size=16),
        tickfont=dict(size=13),
        automargin=True
    )

    return fig

def top_bottom_text(data, value_col):
    top = data.loc[data[value_col].idxmax()]
    bottom = data.loc[data[value_col].idxmin()]
    return top, bottom


def load_font(size, bold=False):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]

    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass

    return ImageFont.load_default()


def draw_wrapped_text(draw, text, x, y, font, max_width, line_spacing=10, fill="black"):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + " " + word if current_line else word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), line, font=font)
        y += (bbox[3] - bbox[1]) + line_spacing

    return y


def create_download_jpg(fig, title):
    fig = style_figure(fig)

    fig.update_layout(
        width=1500,
        height=900,
        margin=dict(t=30, b=220, l=90, r=50)
    )

    chart_bytes = fig.to_image(
        format="png",
        width=1500,
        height=900,
        scale=2
    )

    chart = Image.open(BytesIO(chart_bytes)).convert("RGB")
    chart = chart.resize((1500, 900))

    width = 1600
    padding = 50

    title_font = load_font(64, bold=True)

    temp_img = Image.new("RGB", (width, 300), "white")
    temp_draw = ImageDraw.Draw(temp_img)

    bbox = temp_draw.textbbox((0, 0), title, font=title_font)
    title_width = bbox[2] - bbox[0]
    title_height = bbox[3] - bbox[1]

    total_height = padding + title_height + 40 + chart.height + padding

    final_img = Image.new("RGB", (width, total_height), "white")
    draw = ImageDraw.Draw(final_img)

    title_x = (width - title_width) // 2

    draw.text(
        (title_x, padding),
        title,
        font=title_font,
        fill="black"
    )

    chart_y = padding + title_height + 40

    final_img.paste(
        chart,
        (padding, chart_y)
    )

    output = BytesIO()
    final_img.save(output, format="JPEG", quality=95)
    output.seek(0)

    return output


def show_figure(title, fig, purpose, finding):
    st.header(title)

    st.markdown("### What this figure shows")
    st.write(purpose)

    st.markdown("### Key Findings / Why This Figure Is Important")
    st.write(finding)

    fig = style_figure(fig)
    st.plotly_chart(fig, use_container_width=True)

    try:
        jpg = create_download_jpg(fig, title)
        st.download_button(
            label="Download full figure as JPG",
            data=jpg,
            file_name=title.replace(" ", "_").replace("/", "_") + ".jpg",
            mime="image/jpeg"
        )
    except Exception as e:
        st.error("JPG download failed. Check that kaleido==0.2.1 and pillow are in requirements.txt.")
        st.caption(str(e))


# -----------------------------
# Figure selector
# -----------------------------
figure_choice = st.selectbox(
    "Choose a figure",
    [
        "1. Average Surface Temperature Bar Chart",
        "2. Surface Temperature by Time of Day",
        "3. Temperature Spread by Surface"
    ]
)


# -----------------------------
# Figure 1
# -----------------------------
if figure_choice == "1. Average Surface Temperature Bar Chart":
    title = "Average Surface Temperature Bar Chart"

    summary = (
        long_df.groupby("surface", as_index=False)["surface_temp"]
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

    top, bottom = top_bottom_text(summary, "surface_temp")
    difference = top["surface_temp"] - bottom["surface_temp"]

    purpose = (
        "This figure compares the overall average temperature for each surface type "
        "using the uploaded data."
    )

    finding = (
        f"The hottest surface was {top['surface']} with an average temperature of "
        f"{top['surface_temp']:.1f}°F. The coolest surface was {bottom['surface']} "
        f"with an average temperature of {bottom['surface_temp']:.1f}°F. The difference "
        f"between the hottest and coolest surfaces was {difference:.1f}°F."
    )

    show_figure(title, fig, purpose, finding)


# -----------------------------
# Figure 2
# -----------------------------
elif figure_choice == "2. Surface Temperature by Time of Day":
    title = "Surface Temperature by Time of Day"

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

    time_summary = (
        long_df.groupby("time", as_index=False)["surface_temp"]
        .mean()
        .dropna()
    )

    top_time, bottom_time = top_bottom_text(time_summary, "surface_temp")

    surface_summary = (
        long_df.groupby("surface", as_index=False)["surface_temp"]
        .mean()
        .sort_values("surface_temp", ascending=False)
    )

    hottest_surface = surface_summary.iloc[0]

    purpose = (
        "This figure shows how average surface temperatures changed by time of day "
        "for each surface type."
    )

    finding = (
        f"The warmest time of day overall was {top_time['time']} with an average surface "
        f"temperature of {top_time['surface_temp']:.1f}°F. The coolest time was "
        f"{bottom_time['time']} with an average of {bottom_time['surface_temp']:.1f}°F. "
        f"Across the uploaded data, {hottest_surface['surface']} had the highest overall "
        f"average temperature."
    )

    show_figure(title, fig, purpose, finding)


# -----------------------------
# Figure 3
# -----------------------------
elif figure_choice == "3. Temperature Spread by Surface":
    title = "Temperature Spread by Surface"

    fig = px.box(
        long_df,
        x="surface",
        y="surface_temp",
        color="surface",
        labels={
            "surface": "Surface Type",
            "surface_temp": "Surface Temperature (°F)"
        }
    )


    spread = (
        long_df.groupby("surface")["surface_temp"]
        .agg(["min", "max", "mean"])
        .reset_index()
    )

    spread["range"] = spread["max"] - spread["min"]

    widest = spread.loc[spread["range"].idxmax()]
    narrowest = spread.loc[spread["range"].idxmin()]
    hottest = spread.loc[spread["mean"].idxmax()]

    purpose = (
        "This box plot shows the spread, median, and variability of temperatures "
        "for each surface type."
    )

    finding = (
        f"{widest['surface']} had the widest temperature spread, ranging "
        f"{widest['range']:.1f}°F between its lowest and highest recorded values. "
        f"{narrowest['surface']} had the smallest spread, ranging "
        f"{narrowest['range']:.1f}°F. Based on average temperature, "
        f"{hottest['surface']} was the hottest surface overall."
    )

    show_figure(title, fig, purpose, finding)
