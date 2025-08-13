import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
from PIL import Image as PILImage
from io import BytesIO
import tempfile
import os
from barcode import Code128, EAN13
from barcode.writer import ImageWriter

# Configure page
st.set_page_config(
    page_title="Label Generator (Illustrator → Streamlit)", 
    layout="wide",
    page_icon="🏷️"
)
st.title("🏷️ Label Generator — Illustrator Template → Data → PDF")

# Sidebar controls
with st.sidebar:
    st.header("1) Template (PDF)")
    tpl_file = st.file_uploader(
        "Upload Illustrator-exported PDF template", 
        type=["pdf"],
        help="Upload your label template PDF or use the sample file"
    )
    if not tpl_file:
        st.caption("Sample: ./templates/Template.pdf")

    st.header("2) Data (CSV)")
    data_file = st.file_uploader(
        "Upload CSV data", 
        type=["csv"],
        help="CSV should contain columns: PRODUCT_NAME, COLOUR, STYLE, BATCH, BARCODE"
    )
    if not data_file:
        st.caption("Sample: ./data/Data.csv")

    st.header("3) Barcode Settings")
    barcode_type = st.selectbox("Type", ["CODE128", "EAN13"])
    includetext = st.checkbox("Include human-readable text", value=True)

# ---------- Load template (from upload or sample path) ----------
st.markdown("#### Template Preview")
template_path = None
if tpl_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_tpl:
        tmp_tpl.write(tpl_file.read())
        template_path = tmp_tpl.name
else:
    sample_path = os.path.join(os.path.dirname(__file__), "templates", "Template.pdf")
    if os.path.exists(sample_path):
        template_path = sample_path
    else:
        st.error("No template provided and sample not found. Please upload a PDF template.")
        st.stop()

