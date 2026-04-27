# Chaoxing PDF Extractor Skill

Codex skill and CLI tool for extracting Chaoxing/Xuexitong course materials.
The extraction workflow is adapted from
`https://github.com/Acselerator/chaoxing-pdf-extractor.git`.

It opens a Chaoxing course page with Selenium, restores saved login cookies when possible, parses
chapter links, then downloads the original source file when Chaoxing exposes it. If the source file
is not available, it can fall back to Chaoxing's converted PDF or rebuild a PDF from document page
images.

## What Link To Provide

Provide the course chapter-list page URL, usually copied from the browser after opening a course in
Xuexitong/Chaoxing. It commonly looks like:

```text
https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu?courseid=...&clazzid=...&cpi=...&enc=...&pageHeader=1
```

The URL should contain at least:

- `courseid`
- `clazzid`
- `cpi`
- `enc`

Use the page that shows the left-side chapter catalog. Direct single-chapter links can also work
with `--current-page-only`, but the course chapter-list URL is preferred for full-course downloads.

## Install

Use an isolated Python environment. Do not install dependencies into `base`.

```bash
conda create -n chaoxing-pdf-extractor python=3.10 -y
conda activate chaoxing-pdf-extractor
env PYTHONNOUSERSITE=1 python -m pip install -r scripts/requirements.txt
```

Chrome is the recommended browser on Linux. The script uses `webdriver-manager` for ChromeDriver.

## First Run

The first run may require manual login because Chaoxing often uses QR login or verification codes.

```bash
conda activate chaoxing-pdf-extractor
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --output-dir './downloads' \
  --browser chrome
```

After logging in inside the opened browser, return to the terminal and press Enter. The script saves
cookies to:

```text
~/.cache/chaoxing-pdf-extractor/cookies.json
```

## Subsequent Runs

After cookies are saved, use `--skip-login`:

```bash
conda activate chaoxing-pdf-extractor
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --output-dir './downloads' \
  --browser chrome \
  --skip-login
```

If the saved cookies expire, the script falls back to manual login and refreshes the cookie file.

## Download Modes

Default mode:

```bash
--download-mode prefer-direct-pdf
```

Available modes:

- `prefer-source`: try original source files first, then direct PDF, then image PDF.
- `source`: only try original source files. Use this when you specifically want PPT/PPTX/PDF source uploads.
- `prefer-direct-pdf`: try Chaoxing's converted PDF first, then image PDF.
- `direct-pdf`: only try Chaoxing's converted PDF.
- `image-pdf`: download document page images and rebuild a PDF locally.

For full-course archival, `prefer-source` is usually best:

```bash
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --output-dir './downloads' \
  --browser chrome \
  --skip-login \
  --download-mode prefer-source
```

## Quick Checks

List chapters without downloading:

```bash
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --dry-run \
  --skip-login
```

Download only the first chapter:

```bash
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --limit 1 \
  --skip-login
```

## Codex Skill Installation

Clone this repository into your Codex skills directory:

```bash
git clone https://github.com/muqy1818/chaoxing-pdf-extractor-skill.git \
  ~/.codex/skills/chaoxing-pdf-extractor
```

Restart Codex or reload skills so `chaoxing-pdf-extractor` is discovered.

## Notes

- Only use this tool for materials you are allowed to access.
- Keep `~/.cache/chaoxing-pdf-extractor/cookies.json` private.
- Do not commit downloaded course materials, cookies, browser profiles, or local cache files.
- Some course chapters may contain videos or interactive content only; these are skipped when no
  document object or page image is found.
