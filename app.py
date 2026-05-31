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


# -----------------------------
# Clean data
# -----------------------------
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
    "vegetation": "vegetation",
}

df.rename(columns=rename_map, inplace=True)

surface_cols = [
    "black_asphalt",
    "light_gray",
    "white_2_coats",
    "white_4_coats",
    "dirt",
    "vegetation",
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
        ordered=True,
    )

id_vars = [
    c for c in ["date", "time", "ambient_temp", "cloud_cover", "wind_speed"]
    if c in df.columns
]

long_df = df.melt(
    id_vars=id_vars,
    value_vars=surface_cols,
    var_name="surface",
    value_name="surface_temp",
)

surface_names = {
    "black_asphalt": "Black Aggregate / Asphalt",
    "light_gray": "Light Gray Aggregate",
    "white_2_coats": "2 Coats White Cooling Sealant",
    "white_4_coats": "4 Coats White Cooling Sealant",
    "dirt": "Dirt",
    "vegetation": "Vegetation",
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
        margin=dict(t=20, b=190, l=80, r=40),
        hovermode="closest",
        height=750,
    )

    fig.update_xaxes(
        title_font=dict(size=16),
        tickfont=dict(size=12),
        tickangle=0,
        automargin=True,
    )

    fig.update_yaxes(
        title_font=dict(size=16),
        tickfont=dict(size=13),
        automargin=True,
    )

    return fig


def top_bottom_text(data, value_col):
    top = data.loc[data[value_col].idxmax()]
    bottom = data.loc[data[value_col].idxmin()]
    return top, bottom


def load_font(size, bold=False):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]

    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass

    return ImageFont.load_default()


def draw_wrapped_text(draw, text, x, y, font, max_width, line_spacing=10, fill="black"):
    words = str(text).split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + " " + word if current_line else word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), line, font=font)
        y += (bbox[3] - bbox[1]) + line_spacing

    return y


def create_custom_jpg(
    fig,
    title,
    purpose,
    finding,
    include_title=True,
    include_figure=True,
    include_purpose=False,
    include_finding=True,
    title_size=56,
    purpose_size=24,
    finding_size=24,
    figure_width=1500,
    figure_height=900,
):
    fig = style_figure(fig)

    fig.update_layout(
        width=figure_width,
        height=figure_height,
        margin=dict(t=30, b=230, l=90, r=50),
    )

    width = figure_width + 100
    padding = 50
    section_gap = 35

    title_font = load_font(title_size, bold=True)
    heading_font = load_font(max(24, finding_size + 4), bold=True)
    purpose_font = load_font(purpose_size, bold=False)
    finding_font = load_font(finding_size, bold=False)

    chart = None
    if include_figure:
        chart_bytes = fig.to_image(
            format="png",
            width=figure_width,
            height=figure_height,
            scale=2,
        )
        chart = Image.open(BytesIO(chart_bytes)).convert("RGB")
        chart = chart.resize((figure_width, figure_height))

    temp_img = Image.new("RGB", (width, 4000), "white")
    temp_draw = ImageDraw.Draw(temp_img)

    y = padding

    if include_title:
        y = draw_wrapped_text(
            temp_draw,
            title,
            padding,
            y,
            title_font,
            width - 2 * padding,
            line_spacing=14,
        )
        y += section_gap

    if include_purpose:
        temp_draw.text(
            (padding, y),
            "What this figure shows",
            font=heading_font,
            fill="black",
        )
        y += heading_font.size + 15

        y = draw_wrapped_text(
            temp_draw,
            purpose,
            padding,
            y,
            purpose_font,
            width - 2 * padding,
            line_spacing=12,
        )
        y += section_gap

    if include_figure and chart is not None:
        y += figure_height + section_gap

    if include_finding:
        temp_draw.text(
            (padding, y),
            "Key Findings / Why This Figure Is Important",
            font=heading_font,
            fill="black",
        )
        y += heading_font.size + 15

        y = draw_wrapped_text(
            temp_draw,
            finding,
            padding,
            y,
            finding_font,
            width - 2 * padding,
            line_spacing=12,
        )
        y += section_gap

    final_height = max(y + padding, 300)

    final_img = Image.new("RGB", (width, final_height), "white")
    final_draw = ImageDraw.Draw(final_img)

    y = padding

    if include_title:
        y = draw_wrapped_text(
            final_draw,
            title,
            padding,
            y,
            title_font,
            width - 2 * padding,
            line_spacing=14,
        )
        y += section_gap

    if include_purpose:
        final_draw.text(
            (padding, y),
            "What this figure shows",
            font=heading_font,
            fill="black",
        )
        y += heading_font.size + 15

        y = draw_wrapped_text(
            final_draw,
            purpose,
            padding,
            y,
            purpose_font,
            width - 2 * padding,
            line_spacing=12,
        )
        y += section_gap

    if include_figure and chart is not None:
        final_img.paste(chart, (padding, y))
        y += figure_height + section_gap

    if include_finding:
        final_draw.text(
            (padding, y),
            "Key Findings / Why This Figure Is Important",
            font=heading_font,
            fill="black",
        )
        y += heading_font.size + 15

        draw_wrapped_text(
            final_draw,
            finding,
            padding,
            y,
            finding_font,
            width - 2 * padding,
            line_spacing=12,
        )

    output = BytesIO()
    final_img.save(output, format="JPEG", quality=95)
    output.seek(0)
    return output


