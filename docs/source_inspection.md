# Supplied source inspection

Read-only source files:
- `C:\Users\pk284\Downloads\gee_sar_extraction_pipeline_v3_1 (1).py`
- `C:\Users\pk284\Downloads\Minor_Project_1.pptx`

The prompt listed slightly different suffixes; the actual user-attached paths above were used. Originals were not overwritten or executed. The Python file is a Colab notebook export with `!pip`, interactive EE authentication, HTML/Leaflet AOI selection, notebook callbacks and download cells; it is not directly suitable for a web server.

The Python pipeline was read, and all 11 presentation slides' text plus embedded workflow/methodology images were inspected. The deck shows AOI selection → download → preprocessing/cloud-shadow masking → selective change detection → threshold decision → alerts. Its method tables include channel separation, subtraction, convolution, histogram/threshold operations, median/Gaussian filters, edge detectors, SAR/NDVI combinations and terrain display. It proposes future CNN inputs but supplies neither a trained model nor ground-truth validation.

## Reuse and changes

| Source logic | Application treatment |
|---|---|
| EE initialization with project ID | Reusable server initializer with local/ADC/service-account support; no notebook login in requests |
| Sentinel-1 IW VV/VH filter | Retained, with same pass/relative-orbit pairs, actual timestamps and valid-coverage tests |
| Evenly spaced images across year | Replaced by newest compatible multitemporal pair and explicit historical fallback |
| S2 B4/B3/B2/B8 exports | Retained band ordering; added SCL masks, valid coverage and NDVI support |
| GeoTIFF and SAR/RGB PNG outputs | Retained; bounded common UTM grids replace unconditional EPSG:4326 exports |
| SRTM elevation/hillshade | Retained source; use EE terrain slope/hillshade with metric native spacing rather than unscaled array gradients |
| CSV/README metadata | Replaced by structured per-scene/job JSON and database provenance |
| MATLAB-ready folders | Isolated per-job/per-segment directories, trusted JSON manifest and output validation |
| Differencing/filtering/threshold/NDVI methods | Separate real MATLAB functions, explicitly experimental |
| Agency logos/use cases | Not reused as affiliation claims |

The notebook's project ID was not automatically adopted. The user subsequently explicitly supplied `ananya-499117`, which was then saved to local configuration. No original scene dates or presentation screenshots are presented as current satellite results.
