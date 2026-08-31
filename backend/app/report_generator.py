from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

import matplotlib.pyplot as plt

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_PATH = BASE_DIR / "data.json"

# Fallback if you previously used report_data.json
if not DATA_PATH.exists():
    DATA_PATH = BASE_DIR / "report_data.json"

ASSETS_DIR = BASE_DIR / "report_assets"
OUTPUT_DIR = BASE_DIR / "generated_reports"

LOGO_PATH = ASSETS_DIR / "logo.png"
SATELLITE_PATH = ASSETS_DIR / "satellite.png"
SPILL_MASK_PATH = ASSETS_DIR / "spill_mask.png"
VESSEL_TRACKS_PATH = ASSETS_DIR / "vessel_tracks.png"
DRIFT_HINDCAST_PATH = ASSETS_DIR / "drift_hindcast.png"

OUTPUT_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)


# ============================================================
# PAGE / COLORS
# ============================================================

PAGE_WIDTH, PAGE_HEIGHT = A4

MARGIN = 34

NAVY = HexColor("#10212D")
NAVY_2 = HexColor("#152B3A")
BLUE = HexColor("#4B9ED0")
BLUE_LIGHT = HexColor("#DCEAF3")

TEXT = HexColor("#263846")
TEXT_MUTED = HexColor("#61717D")

BORDER = HexColor("#C7D0D6")
ROW_BG = HexColor("#F3F5F6")
ROW_ALT = HexColor("#E9EEF1")

WHITE = HexColor("#FFFFFF")

RED = HexColor("#C94B43")
GREEN = HexColor("#3C7A5B")
ORANGE = HexColor("#B87524")


# ============================================================
# DATA
# ============================================================


def load_data() -> dict:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"\nData file not found:\n{DATA_PATH}\nCreate backend/app/data.json first."
        )

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# GENERATED VISUALIZATIONS
# ============================================================


def create_vessel_tracks_image(output_path: Path):
    """
    Creates a clean AIS vessel track visualization.
    """

    fig, ax = plt.subplots(figsize=(12, 7), dpi=160)

    fig.patch.set_facecolor("#10212D")
    ax.set_facecolor("#10212D")

    # --------------------------------------------------------
    # Fake coastline
    # --------------------------------------------------------

    coast_x = [82.98, 83.05, 83.08, 83.04, 83.12, 83.16, 83.10, 83.20]

    coast_y = [17.20, 17.28, 17.42, 17.55, 17.66, 17.78, 17.92, 18.02]

    ax.fill_between(coast_x, coast_y, 18.3, color="#334743", alpha=0.9)

    # --------------------------------------------------------
    # MV OCEAN STAR
    # --------------------------------------------------------

    ocean_x = [83.45, 83.48, 83.52, 83.56, 83.61, 83.67, 83.72, 83.78]

    ocean_y = [17.48, 17.56, 17.62, 17.70, 17.75, 17.82, 17.87, 17.87]

    ax.plot(ocean_x, ocean_y, color="#F05A4F", linewidth=2.5, label="MV OCEAN STAR")

    # --------------------------------------------------------
    # SEA VOYAGER
    # --------------------------------------------------------

    sea_x = [83.55, 83.60, 83.66, 83.72, 83.78, 83.84, 83.90]

    sea_y = [17.66, 17.73, 17.79, 17.86, 17.94, 18.01, 18.08]

    ax.plot(sea_x, sea_y, color="#56A8D8", linewidth=2.2, label="SEA VOYAGER")

    # --------------------------------------------------------
    # BLUE HORIZON
    # --------------------------------------------------------

    blue_x = [83.40, 83.48, 83.56, 83.64, 83.73, 83.82, 83.92]

    blue_y = [17.43, 17.40, 17.39, 17.41, 17.45, 17.50, 17.55]

    ax.plot(blue_x, blue_y, color="#65A877", linewidth=2, label="BLUE HORIZON")

    # --------------------------------------------------------
    # Spill location
    # --------------------------------------------------------

    spill_x = 83.45
    spill_y = 17.48

    ax.scatter(
        spill_x,
        spill_y,
        s=80,
        color="#F05A4F",
        edgecolors="white",
        linewidth=1.5,
        zorder=10,
    )

    ax.annotate(
        "SPILL\nLOCATION",
        xy=(spill_x, spill_y),
        xytext=(spill_x + 0.02, spill_y - 0.13),
        color="#F05A4F",
        fontsize=9,
        fontweight="bold",
    )

    # --------------------------------------------------------
    # Styling
    # --------------------------------------------------------

    ax.set_xlim(82.95, 84.05)
    ax.set_ylim(17.15, 18.15)

    ax.grid(color="#334A59", linewidth=0.8, alpha=0.7)

    for spine in ax.spines.values():
        spine.set_color("#40525E")

    ax.tick_params(colors="#8EA1AD", labelsize=8)

    ax.set_xlabel("Longitude", color="#8EA1AD", fontsize=8)
    ax.set_ylabel("Latitude", color="#8EA1AD", fontsize=8)

    legend = ax.legend(
        loc="upper left",
        facecolor="#0D1B26",
        edgecolor="#304350",
        labelcolor="white",
        fontsize=8,
        framealpha=1,
        borderpad=1,
    )

    for text in legend.get_texts():
        text.set_color("#DDE6EB")

    plt.tight_layout()

    fig.savefig(output_path, bbox_inches="tight", facecolor=fig.get_facecolor())

    plt.close(fig)


