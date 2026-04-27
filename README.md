<p align="center">
  <img src="assets/readme-hero.png" alt="Chaoxing PDF Extractor Skill hero" width="100%">
</p>

# Chaoxing PDF Extractor Skill

Codex skill and CLI tool for extracting Chaoxing/Xuexitong course materials.

This workflow is adapted from
`https://github.com/Acselerator/chaoxing-pdf-extractor.git` and extended with
course-wide extraction, saved-cookie login reuse, original source-file download, direct converted
PDF download, and image-PDF fallback.

Languages: [中文](#中文说明) | [English](#english)

## 中文说明

### 这个工具做什么

这个仓库提供一个 Codex skill 和一个可直接运行的 Python CLI，用于从学习通/超星课程页面批量提取课件资料。

它会用 Selenium 打开课程页面，解析左侧章节目录，然后按章节保存资料。下载策略支持：

- 优先下载老师上传的原始源文件，例如 `pptx`、`pdf`、`docx`
- 如果源文件不可用，下载超星转换好的 PDF
- 如果直链 PDF 不可用，下载页面图片并本地合成为 PDF
- 首次登录后保存 cookie，后续可用 `--skip-login` 免重复登录

### 需要提供什么链接

优先提供课程章节列表页链接，也就是打开课程后能看到左侧章节目录的页面。链接通常长这样：

```text
https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu?courseid=...&clazzid=...&cpi=...&enc=...&pageHeader=1
```

这个链接一般需要包含：

- `courseid`
- `clazzid`
- `cpi`
- `enc`

不要只给登录页链接。也不要优先给单个章节页面链接，除非你只想抓当前章节，并配合
`--current-page-only` 使用。

### 安装

请使用独立 Python 环境，不要把依赖装到 `base` 环境。

```bash
conda create -n chaoxing-pdf-extractor python=3.10 -y
conda activate chaoxing-pdf-extractor
env PYTHONNOUSERSITE=1 python -m pip install -r scripts/requirements.txt
```

Linux 上推荐使用 Chrome。脚本会通过 `webdriver-manager` 管理 ChromeDriver。

### 第一次运行

第一次通常需要手动登录，因为学习通可能要求扫码、验证码或二次验证。

```bash
conda activate chaoxing-pdf-extractor
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --output-dir './downloads' \
  --browser chrome
```

浏览器打开后，在页面里完成登录。确认登录成功后，回到终端按 Enter。脚本会保存 cookie 到：

```text
~/.cache/chaoxing-pdf-extractor/cookies.json
```

### 后续免登录运行

cookie 保存后，后续加 `--skip-login`：

```bash
conda activate chaoxing-pdf-extractor
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --output-dir './downloads' \
  --browser chrome \
  --skip-login
```

如果 cookie 过期，脚本会自动退回手动登录，并刷新 cookie 文件。

### 下载模式

默认模式：

```bash
--download-mode prefer-direct-pdf
```

可选模式：

- `prefer-source`：优先原始源文件，再尝试直链 PDF，最后退回图片合成 PDF
- `source`：只尝试原始源文件，适合专门抓 `pptx`、`pdf`、`docx`
- `prefer-direct-pdf`：优先超星转换 PDF，再退回图片合成 PDF
- `direct-pdf`：只尝试超星转换 PDF
- `image-pdf`：下载页面图片并本地合成为 PDF

如果要归档整门课，推荐：

```bash
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --output-dir './downloads' \
  --browser chrome \
  --skip-login \
  --download-mode prefer-source
```

### 快速检查

只解析章节，不下载：

```bash
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --dry-run \
  --skip-login
```

只下载第一章：

```bash
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --limit 1 \
  --skip-login
```

### 安装为 Codex Skill

把仓库克隆到 Codex skills 目录：

```bash
git clone https://github.com/MuQY1818/chaoxing-pdf-extractor-skill.git \
  ~/.codex/skills/chaoxing-pdf-extractor
```

然后重启 Codex 或重新加载 skills。

### 注意事项

- 仅用于你有权限访问的课程资料
- 不要提交 `~/.cache/chaoxing-pdf-extractor/cookies.json`
- 不要提交浏览器 profile、下载资料或本地缓存
- 视频章节、交互式章节、无文档对象的章节可能会被跳过
- 部分课程源文件本身就是 PDF，不一定都是 PPTX

## English

### What This Tool Does

This repository provides a Codex skill and a standalone Python CLI for extracting course materials
from Chaoxing/Xuexitong course pages.

It opens the course page with Selenium, parses the chapter catalog, and saves materials by chapter.
The download strategy supports:

- Original uploaded source files, such as `pptx`, `pdf`, and `docx`
- Chaoxing converted PDF files when source files are unavailable
- Local image-to-PDF rebuilding when direct PDF downloads are unavailable
- Saved-cookie reuse after the first login, so later runs can use `--skip-login`

### What Link Should I Provide

Provide the course chapter-list page URL. This is the page that shows the course catalog on the
left side after you open a course in Chaoxing/Xuexitong. It usually looks like:

```text
https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu?courseid=...&clazzid=...&cpi=...&enc=...&pageHeader=1
```

The URL should usually include:

- `courseid`
- `clazzid`
- `cpi`
- `enc`

Do not provide only the login page. Avoid single-chapter URLs unless you only want the current
chapter and plan to use `--current-page-only`.

### Install

Use an isolated Python environment. Do not install dependencies into `base`.

```bash
conda create -n chaoxing-pdf-extractor python=3.10 -y
conda activate chaoxing-pdf-extractor
env PYTHONNOUSERSITE=1 python -m pip install -r scripts/requirements.txt
```

Chrome is recommended on Linux. The script uses `webdriver-manager` for ChromeDriver.

### First Run

The first run usually requires manual login because Chaoxing may require QR login, verification
codes, or secondary verification.

```bash
conda activate chaoxing-pdf-extractor
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --output-dir './downloads' \
  --browser chrome
```

After the browser opens, complete login in the browser. Once the account is logged in, return to the
terminal and press Enter. The script saves cookies to:

```text
~/.cache/chaoxing-pdf-extractor/cookies.json
```

### Subsequent Runs Without Repeated Login

After cookies are saved, use `--skip-login`:

```bash
conda activate chaoxing-pdf-extractor
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --output-dir './downloads' \
  --browser chrome \
  --skip-login
```

If saved cookies expire, the script falls back to manual login and refreshes the cookie file.

### Download Modes

Default mode:

```bash
--download-mode prefer-direct-pdf
```

Available modes:

- `prefer-source`: try original source files first, then direct PDF, then image PDF
- `source`: only try original source files; useful when you specifically want `pptx`, `pdf`, or `docx`
- `prefer-direct-pdf`: try Chaoxing converted PDF first, then image PDF
- `direct-pdf`: only try Chaoxing converted PDF
- `image-pdf`: download page images and rebuild a PDF locally

For full-course archival, `prefer-source` is usually the best choice:

```bash
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --output-dir './downloads' \
  --browser chrome \
  --skip-login \
  --download-mode prefer-source
```

### Quick Checks

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

### Install As A Codex Skill

Clone this repository into your Codex skills directory:

```bash
git clone https://github.com/MuQY1818/chaoxing-pdf-extractor-skill.git \
  ~/.codex/skills/chaoxing-pdf-extractor
```

Then restart Codex or reload skills.

### Notes

- Use this tool only for course materials you are allowed to access.
- Keep `~/.cache/chaoxing-pdf-extractor/cookies.json` private.
- Do not commit browser profiles, downloaded materials, cookies, or local cache files.
- Video-only, interactive, or document-less chapters may be skipped.
- Some course source files are PDFs, not PPTX files.

## Image Prompt Used

```text
Use case: productivity-visual
Asset type: GitHub README hero banner
Primary request: Create a minimalist Apple-inspired hero image for a tool that extracts course materials from 学习通 / Chaoxing into local PDF and PPTX files.
Scene/backdrop: pure clean light background, subtle off-white to very light gray gradient, lots of negative space, no desk objects, no plants, no keyboard, no robot.
Subject: one elegant floating browser card on the left showing a simplified 学习通 course page. The top-left of the card has a small red rounded-square app icon and the exact Chinese text “学习通”. On the right, only three floating file cards: one PDF document icon, one PPTX slide icon, and one folder icon. A single thin soft blue line connects the course card to the files.
Style/medium: Apple keynote-style minimal product illustration, premium software landing-page hero, soft glassmorphism, subtle shadows, clean rounded rectangles, high-end restrained design.
Composition/framing: wide 16:9 banner, centered balanced layout, generous margins, sparse elements, calm and readable at README width.
Lighting/mood: bright, quiet, refined, airy, professional.
Color palette: mostly white, silver, very light gray, small red accent for 学习通 icon, soft blue connector, tiny warm accent on folder. Avoid saturated colors and avoid busy gradients.
Text: only render this exact Chinese text once: “学习通”. No other readable text, no random letters, no numbers.
Constraints: no QR code, no watermark, no real website data, no OpenAI logo, no GitHub logo, no official-affiliation feel, no clutter, no robot, no plants, no desk scene, no many folders, no complex network lines.
```
