from __future__ import annotations

import base64
import csv
import io
import json
import math
from typing import Any

import streamlit as st
from PIL import Image


st.set_page_config(page_title="Plot Digitizer", page_icon="📈", layout="wide")

PALETTE = ["#e4572e", "#168aad", "#52b788", "#9b5de5", "#f4a261", "#d63384"]
COMPONENT_HTML = """
<div class="digitizer-shell">
  <div class="digitizer-toolbar">
    <span class="digitizer-hint" id="hint"></span>
    <span class="digitizer-size" id="size"></span>
  </div>
  <div class="digitizer-viewport" id="viewport">
    <canvas id="plot"></canvas>
    <div class="digitizer-lens" id="lens" hidden>
      <canvas id="lens-canvas" width="174" height="174"></canvas>
      <div class="digitizer-lens-label" id="lens-label"></div>
    </div>
  </div>
</div>
"""
COMPONENT_CSS = """
.digitizer-shell { font-family: var(--st-font, sans-serif); }
.digitizer-toolbar { display:flex; justify-content:space-between; gap:1rem; padding:0.6rem 0.8rem; color:var(--st-text-color); background:var(--st-secondary-background-color); border:1px solid var(--st-border-color); border-bottom:0; border-radius:0.7rem 0.7rem 0 0; font-size:0.85rem; }
.digitizer-viewport { height:580px; overflow:auto; position:relative; border:1px solid var(--st-border-color); border-radius:0 0 0.7rem 0.7rem; background-color:#e9ecef; background-image:linear-gradient(45deg,#dfe3e7 25%,transparent 25%),linear-gradient(-45deg,#dfe3e7 25%,transparent 25%),linear-gradient(45deg,transparent 75%,#dfe3e7 75%),linear-gradient(-45deg,transparent 75%,#dfe3e7 75%); background-size:20px 20px; background-position:0 0,0 10px,10px -10px,-10px 0; }
canvas { display:block; max-width:none; cursor:crosshair; }
.digitizer-lens { position:absolute; z-index:2; width:174px; height:198px; box-sizing:border-box; padding:5px; border:1px solid #344054; border-radius:10px; background:#fff; box-shadow:0 5px 20px #0005; pointer-events:none; }
.digitizer-lens canvas { width:162px; height:162px; border-radius:5px; cursor:default; }
.digitizer-lens-label { color:#344054; font:11px/22px sans-serif; text-align:center; white-space:nowrap; }
"""
COMPONENT_JS = """
export default function(component) {
  const {data, parentElement, setTriggerValue} = component;
  const canvas = parentElement.querySelector('#plot');
  const viewport = parentElement.querySelector('#viewport');
  const hint = parentElement.querySelector('#hint');
  const size = parentElement.querySelector('#size');
  const lens = parentElement.querySelector('#lens');
  const lensCanvas = parentElement.querySelector('#lens-canvas');
  const lensLabel = parentElement.querySelector('#lens-label');
  if (!canvas || !viewport || !lens || !lensCanvas) return;
  const ctx = canvas.getContext('2d');
  const lensCtx = lensCanvas.getContext('2d');
  const img = new Image();
  img.onload = () => {
    canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
    canvas.style.width = `${img.naturalWidth * data.zoom}px`;
    canvas.style.height = `${img.naturalHeight * data.zoom}px`;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    for (const marker of (data.markers || [])) {
      const x = marker.x * canvas.width, y = marker.y * canvas.height;
      ctx.beginPath(); ctx.arc(x, y, Math.max(5, 4 / data.zoom), 0, Math.PI * 2);
      ctx.fillStyle = marker.color; ctx.fill();
      ctx.lineWidth = Math.max(2, 2 / data.zoom); ctx.strokeStyle = '#fff'; ctx.stroke();
      if (marker.label) {
        ctx.font = `bold ${Math.max(13, 13 / data.zoom)}px sans-serif`;
        ctx.lineWidth = Math.max(3, 3 / data.zoom); ctx.strokeStyle = '#fff';
        ctx.strokeText(marker.label, x + 8, y - 8); ctx.fillStyle = marker.color; ctx.fillText(marker.label, x + 8, y - 8);
      }
    }
    size.textContent = `${img.naturalWidth} × ${img.naturalHeight}px`;
  };
  img.src = data.image;
  hint.textContent = `${data.hint || 'Click the image to add a point'} · Hover for a 3× magnifier`;
  canvas.onmouseenter = () => { lens.hidden = false; };
  canvas.onmouseleave = () => { lens.hidden = true; };
  canvas.onmousemove = (event) => {
    if (!img.complete || !img.naturalWidth) return;
    const rect = canvas.getBoundingClientRect();
    const viewportRect = viewport.getBoundingClientRect();
    const nx = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    const ny = Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height));
    const lensWidth = 174, lensHeight = 198, gap = 14;
    let left = event.clientX - viewportRect.left + viewport.scrollLeft + gap;
    let top = event.clientY - viewportRect.top + viewport.scrollTop + gap;
    if (left + lensWidth > viewport.scrollLeft + viewport.clientWidth) left -= lensWidth + gap * 2;
    if (top + lensHeight > viewport.scrollTop + viewport.clientHeight) top -= lensHeight + gap * 2;
    lens.style.left = `${Math.max(viewport.scrollLeft, left)}px`;
    lens.style.top = `${Math.max(viewport.scrollTop, top)}px`;
    const sourceSize = 162 / (data.zoom * 3);
    const sx = Math.max(0, Math.min(img.naturalWidth - sourceSize, nx * img.naturalWidth - sourceSize / 2));
    const sy = Math.max(0, Math.min(img.naturalHeight - sourceSize, ny * img.naturalHeight - sourceSize / 2));
    lensCtx.clearRect(0, 0, lensCanvas.width, lensCanvas.height);
    lensCtx.drawImage(img, sx, sy, sourceSize, sourceSize, 0, 0, lensCanvas.width, lensCanvas.height);
    lensCtx.strokeStyle = '#e4572e'; lensCtx.lineWidth = 1;
    lensCtx.beginPath(); lensCtx.moveTo(87, 68); lensCtx.lineTo(87, 106); lensCtx.moveTo(68, 87); lensCtx.lineTo(106, 87); lensCtx.stroke();
    if (lensLabel) lensLabel.textContent = `x ${nx.toFixed(4)}  ·  y ${ny.toFixed(4)}`;
  };
  canvas.onclick = (event) => {
    const rect = canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    setTriggerValue('clicked', {x, y, nonce: Date.now() + Math.random()});
  };
}
"""