def create_drift_hindcast_image(output_path: Path):
    """
    Creates estimated origin / backward drift visualization.
    """

    fig, ax = plt.subplots(figsize=(12, 6), dpi=160)

    fig.patch.set_facecolor("#F3F5F6")
    ax.set_facecolor("#F3F5F6")

    # Grid
    ax.grid(color="#CBD4DA", linewidth=0.8, alpha=0.8)

    # --------------------------------------------------------
    # Hindcast path
    # --------------------------------------------------------

    x = [83.42, 83.45, 83.47, 83.49, 83.55, 83.61, 83.68, 83.76, 83.84, 83.92, 84.00]

    y = [17.25, 17.32, 17.44, 17.63, 17.69, 17.72, 17.79, 17.84, 17.89, 17.94, 18.00]

    ax.plot(
        x,
        y,
        color="#315A7C",
        linewidth=2.2,
        linestyle="--",
        marker="o",
        markersize=3.5,
        label="Backward Drift Path",
    )

    # Estimated origin
    ax.scatter(x[0], y[0], s=80, color="#315A7C", zorder=5)

    ax.annotate(
        "ESTIMATED\nORIGIN",
        xy=(x[0], y[0]),
        xytext=(x[0] - 0.14, y[0] + 0.02),
        fontsize=8,
        color="#315A7C",
        fontweight="bold",
    )

    # Spill location
    ax.scatter(x[-1], y[-1], s=85, color="#C94B43", zorder=5)

    ax.annotate(
        "SPILL\nLOCATION",
        xy=(x[-1], y[-1]),
        xytext=(x[-1] + 0.02, y[-1] + 0.02),
        fontsize=8,
        color="#C94B43",
        fontweight="bold",
    )

    # --------------------------------------------------------
    # Styling
    # --------------------------------------------------------

    ax.set_xlim(83.2, 84.2)
    ax.set_ylim(17.05, 18.15)

    ax.tick_params(colors="#61717D", labelsize=8)

    for spine in ax.spines.values():
        spine.set_color("#C7D0D6")

    ax.set_xlabel("Longitude", color="#61717D", fontsize=8)
    ax.set_ylabel("Latitude", color="#61717D", fontsize=8)

    plt.tight_layout()

    fig.savefig(output_path, bbox_inches="tight", facecolor=fig.get_facecolor())

    plt.close(fig)


# ============================================================
# DRAWING HELPERS
# ============================================================


