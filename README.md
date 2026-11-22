# Plot digitizer

A single-page Streamlit app for extracting data from graph images. Upload a PNG, JPEG, GIF, TIFF, BMP, or WebP image, calibrate both axes, click data points, organize points into named datasets, and download a CSV.

## Run locally

```bash
uv sync
uv run streamlit run app.py
```

The image viewer supports zoom, and the axes may be linear or base-10 logarithmic. The three calibration clicks can follow rotated axes: click the origin, a known x-axis position, and a known y-axis position. The data table can be edited; edited values move their markers on the image.

## Deploy on Streamlit Community Cloud

Push this project to a GitHub repository, then create a new app in Streamlit Community Cloud using `app.py` as the entry point. The project dependencies are declared in `pyproject.toml` and `uv.lock`. After deployment, submit the app URL with the source file as required by the course.
