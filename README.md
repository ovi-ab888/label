# Streamlit Label Generator (Illustrator Template → Data → PDF)

This demo shows the full workflow:

1. **Load Template** — Illustrator-exported PDF (./templates/Template.pdf or upload).
2. **Load Data** — CSV with columns: `PRODUCT_NAME, COLOUR, STYLE, BATCH, BARCODE`.
3. **Place Fields** — Percent-based controls so it adapts to any page size.
4. **Generate** — Multi-page PDF with text + barcode on top of your template.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