def draw_image(
    c: canvas.Canvas,
    path: Path,
    x: float,
    y: float,
    width: float,
    height: float,
    title: str | None = None,
):
    """
    Draw image preserving aspect ratio.
    """

    if title:
        title_h = 18

        c.setFillColor(NAVY)
        c.rect(x, y + height - title_h, width, title_h, fill=1, stroke=0)

        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(x + 9, y + height - 12, title.upper())

        image_y = y
        image_h = height - title_h

    else:
        image_y = y
        image_h = height

    if path.exists():
        try:
            image = ImageReader(str(path))

            iw, ih = image.getSize()

            ratio = min(width / iw, image_h / ih)

            draw_w = iw * ratio
            draw_h = ih * ratio

            draw_x = x + (width - draw_w) / 2
            draw_y = image_y + (image_h - draw_h) / 2

            c.drawImage(
                image,
                draw_x,
                draw_y,
                draw_w,
                draw_h,
                preserveAspectRatio=True,
                mask="auto",
            )

        except Exception:
            c.setFillColor(HexColor("#E5E8EA"))
            c.rect(x, image_y, width, image_h, fill=1, stroke=0)

    else:
        # Safe placeholder if image doesn't exist
        c.setFillColor(HexColor("#E5E8EA"))
        c.rect(x, image_y, width, image_h, fill=1, stroke=0)

        c.setFillColor(TEXT_MUTED)
        c.setFont("Helvetica", 8)

        c.drawCentredString(x + width / 2, image_y + image_h / 2, "IMAGE NOT AVAILABLE")

    c.setStrokeColor(BORDER)
    c.rect(x, y, width, height, fill=0, stroke=1)


def draw_section_title(
    c: canvas.Canvas,
    number: str,
    title: str,
    x: float,
    y: float,
):
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", 13)

    c.drawString(x, y, number)

    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 13)

    c.drawString(x + 28, y, title.upper())


def draw_kv_table(
    c: canvas.Canvas,
    rows: list[tuple[str, str]],
    x: float,
    y_top: float,
    width: float,
    label_width: float | None = None,
    row_height: float = 23,
    font_size: float = 7.5,
    highlight: dict | None = None,
):
    """
    Draw key/value table.

    y_top = TOP of table.
    """

    if label_width is None:
        label_width = width * 0.43

    highlight = highlight or {}

    total_height = len(rows) * row_height

    y = y_top - row_height

    for index, (label, value) in enumerate(rows):
        bg = ROW_BG if index % 2 == 0 else WHITE

        # Label background
        c.setFillColor(ROW_ALT)
        c.rect(x, y, label_width, row_height, fill=1, stroke=0)

        # Value background
        c.setFillColor(bg)
        c.rect(x + label_width, y, width - label_width, row_height, fill=1, stroke=0)

        # Borders
        c.setStrokeColor(BORDER)
        c.rect(x, y, width, row_height, fill=0, stroke=1)

        c.line(x + label_width, y, x + label_width, y + row_height)

        # Label
        c.setFillColor(TEXT)
        c.setFont("Helvetica-Bold", font_size)

        c.drawString(x + 7, y + row_height / 2 - 2.5, str(label))

        # Value
        value_color = highlight.get(label, TEXT)

        c.setFillColor(value_color)
        c.setFont("Helvetica", font_size)

        c.drawString(x + label_width + 7, y + row_height / 2 - 2.5, str(value))

        y -= row_height

    return total_height


def draw_vessel_table(
    c: canvas.Canvas,
    vessels: list[dict],
    x: float,
    y_top: float,
    width: float,
):
    headers = [
        "RANK",
        "VESSEL NAME",
        "IMO NUMBER",
        "VESSEL TYPE",
        "FLAG",
        "CLOSEST APPROACH",
        "CORRELATION SCORE",
    ]

    proportions = [
        0.07,
        0.18,
        0.14,
        0.14,
        0.12,
        0.16,
        0.19,
    ]

    col_widths = [width * p for p in proportions]

    header_h = 24
    row_h = 25

    # Header
    current_x = x

    for i, header in enumerate(headers):
        w = col_widths[i]

        c.setFillColor(NAVY)
        c.rect(current_x, y_top - header_h, w, header_h, fill=1, stroke=0)

        c.setStrokeColor(HexColor("#52636D"))
        c.rect(current_x, y_top - header_h, w, header_h, fill=0, stroke=1)

        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 6.4)

        c.drawCentredString(current_x + w / 2, y_top - 15, header)

        current_x += w

    # Rows
    y = y_top - header_h

    for row_index, vessel in enumerate(vessels):
        bg = WHITE if row_index % 2 == 0 else ROW_BG

        values = [
            vessel.get("rank", ""),
            vessel.get("name", ""),
            vessel.get("imo", ""),
            vessel.get("type", ""),
            vessel.get("flag", ""),
            vessel.get("closest_approach", ""),
            vessel.get("correlation", ""),
        ]

        current_x = x

        for col_index, value in enumerate(values):
            w = col_widths[col_index]

            c.setFillColor(bg)
            c.rect(current_x, y - row_h, w, row_h, fill=1, stroke=0)

            c.setStrokeColor(BORDER)
            c.rect(current_x, y - row_h, w, row_h, fill=0, stroke=1)

            # Highlight primary vessel
            if row_index == 0 and col_index in [0, 1, 6]:
                c.setFillColor(RED)
                c.setFont("Helvetica-Bold", 7)
            else:
                c.setFillColor(TEXT)
                c.setFont("Helvetica", 7)

            c.drawCentredString(current_x + w / 2, y - 16, str(value))

            current_x += w

        y -= row_h

    return header_h + len(vessels) * row_h