# Open template & preview first page
try:
    doc = fitz.open(template_path)
    page = doc[0]
    preview = page.get_pixmap(dpi=144)
    st.image(
        PILImage.open(BytesIO(preview.tobytes("png")), 
        use_container_width=True, 
        caption="Template Page 1 Preview"
    )
except Exception as e:
    st.error(f"Failed to load template: {str(e)}")
    st.stop()

# ---------- Placement controls ----------
st.markdown("---")
st.subheader("Field Placement (Percent of page)")

def pos_group(label, default_x, default_y, default_size=12):
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        x = st.slider(f"{label} — X %", 0.0, 100.0, default_x, 0.1)
    with c2:
        y = st.slider(f"{label} — Y %", 0.0, 100.0, default_y, 0.1)
    with c3:
        s = st.number_input(f"{label} — Font pt", value=default_size, min_value=6, max_value=72, step=1)
    return x, y, s

pn_x, pn_y, pn_s = pos_group("PRODUCT_NAME", 20.0, 60.0, 12)
cl_x, cl_y, cl_s = pos_group("COLOUR",        20.0, 70.0, 11)
st_x, st_y, st_s = pos_group("STYLE",         20.0, 80.0, 11)
bt_x, bt_y, bt_s = pos_group("BATCH",         20.0, 90.0, 11)

st.markdown("##### Barcode Placement & Size")
c1, c2, c3, c4 = st.columns([1,1,1,1])
with c1:
    bc_x = st.slider("BARCODE — X %", 0.0, 100.0, 75.0, 0.1)
with c2:
    bc_y = st.slider("BARCODE — Y %", 0.0, 100.0, 20.0, 0.1)
with c3:
    bc_w = st.slider("Width % of page", 5.0, 50.0, 20.0, 0.5)
with c4:
    bc_h = st.slider("Height % of page", 5.0, 30.0, 12.0, 0.5)

# ---------- Load data (from upload or sample path) ----------
st.markdown("---")
st.subheader("Data Table")

df = None
if data_file:
    try:
        df = pd.read_csv(data_file)
    except Exception as e:
        st.error(f"Failed to load CSV: {str(e)}")
        st.stop()
else:
    sample_csv = os.path.join(os.path.dirname(__file__), "data", "Data.csv")
    if os.path.exists(sample_csv):
        try:
            df = pd.read_csv(sample_csv)
        except Exception as e:
            st.error(f"Failed to load sample CSV: {str(e)}")
            st.stop()

if df is None or df.empty:
    st.warning("Please upload a CSV with columns like: PRODUCT_NAME, COLOUR, STYLE, BATCH, BARCODE")
    st.stop()

st.dataframe(df, use_container_width=True)

# ---------- Generate Labels ----------
st.markdown("---")
st.subheader("Generate Labels")

col_a, col_b = st.columns([1,1])
with col_a:
    start = st.number_input("Start row (1-indexed)", min_value=1, max_value=len(df), value=1)
with col_b:
    end = st.number_input("End row (inclusive)", min_value=1, max_value=len(df), value=len(df))

gen = st.button("🚀 Generate PDF")

# Helper functions
def make_barcode_png_bytes(code_text: str, kind: str, includetext: bool=True) -> bytes:
    if not code_text or str(code_text).strip() == "":
        code_text = "000000000000"
    writer = ImageWriter()
    
    try:
        if kind == "EAN13":
            # EAN13 needs 12 digits (checksum auto)
            digits = ''.join(ch for ch in str(code_text) if ch.isdigit())
            if len(digits) < 12:
                digits = digits.zfill(12)
            bc = EAN13(digits[:12], writer=writer)
        else:
            bc = Code128(str(code_text), writer=writer)
        
        out = BytesIO()
        bc.write(out, options={
            "write_text": includetext,
            "quiet_zone": 4.0,
            "font_size": 10,
            "module_height": 15.0
        })
        return out.getvalue()
    except Exception as e:
        st.error(f"Barcode generation failed: {str(e)}")
        return None

def p2x(rect, pct):  # percent → point
    return rect.x0 + (pct/100.0) * rect.width

def p2y(rect, pct):
    return rect.y0 + (pct/100.0) * rect.height

if gen:
    out_pdf_path = "generated_labels.pdf"
    out_doc = fitz.open()
    rect = page.rect  # page size in points

    sel = df.iloc[start-1:end].copy()
    progress = st.progress(0.0, text="Generating...")
    total = len(sel)

    for i, row in enumerate(sel.itertuples(index=False), start=1):
        try:
            tpl = fitz.open(template_path)
            p = tpl[0]

            # Draw text items
            def val(obj, name):
                try: 
                    return str(getattr(obj, name)) if getattr(obj, name) is not None else ""
                except AttributeError: 
                    return ""

            items = [
                (val(row, "PRODUCT_NAME"), pn_x, pn_y, pn_s),
                (val(row, "COLOUR"),       cl_x, cl_y, cl_s),
                (val(row, "STYLE"),        st_x, st_y, st_s),
                (val(row, "BATCH"),        bt_x, bt_y, bt_s),
            ]
            
            for text, xx, yy, size in items:
                p.insert_text(
                    (p2x(rect, xx), p2y(rect, yy)), 
                    text, 
                    fontsize=size, 
                    color=(0,0,0)
                    # fontfile= could be added for custom fonts

            # Barcode
            code_value = ""
            if "BARCODE" in df.columns:
                code_value = row[df.columns.get_loc("BARCODE")]
            
            bc_png = make_barcode_png_bytes(code_value, barcode_type, includetext)
            if bc_png is None:
                continue

            # Get image size via PIL to keep aspect
            pil_im = PILImage.open(BytesIO(bc_png))
            iw, ih = pil_im.size

            # Target size based on page %
            target_w = rect.width * (bc_w/100.0)
            scale = target_w / iw
            target_h = ih * scale
            max_h = rect.height * (bc_h/100.0)
            if target_h > max_h:
                scale = max_h / ih
                target_h = max_h
                target_w = iw * scale

            x = p2x(rect, bc_x)
            y = p2y(rect, bc_y)
            p.insert_image(
                fitz.Rect(x, y, x + target_w, y + target_h), 
                stream=bc_png
            )

            out_doc.insert_pdf(tpl)
            tpl.close()
            progress.progress(i/total, text=f"Generating... ({i}/{total})")
            
        except Exception as e:
            st.error(f"Error generating label for row {i}: {str(e)}")
            continue

    try:
        out_doc.save(out_pdf_path)
        out_doc.close()

        # Preview + Download
        prev_doc = fitz.open(out_pdf_path)
        prev_pix = prev_doc[0].get_pixmap(dpi=144)
        st.image(
            prev_pix.tobytes("ppm"), 
            caption="Preview (first page)", 
            use_container_width=True
        )

        with open(out_pdf_path, "rb") as f:
            st.download_button(
                "⬇️ Download Generated PDF", 
                data=f.read(), 
                file_name="labels.pdf", 
                mime="application/pdf"
            )

        st.success(f"Done! Generated {total} label page(s).")
        
    except Exception as e:
        st.error(f"Failed to save PDF: {str(e)}")

# Clean up temp files
if 'template_path' in locals() and os.path.exists(template_path):
    try:
        os.unlink(template_path)
    except:
        pass