def download_settings(title, fig, purpose, finding):
    with st.expander("Customize Download", expanded=False):
        st.write("Choose what you want included in the downloaded JPG.")

        col1, col2 = st.columns(2)

        with col1:
            include_title = st.checkbox("Include title", value=True)
            include_figure = st.checkbox("Include figure", value=True)
            include_purpose = st.checkbox("Include what this figure shows", value=False)
            include_finding = st.checkbox("Include key findings", value=False)

        with col2:
            title_size = st.slider("Title size", 24, 90, 60)
            purpose_size = st.slider("Description size", 16, 45, 24)
            finding_size = st.slider("Key findings size", 16, 45, 24)

        col3, col4 = st.columns(2)

        with col3:
            figure_width = st.slider("Figure width", 1000, 2200, 1600, step=100)

        with col4:
            figure_height = st.slider("Figure height", 600, 1400, 950, step=50)

        try:
           jpg = create_custom_jpg(
    fig=fig,
    title=title,
    purpose=purpose,
    finding=finding,
    include_title=include_title,
    include_figure=include_figure,
    include_purpose=include_purpose,
    include_finding=include_finding,
    title_size=title_size,
    purpose_size=purpose_size,
    finding_size=finding_size,
    figure_width=figure_width,
    figure_height=figure_height,
)

st.markdown("### Preview")

preview_img = Image.open(jpg)

st.image(
    preview_img,
    use_container_width=True
)

jpg.seek(0)

st.download_button(
    label="Download JPG",
    data=jpg,
    file_name=title.replace(" ", "_").replace("/", "_") + ".jpg",
    mime="image/jpeg",
)

        except Exception as e:
            st.error("JPG download failed. Check that kaleido==0.2.1 and pillow are in requirements.txt.")
            st.caption(str(e))


def show_figure(title, fig, purpose, finding):
    st.markdown(
        f"<h1 style='text-align:center; font-size:48px;'>{title}</h1>",
        unsafe_allow_html=True,
    )

    st.markdown("### What this figure shows")
    st.write(purpose)

    st.markdown("### Key Findings / Why This Figure Is Important")
    st.write(finding)

    fig = style_figure(fig)
    st.plotly_chart(fig, use_container_width=True)

    download_settings(title, fig, purpose, finding)


# -----------------------------
# Figure selector
# -----------------------------
figure_choice = st.selectbox(
    "Choose a figure",
    [
        "1. Average Surface Temperature Bar Chart",
        "2. Surface Temperature by Time of Day",
        "3. Temperature Spread by Surface",
    ],
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
            "surface_temp": "Average Surface Temperature (°F)",
        },
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
            "surface": "Surface Type",
        },
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
            "surface_temp": "Surface Temperature (°F)",
        },
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
