---
name: chaoxing-pdf-extractor
description: Extract PPT or document images from Chaoxing/Xuexitong course pages and save them as chapter PDFs using Selenium browser automation. Use when a user provides a Chaoxing course URL, asks to download courseware, convert embedded PPT/document image pages into PDFs, test the Acselerator chaoxing-pdf-extractor workflow, or troubleshoot Chaoxing PDF extraction.
---

# Chaoxing PDF Extractor

## Overview

Use this skill to run a local Selenium workflow that opens a Chaoxing course page, lets the user
complete manual login when needed, parses chapter links, downloads embedded document images, and
combines those images into PDFs.

## Workflow

1. Use the bundled script at `scripts/chaoxing_pdf_extractor.py`.
2. Run it from an activated non-base Python environment. If dependencies are missing, create or use
   a dedicated environment before installing `scripts/requirements.txt`.
3. Prefer Chrome on Linux unless the user specifically asks for Edge.
4. Reuse the default Chrome profile and cookie file so login usually only needs to be completed
   once:
   `~/.cache/chaoxing-pdf-extractor/chrome-profile`
   `~/.cache/chaoxing-pdf-extractor/cookies.json`
5. Save outputs under the requested directory, or under `downloads/` by default.

## Commands

Install dependencies only after confirming the active environment is not `base`:

```bash
python -m pip install -r /home/server/.codex/skills/chaoxing-pdf-extractor/scripts/requirements.txt
```

Run a normal extraction with manual login. The default mode tries Chaoxing's converted PDF first
and falls back to rebuilding a PDF from page images:

```bash
python /home/server/.codex/skills/chaoxing-pdf-extractor/scripts/chaoxing_pdf_extractor.py \
  --course-url "<CHAOXING_COURSE_URL>" \
  --output-dir ./downloads \
  --browser chrome
```

After the first successful login, reuse the saved profile and skip the login prompt:

```bash
python /home/server/.codex/skills/chaoxing-pdf-extractor/scripts/chaoxing_pdf_extractor.py \
  --course-url "<CHAOXING_COURSE_URL>" \
  --skip-login
```

Try the original uploaded PPT/PPTX first, then fall back to direct PDF and image PDF:

```bash
python /home/server/.codex/skills/chaoxing-pdf-extractor/scripts/chaoxing_pdf_extractor.py \
  --course-url "<CHAOXING_COURSE_URL>" \
  --download-mode prefer-source
```

List parsed chapters without downloading:

```bash
python /home/server/.codex/skills/chaoxing-pdf-extractor/scripts/chaoxing_pdf_extractor.py \
  --course-url "<CHAOXING_COURSE_URL>" \
  --dry-run
```

Reuse a logged-in Chrome profile:

```bash
python /home/server/.codex/skills/chaoxing-pdf-extractor/scripts/chaoxing_pdf_extractor.py \
  --course-url "<CHAOXING_COURSE_URL>" \
  --user-data-dir /path/to/chrome-profile \
  --skip-login
```

## Operating Notes

- Do not run fully headless unless a logged-in browser profile is supplied; login often needs QR or
  verification-code interaction.
- If a target URL opens the Chaoxing login page, tell the user that authenticated access is required.
- The script uses a persistent Chrome profile by default. Do not delete
  `~/.cache/chaoxing-pdf-extractor/chrome-profile` or
  `~/.cache/chaoxing-pdf-extractor/cookies.json` unless login state should be reset.
- Prefer `--download-mode prefer-direct-pdf` for speed. Use `--download-mode prefer-source` only
  when the user specifically wants the original PPT/PPTX, because Chaoxing may reject the source
  download endpoint with 403.
- Use `--limit 1 --dry-run` for quick validation before downloading a full course.
- Use `--current-page-only` when the user provides a direct chapter page or chapter-list parsing
  fails but the current page contains an embedded document.
- Read `references/upstream.md` only when provenance or differences from the upstream repository are
  relevant.

## Safety

- Use only for materials the user is allowed to access.
- Avoid collecting or printing passwords, tokens, or personal account credentials.
- Keep generated PDFs local unless the user explicitly asks to move or upload them.