# ============================================================
# HEADER / FOOTER
# ============================================================


def draw_header(
    c: canvas.Canvas,
    generated_at: str,
):
    """
    Professional minimal header.
    """

    header_y = PAGE_HEIGHT - 42

    # Logo
    logo_size = 44

    if LOGO_PATH.exists():
        try:
            c.drawImage(
                str(LOGO_PATH),
                MARGIN,
                header_y - logo_size,
                logo_size,
                logo_size,
                preserveAspectRatio=True,
                mask="auto",
            )

        except Exception:
            pass

    else:
        # Fallback logo circle
        c.setStrokeColor(BLUE)
        c.setLineWidth(1.3)

        c.circle(MARGIN + 22, header_y - 22, 20, stroke=1, fill=0)

    # Brand
    brand_x = MARGIN + 58

    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 14)

    c.drawString(brand_x, header_y - 17, "OCEAN")

    c.setFillColor(HexColor("#587087"))

    c.drawString(brand_x + 73, header_y - 17, "FORENSICS")

    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica-Bold", 6.5)

    c.drawString(brand_x, header_y - 36, "AI-ASSISTED MARITIME INTELLIGENCE")

    # Report title
    right_x = PAGE_WIDTH - MARGIN

    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 9.5)

    title = "MARITIME INCIDENT INTELLIGENCE REPORT"

    c.drawRightString(right_x, header_y - 17, title)

    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", 7.5)

    c.drawRightString(right_x, header_y - 36, generated_at)

    # Divider
    line_y = header_y - 58

    c.setStrokeColor(BORDER)
    c.setLineWidth(0.8)

    c.line(MARGIN, line_y, PAGE_WIDTH - MARGIN, line_y)

    return line_y


def draw_footer(
    c: canvas.Canvas,
    page_number: int,
):
    footer_y = 25

    c.setStrokeColor(BORDER)
    c.setLineWidth(0.6)

    c.line(MARGIN, footer_y + 13, PAGE_WIDTH - MARGIN, footer_y + 13)

    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", 6.5)

    c.drawString(
        MARGIN,
        footer_y,
        "AI-generated intelligence report. Validate with additional data and expert analysis.",
    )

    c.drawRightString(
        PAGE_WIDTH - MARGIN, footer_y, f"OCEAN FORENSICS | PAGE {page_number}"
    )


# ============================================================
# REPORT METADATA
# ============================================================


def draw_metadata(
    c: canvas.Canvas,
    data: dict,
    y_top: float,
):
    x = MARGIN
    width = PAGE_WIDTH - 2 * MARGIN

    height = 46

    columns = [
        ("REPORT ID", data.get("report_id", "—")),
        ("GENERATED", data.get("generated_at", "—")),
        ("STATUS", data.get("status", "—")),
        ("CLASSIFICATION", data.get("classification", "—")),
    ]

    col_w = width / 4

    for i, (label, value) in enumerate(columns):
        cx = x + i * col_w

        c.setFillColor(ROW_BG)
        c.rect(cx, y_top - height, col_w, height, fill=1, stroke=0)

        c.setStrokeColor(BORDER)
        c.rect(cx, y_top - height, col_w, height, fill=0, stroke=1)

        c.setFillColor(TEXT_MUTED)
        c.setFont("Helvetica-Bold", 6.8)

        c.drawString(cx + 9, y_top - 16, label)

        c.setFillColor(TEXT)
        c.setFont("Helvetica-Bold", 8.5)

        c.drawString(cx + 9, y_top - 31, str(value))

    return height