_IMAGE_CANVAS = st.components.v2.component(
    "plot_digitizer_canvas", html=COMPONENT_HTML, css=COMPONENT_CSS, js=COMPONENT_JS
)


def to_data_url(image: Image.Image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def fresh_dataset(index: int) -> dict[str, Any]:
    return {"name": f"Dataset {index}", "color": PALETTE[(index - 1) % len(PALETTE)], "points": []}


def add_dataset_callback() -> None:
    st.session_state.datasets.append(fresh_dataset(len(st.session_state.datasets) + 1))
    st.session_state.active_dataset = len(st.session_state.datasets) - 1


def delete_active_dataset_callback() -> None:
    selected_index = st.session_state.active_dataset
    st.session_state.datasets.pop(selected_index)
    st.session_state.active_dataset = max(0, selected_index - 1)


def calibrated_value(point: dict[str, float], calibration: dict[str, Any], log_x: bool, log_y: bool) -> tuple[float, float]:
    ox, oy = calibration["origin"]["x"], calibration["origin"]["y"]
    xx, xy = calibration["xpoint"]["x"], calibration["xpoint"]["y"]
    yx, yy = calibration["ypoint"]["x"], calibration["ypoint"]["y"]
    dx, dy = point["x"] - ox, point["y"] - oy
    ax, ay = xx - ox, xy - oy
    bx, by = yx - ox, yy - oy
    determinant = ax * by - ay * bx
    if abs(determinant) < 1e-10:
        raise ValueError("Calibration points are too close together or collinear.")
    # Solve the image-space basis coordinates. The y image coordinate grows downward.
    u = (dx * by - dy * bx) / determinant
    v = (ax * dy - ay * dx) / determinant
    x0, xv, y0, yv = calibration["values"]
    if log_x:
        x0, xv = math.log10(x0), math.log10(xv)
    if log_y:
        y0, yv = math.log10(y0), math.log10(yv)
    tx = u * (xv - x0) + x0
    ty = v * (yv - y0) + y0
    if log_x:
        tx = 10 ** tx
    if log_y:
        ty = 10 ** ty
    return tx, ty


def image_position(x: float, y: float, calibration: dict[str, Any], log_x: bool, log_y: bool) -> dict[str, float]:
    ox, oy = calibration["origin"]["x"], calibration["origin"]["y"]
    xx, xy = calibration["xpoint"]["x"], calibration["xpoint"]["y"]
    yx, yy = calibration["ypoint"]["x"], calibration["ypoint"]["y"]
    x0, xv, y0, yv = calibration["values"]
    if log_x:
        x0, xv = math.log10(x0), math.log10(xv)
    if log_y:
        y0, yv = math.log10(y0), math.log10(yv)
    ux = (math.log10(x) if log_x else x) - x0
    vy = (math.log10(y) if log_y else y) - y0
    u = ux / (xv - x0)
    v = vy / (yv - y0)
    return {"x": ox + u * (xx - ox) + v * (yx - ox), "y": oy + u * (xy - oy) + v * (yy - oy)}


def wide_csv(datasets: list[dict[str, Any]], x_label: str, y_label: str, calibration: dict[str, Any] | None, log_x: bool, log_y: bool) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow([cell for dataset in datasets for cell in (dataset["name"], "")])
    writer.writerow([cell for _dataset in datasets for cell in (x_label, y_label)])
    converted: list[list[tuple[float, float]]] = []
    for dataset in datasets:
        values = []
        for point in dataset["points"]:
            if calibration:
                values.append(calibrated_value(point, calibration, log_x, log_y))
        converted.append(values)
    for row_index in range(max((len(points) for points in converted), default=0)):
        row: list[str | float] = []
        for points in converted:
            row.extend(points[row_index] if row_index < len(points) else ("", ""))
        writer.writerow(row)
    return output.getvalue().encode("utf-8-sig")


st.title("Plot digitizer")
st.write("Extract data points from a graph image, calibrate its axes, and download the results as CSV.")
uploaded = st.file_uploader("Upload a graph image", type=["png", "jpg", "jpeg", "gif", "tif", "tiff", "bmp", "webp"])

if "datasets" not in st.session_state:
    st.session_state.datasets = [fresh_dataset(1)]
if "calibration" not in st.session_state:
    st.session_state.calibration = None
if "image_id" not in st.session_state:
    st.session_state.image_id = None

if uploaded is not None:
    try:
        uploaded.seek(0)
        with Image.open(uploaded) as source:
            source.seek(0)
            image = source.convert("RGB")
        image_id = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.image_id != image_id:
            st.session_state.image_id = image_id
            st.session_state.datasets = [fresh_dataset(1)]
            st.session_state.calibration = None
        image_url = to_data_url(image)

        with st.sidebar:
            st.header("Axes and scale")
            x_label = st.text_input("X axis name", value="x")
            y_label = st.text_input("Y axis name", value="y")
            x_scale = st.selectbox("X axis scale", ["Linear", "Logarithmic"])
            y_scale = st.selectbox("Y axis scale", ["Linear", "Logarithmic"])
            log_x, log_y = x_scale == "Logarithmic", y_scale == "Logarithmic"
            st.caption("Log axes use base 10. For logarithmic calibration, enter positive values; calibration is performed in log space.")
            st.divider()
            calibration = st.session_state.calibration
            if calibration is None:
                st.subheader("Calibrate image")
                st.caption("Click the origin, then a known point on the x axis, then a known point on the y axis.")
                stage = len(st.session_state.get("calibration_clicks", []))
                prompts = ["Origin", "X-axis reference point", "Y-axis reference point"]
                st.info(f"Next image click: **{prompts[min(stage, 2)]}**")
                click_values = st.columns(2)
                x0 = click_values[0].number_input(f"{x_label} at origin", value=0.0, key="x_origin")
                xv = click_values[1].number_input(f"{x_label} at x reference", value=1.0, key="x_reference")
                yvals = st.columns(2)
                y0 = yvals[0].number_input(f"{y_label} at origin", value=0.0, key="y_origin")
                yv = yvals[1].number_input(f"{y_label} at y reference", value=1.0, key="y_reference")
                if log_x and (x0 <= 0 or xv <= 0):
                    st.warning("X-axis reference values must be positive for a logarithmic axis.")
                if log_y and (y0 <= 0 or yv <= 0):
                    st.warning("Y-axis reference values must be positive for a logarithmic axis.")
                if st.button("Reset calibration clicks", width="stretch"):
                    st.session_state.calibration_clicks = []
                    st.rerun()
            else:
                st.success("Axes calibrated")
                if st.button("Recalibrate axes", width="stretch"):
                    st.session_state.calibration = None
                    st.session_state.calibration_clicks = []
                    st.rerun()

            st.divider()
            st.header("Datasets")
            selected = st.selectbox("Active dataset", options=list(range(len(st.session_state.datasets))), format_func=lambda i: st.session_state.datasets[i]["name"], key="active_dataset")
            active = st.session_state.datasets[selected]
            active["name"] = st.text_input("Dataset name", value=active["name"], key=f"dataset_name_{selected}")
            active["color"] = st.color_picker("Point color", value=active["color"], key=f"dataset_color_{selected}")
            ds_cols = st.columns(2)
            ds_cols[0].button("Add dataset", icon=":material/add:", width="stretch", on_click=add_dataset_callback)
            ds_cols[1].button(
                "Delete",
                icon=":material/delete:",
                width="stretch",
                disabled=len(st.session_state.datasets) == 1,
                on_click=delete_active_dataset_callback,
            )
            if st.button("Undo last point", icon=":material/undo:", width="stretch", disabled=not active["points"]):
                active["points"].pop()
                st.rerun()

        zoom = st.slider("Image zoom", min_value=0.25, max_value=3.0, value=1.0, step=0.25)
        calibration_clicks = st.session_state.setdefault("calibration_clicks", [])
        markers = []
        for i, point in enumerate(calibration_clicks):
            markers.append({"x": point["x"], "y": point["y"], "color": "#222222", "label": ["O", "X", "Y"][i]})
        for i, dataset in enumerate(st.session_state.datasets):
            for point_index, point in enumerate(dataset["points"]):
                markers.append({"x": point["x"], "y": point["y"], "color": dataset["color"], "label": str(point_index + 1)})
        if st.session_state.calibration is None:
            hint = "Click calibration point 1 of 3" if len(calibration_clicks) == 0 else f"Click calibration point {len(calibration_clicks) + 1} of 3"
        else:
            hint = f"Click to add a point to {st.session_state.datasets[selected]['name']}"
        canvas_key = "digitizer_canvas"
        result = _IMAGE_CANVAS(
            key=canvas_key,
            data={"image": image_url, "zoom": zoom, "markers": markers, "hint": hint},
        )
        click = getattr(result, "clicked", None)
        if click and click.get("nonce") != st.session_state.get("last_click_nonce"):
            st.session_state.last_click_nonce = click.get("nonce")
            point = {"x": float(click["x"]), "y": float(click["y"])}
            if st.session_state.calibration is None:
                calibration_clicks.append(point)
                if len(calibration_clicks) == 3:
                    if (log_x and (x0 <= 0 or xv <= 0)) or (log_y and (y0 <= 0 or yv <= 0)):
                        calibration_clicks.pop()
                        st.error("Logarithmic axis calibration values must all be positive.")
                    elif math.isclose(x0, xv) or math.isclose(y0, yv):
                        calibration_clicks.pop()
                        st.error("The origin and reference value on each axis must be different.")
                    else:
                        ox, xp, yp = calibration_clicks
                        determinant = (xp["x"] - ox["x"]) * (yp["y"] - ox["y"]) - (xp["y"] - ox["y"]) * (yp["x"] - ox["x"])
                        if abs(determinant) < 1e-5:
                            calibration_clicks.pop()
                            st.error("Calibration points are collinear; choose a clearer y-axis reference point.")
                        else:
                            st.session_state.calibration = {"origin": ox, "xpoint": xp, "ypoint": yp, "values": [x0, xv, y0, yv]}
                            st.session_state.calibration_clicks = []
                st.rerun()
            else:
                st.session_state.datasets[selected]["points"].append(point)
                st.rerun()

        if st.session_state.calibration is None:
            st.info("Calibrate the axes to begin extracting data points.")
        else:
            st.subheader("Data table")
            rows = []
            for dataset_index, dataset in enumerate(st.session_state.datasets):
                for point_index, point in enumerate(dataset["points"]):
                    px, py = calibrated_value(point, st.session_state.calibration, log_x, log_y)
                    rows.append({"Dataset": dataset["name"], x_label: px, y_label: py, "_dataset": dataset_index, "_point": point_index})
            if rows:
                edited = st.data_editor(rows, key="point_table", num_rows="dynamic", hide_index=True, width="stretch", alt="Digitized x and y values by dataset", column_config={"_dataset": None, "_point": None, "Dataset": st.column_config.TextColumn("Dataset")})
                if len(edited) != len(rows):
                    st.warning("Add or delete points using image clicks and the Undo button so each point stays attached to the correct dataset.")
                else:
                    table_changed = False
                    for row_index, row in enumerate(edited):
                        original = rows[row_index]
                        dataset_index, point_index = original["_dataset"], original["_point"]
                        dataset = st.session_state.datasets[dataset_index]
                        new_name = str(row["Dataset"])
                        if new_name != dataset["name"]:
                            dataset["name"] = new_name
                            table_changed = True
                        xval = float(row[x_label]); yval = float(row[y_label])
                        if (not log_x or xval > 0) and (not log_y or yval > 0):
                            new_position = image_position(xval, yval, st.session_state.calibration, log_x, log_y)
                            if not math.isclose(new_position["x"], dataset["points"][point_index]["x"], abs_tol=1e-10) or not math.isclose(new_position["y"], dataset["points"][point_index]["y"], abs_tol=1e-10):
                                dataset["points"][point_index] = new_position
                                table_changed = True
                    if table_changed:
                        st.rerun()
            else:
                st.caption("Clicked points will appear here as you digitize the graph.")
        csv_data = wide_csv(st.session_state.datasets, x_label, y_label, st.session_state.calibration, log_x, log_y)
        st.download_button("Download CSV", csv_data, file_name="digitized_data.csv", mime="text/csv", width="content", disabled=st.session_state.calibration is None)
    except Exception as exc:
        st.error(f"Could not read or display this image: {exc}")
else:
    st.info("Upload a PNG, JPG, GIF, TIFF, or other common image file to get started.")
