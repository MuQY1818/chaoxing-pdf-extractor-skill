# Upstream Notes

- Source repository: `https://github.com/Acselerator/chaoxing-pdf-extractor.git`
- Inspected commit: `18d554c`
- Original entry point: `main.py`

The bundled skill script keeps the original Selenium plus BeautifulSoup workflow but changes the
entry point into a CLI:

- Accept a course URL with `--course-url` instead of editing a hardcoded Python constant.
- Default to Chrome because it is commonly available on Linux hosts; Edge remains available with
  `--browser edge`.
- Fix the original fallback path that referenced an undefined `START_URL`.
- Add `--dry-run`, `--limit`, `--current-page-only`, `--user-data-dir`, and `--skip-login`.
- Add `--download-mode` with direct converted-PDF and source-file download attempts.
- Keep manual login as the default because Chaoxing commonly requires QR or verification-code login.

Chaoxing usually redirects unauthenticated course URLs to a login page. A successful extraction
therefore normally requires an interactive browser session or a reused logged-in browser profile.

Observed on the `云计算技术` test course:

- Original source download through `d0.ananas.chaoxing.com/download/<objectid>` returned `403`.
- Converted-PDF download derived from document image URLs succeeded and produced a 60-page PDF.
- Image-based PDF rebuild remains the fallback path.