# ============================================================
# PAGE 1
# ============================================================


def draw_page_one(
    c: canvas.Canvas,
    data: dict,
):
    header_bottom = draw_header(c, data.get("generated_at", ""))

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    metadata_top = header_bottom - 24

    draw_metadata(c, data, metadata_top)

    # --------------------------------------------------------
    # 01 Incident Overview
    # --------------------------------------------------------

    section_y = metadata_top - 72

    draw_section_title(c, "01", "Incident Overview", MARGIN, section_y)

    incident = data.get("incident", {})

    rows = [
        ("Incident Type", incident.get("incident_type", "—")),
        ("Detection Status", incident.get("detection_status", "—")),
        ("Severity", incident.get("severity", "—")),
        ("Confidence Score", incident.get("confidence_score", "—")),
        ("Coordinates", incident.get("coordinates", "—")),
        ("Region", incident.get("region", "—")),
        ("Detection Time", incident.get("detection_time", "—")),
        ("Reference Time (UTC)", incident.get("reference_time", "—")),
    ]

    table_top = section_y - 12

    table_width = PAGE_WIDTH - 2 * MARGIN

    draw_kv_table(
        c,
        rows,
        MARGIN,
        table_top,
        table_width,
        row_height=20,
        font_size=7,
        highlight={
            "Detection Status": GREEN,
            "Severity": RED,
        },
    )

    # --------------------------------------------------------
    # Satellite image
    # --------------------------------------------------------

    image_y = 250
    image_h = 170

    draw_image(
        c,
        SATELLITE_PATH,
        MARGIN,
        image_y,
        PAGE_WIDTH - 2 * MARGIN,
        image_h,
        "Processed Satellite Observation",
    )

    # --------------------------------------------------------
    # 02 Satellite Analysis
    # --------------------------------------------------------

    section_y = 225

    draw_section_title(c, "02", "Satellite Analysis", MARGIN, section_y)

    satellite = data.get("satellite", {})

    rows = [
        ("Satellite Source", satellite.get("source", "—")),
        ("Acquisition Date", satellite.get("acquisition_date", "—")),
        ("Polarization", satellite.get("polarization", "—")),
        ("Orbit Direction", satellite.get("orbit_direction", "—")),
        ("Estimated Spill Area", satellite.get("estimated_spill_area", "—")),
        ("Spill Length", satellite.get("spill_length", "—")),
        ("Spill Width (Avg.)", satellite.get("spill_width", "—")),
        ("Detection Confidence", satellite.get("detection_confidence", "—")),
        ("Sea State (Estimated)", satellite.get("sea_state", "—")),
    ]

    draw_kv_table(
        c,
        rows,
        MARGIN,
        section_y - 12,
        PAGE_WIDTH - 2 * MARGIN,
        row_height=16,
        font_size=6.7,
    )

    draw_footer(c, 1)
    c.showPage()


# ============================================================
# PAGE 2
# ============================================================


def draw_page_two(
    c: canvas.Canvas,
    data: dict,
):
    header_bottom = draw_header(c, data.get("generated_at", ""))

    # --------------------------------------------------------
    # Spill Mask
    # --------------------------------------------------------

    image_top = header_bottom - 30
    image_h = 220
    image_y = image_top - image_h

    draw_image(
        c,
        SPILL_MASK_PATH,
        MARGIN,
        image_y,
        PAGE_WIDTH - 2 * MARGIN,
        image_h,
        "AI-Generated Spill Segmentation Mask",
    )

    # --------------------------------------------------------
    # 03 Spill Characteristics
    # --------------------------------------------------------

    section_y = image_y - 30

    draw_section_title(c, "03", "Spill Characteristics", MARGIN, section_y)

    spill = data.get("spill_characteristics", {})

    rows = [
        ("Oil Type (Predicted)", spill.get("oil_type", "—")),
        ("Appearance", spill.get("appearance", "—")),
        ("Spread Direction", spill.get("spread_direction", "—")),
        ("Weather Condition", spill.get("weather_condition", "—")),
        ("Wind Speed", spill.get("wind_speed", "—")),
        ("Wind Direction", spill.get("wind_direction", "—")),
        ("Surface Current", spill.get("surface_current", "—")),
        ("Tidal Condition", spill.get("tidal_condition", "—")),
        ("Estimated Drift", spill.get("estimated_drift", "—")),
    ]

    table_h = draw_kv_table(
        c,
        rows,
        MARGIN,
        section_y - 12,
        PAGE_WIDTH - 2 * MARGIN,
        row_height=17,
        font_size=6.8,
    )

    # --------------------------------------------------------
    # 04 Vessel Correlation
    # --------------------------------------------------------

    vessel_section_y = section_y - table_h - 45

    draw_section_title(
        c, "04", "Vessel Correlation (AIS Analysis)", MARGIN, vessel_section_y
    )

    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", 7)

    c.drawString(
        MARGIN,
        vessel_section_y - 14,
        "AIS vessel tracks were analyzed against the estimated spill origin using spatial and temporal correlation.",
    )

    draw_vessel_table(
        c,
        data.get("vessels", []),
        MARGIN,
        vessel_section_y - 26,
        PAGE_WIDTH - 2 * MARGIN,
    )

    draw_footer(c, 2)
    c.showPage()


# ============================================================
# PAGE 3
# ============================================================


def draw_page_three(
    c: canvas.Canvas,
    data: dict,
):
    header_bottom = draw_header(c, data.get("generated_at", ""))

    # --------------------------------------------------------
    # 05 Vessel Tracks
    # --------------------------------------------------------

    section_y = header_bottom - 32

    draw_section_title(c, "05", "Vessel Tracks & Spill Location", MARGIN, section_y)

    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", 7)

    c.drawString(
        MARGIN,
        section_y - 15,
        "AIS vessel trajectories within the investigation area at the estimated detection timeframe.",
    )

    image_h = 235
    image_y = section_y - 270

    draw_image(c, VESSEL_TRACKS_PATH, MARGIN, image_y, PAGE_WIDTH - 2 * MARGIN, image_h)

    # --------------------------------------------------------
    # 06 Drift Hindcast
    # --------------------------------------------------------

    section_y = image_y - 35

    draw_section_title(c, "06", "Drift Hindcast (Estimated Origin)", MARGIN, section_y)

    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", 7)

    c.drawString(
        MARGIN,
        section_y - 15,
        "Backward drift simulation was performed to estimate the probable origin of the oil spill based on environmental conditions.",
    )

    drift = data.get("drift", {})

    rows = [
        ("Simulation Duration", drift.get("simulation_duration", "—")),
        ("Time Step", drift.get("time_step", "—")),
        ("Model", drift.get("model", "—")),
    ]

    table_top = section_y - 28

    draw_kv_table(
        c, rows, MARGIN, table_top, PAGE_WIDTH - 2 * MARGIN, row_height=18, font_size=7
    )

    graph_y = table_top - 54 - 190

    draw_image(c, DRIFT_HINDCAST_PATH, MARGIN, graph_y, PAGE_WIDTH - 2 * MARGIN, 190)

    draw_footer(c, 3)
    c.showPage()


# ============================================================
# PAGE 4
# ============================================================


def draw_page_four(
    c: canvas.Canvas,
    data: dict,
):
    header_bottom = draw_header(c, data.get("generated_at", ""))

    section_y = header_bottom - 38

    draw_section_title(c, "07", "Investigation Summary", MARGIN, section_y)

    # --------------------------------------------------------
    # Summary text
    # --------------------------------------------------------

    summary_lines = [
        "A marine surface anomaly consistent with an oil spill was identified through satellite SAR imagery analysis.",
        "The detected anomaly was subsequently processed to estimate spill geometry and probable origin.",
        "",
        "AIS vessel tracks within the investigation area were analyzed using spatial and temporal correlation.",
        "MV OCEAN STAR demonstrated the highest correlation with the detected incident and is the primary vessel of interest.",
        "",
        "This report is generated automatically by the Ocean Forensics maritime intelligence platform and should support,",
        "not replace, expert investigation and verification.",
    ]

    y = section_y - 28

    c.setFillColor(TEXT)
    c.setFont("Helvetica", 8)

    for line in summary_lines:
        if line == "":
            y -= 12
            continue

        c.drawString(MARGIN, y, line)

        y -= 16

    # --------------------------------------------------------
    # Final result table
    # --------------------------------------------------------

    summary = data.get("summary", {})

    table_y = y - 22

    rows = [
        ("Primary Vessel of Interest", summary.get("primary_vessel", "—")),
        ("Correlation Score", summary.get("correlation_score", "—")),
        ("Recommended Action", summary.get("recommended_action", "—")),
        ("Report Generated By", summary.get("generated_by", "—")),
    ]

    draw_kv_table(
        c,
        rows,
        MARGIN,
        table_y,
        PAGE_WIDTH - 2 * MARGIN,
        row_height=28,
        font_size=8,
        highlight={
            "Primary Vessel of Interest": RED,
            "Correlation Score": RED,
        },
    )

    # --------------------------------------------------------
    # Investigation conclusion box
    # --------------------------------------------------------

    # Height of the summary table above:
    # 4 rows × 28 points each
    summary_table_height = len(rows) * 28

    # Keep a clean gap between the table and assessment
    assessment_gap = 18

    # Assessment card dimensions
    assessment_height = 82

    # table_y is the TOP of the summary table.
    # Calculate the assessment position from the actual BOTTOM
    # of that table instead of using a hardcoded value.
    box_y = table_y - summary_table_height - assessment_gap - assessment_height

    # Subtle background
    c.setFillColor(HexColor("#F4F7F8"))
    c.roundRect(
        MARGIN,
        box_y,
        PAGE_WIDTH - 2 * MARGIN,
        assessment_height,
        5,
        fill=1,
        stroke=0,
    )

    # Title
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 10)

    c.drawString(
        MARGIN + 16,
        box_y + assessment_height - 24,
        "INVESTIGATION ASSESSMENT",
    )

    # Assessment text
    c.setFillColor(TEXT_MUTED)
    c.setFont("Helvetica", 8)

    c.drawString(
        MARGIN + 16,
        box_y + assessment_height - 44,
        "Current evidence indicates a high-confidence spatial and temporal correlation with the identified vessel.",
    )

    c.drawString(
        MARGIN + 16,
        box_y + assessment_height - 60,
        "Further investigation and verification using additional AIS and environmental datasets is recommended.",
    )


# ============================================================
# MAIN GENERATOR
# ============================================================


def generate_report():

    print("\nGenerating Ocean Forensics report...")

    data = load_data()

    # --------------------------------------------------------
    # Generate visualizations
    # --------------------------------------------------------

    print("Creating vessel tracks visualization...")

    create_vessel_tracks_image(VESSEL_TRACKS_PATH)

    print("Creating drift hindcast visualization...")

    create_drift_hindcast_image(DRIFT_HINDCAST_PATH)

    # --------------------------------------------------------
    # Output path
    # --------------------------------------------------------

    report_id = data.get("report_id", "OCEAN_FORENSICS_REPORT")

    safe_report_id = report_id.replace("/", "_").replace("\\", "_").replace(" ", "_")

    output_path = OUTPUT_DIR / f"{safe_report_id}.pdf"

    # --------------------------------------------------------
    # Create PDF
    # --------------------------------------------------------

    c = canvas.Canvas(str(output_path), pagesize=A4)

    c.setTitle("Ocean Forensics - Maritime Incident Intelligence Report")

    c.setAuthor("Ocean Forensics AI")

    # Explicit page layouts.
    # This is intentional — no automatic flow/layout engine.

    draw_page_one(c, data)
    draw_page_two(c, data)
    draw_page_three(c, data)
    draw_page_four(c, data)

    c.save()

    print("\nReport generated successfully.")
    print(f"Output: {output_path}\n")

    return output_path


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":
    generate_report()
