<p align="center">
  <img src="assets/readme-hero.png" alt="Chaoxing PDF Extractor Skill" width="100%">
</p>

# Chaoxing PDF Extractor Skill

Unofficial Codex skill and Python CLI for saving Chaoxing/Xuexitong course materials locally.

This project is adapted from
[`Acselerator/chaoxing-pdf-extractor`](https://github.com/Acselerator/chaoxing-pdf-extractor)
and adds course-wide extraction, reusable login cookies, source-file download, direct PDF download,
and image-to-PDF fallback.

[中文](#中文) | [English](#english)

## 中文

### 简介

这个工具用于把学习通/超星课程里的课件资料保存到本地目录。它会打开课程页面，读取章节目录，
逐章查找文档对象，并尽量下载老师上传的原始文件。

下载优先级取决于 `--download-mode`。归档整门课时通常建议使用 `prefer-source`：
先尝试原始文件，例如 `pptx`、`pdf`、`docx`；失败时再尝试超星转换 PDF；最后才从页面图片合成
PDF。

这是非官方工具。请只用于你有权限访问和保存的课程资料。

### 适用场景

- 批量备份课程课件
- 把课程资料整理成本地文件夹，便于离线复习
- 在交给 AI 阅读前，先把学习通页面里的资料导出为文件
- 尽量保留原始 `pptx`、`pdf`、`docx`，而不是截图

### 需要什么课程链接

请提供课程章节列表页链接，也就是打开课程后左侧能看到章节目录的页面。常见格式如下：

```text
https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu?courseid=...&clazzid=...&cpi=...&enc=...&pageHeader=1
```

通常需要包含这些参数：

- `courseid`
- `clazzid`
- `cpi`
- `enc`

不要只给登录页链接。如果只想抓当前章节，可以给单章节页面链接，并加上 `--current-page-only`。

### 安装

请使用独立 Python 环境。不要把依赖安装到 `base` 环境。

```bash
git clone https://github.com/MuQY1818/chaoxing-pdf-extractor-skill.git
cd chaoxing-pdf-extractor-skill

conda create -n chaoxing-pdf-extractor python=3.10 -y
conda activate chaoxing-pdf-extractor
env PYTHONNOUSERSITE=1 python -m pip install -r scripts/requirements.txt
```

Linux 上推荐使用 Chrome。脚本会通过 `webdriver-manager` 管理 ChromeDriver。

### 第一次运行

第一次运行通常需要手动登录，因为学习通可能要求扫码、验证码或二次验证。

```bash
conda activate chaoxing-pdf-extractor
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --output-dir './downloads' \
  --browser chrome
```

浏览器打开后，先在页面里完成登录。确认登录成功后，回到终端按 Enter。

脚本会把 cookie 保存到：

```text
~/.cache/chaoxing-pdf-extractor/cookies.json
```

### 后续运行

登录态保存后，后续运行加 `--skip-login`：

```bash
conda activate chaoxing-pdf-extractor
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --output-dir './downloads' \
  --browser chrome \
  --skip-login
```

如果 cookie 过期，脚本会退回手动登录，并刷新 cookie 文件。

### 常用命令

只列出章节，不下载：

```bash
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --dry-run \
  --skip-login
```

只下载第一章，用于测试：

```bash
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --limit 1 \
  --skip-login
```

归档整门课，优先保留原始文件：

```bash
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --output-dir './downloads' \
  --browser chrome \
  --skip-login \
  --download-mode prefer-source
```

### 下载模式

| 模式 | 行为 |
| --- | --- |
| `prefer-source` | 优先原始源文件，再尝试直链 PDF，最后退回图片合成 PDF |
| `source` | 只尝试原始源文件，适合专门抓 `pptx`、`pdf`、`docx` |
| `prefer-direct-pdf` | 优先超星转换 PDF，再退回图片合成 PDF |
| `direct-pdf` | 只尝试超星转换 PDF |
| `image-pdf` | 下载页面图片并本地合成为 PDF |

默认模式是 `prefer-direct-pdf`。如果你想尽量拿到原始 PPTX，请使用 `prefer-source`。

### 安装为 Codex Skill

如果你只想把它作为 Codex skill 使用，把仓库克隆到 skills 目录：

```bash
git clone https://github.com/MuQY1818/chaoxing-pdf-extractor-skill.git \
  ~/.codex/skills/chaoxing-pdf-extractor
```

然后重启 Codex，或重新加载 skills。

### 复制给 Agent 的安装提示词

可以把下面这段直接发给另一个 Agent：

```text
请帮我安装并使用这个 Codex skill：

仓库：https://github.com/MuQY1818/chaoxing-pdf-extractor-skill

目标：
1. 把仓库克隆到 ~/.codex/skills/chaoxing-pdf-extractor
2. 创建或使用独立 Python 环境，不要安装到 base 环境
3. 安装 scripts/requirements.txt 里的依赖
4. 使用我提供的学习通课程链接运行脚本
5. 第一次运行如果需要登录，请打开浏览器让我完成登录
6. 登录后保存 cookie，后续使用 --skip-login
7. 默认优先使用 --download-mode prefer-source，把课程资料保存到我指定的目录

我会提供：
- 学习通课程章节列表页链接
- 输出目录

请先检查环境和依赖，再执行。
```

### 注意事项

- 不要提交 `~/.cache/chaoxing-pdf-extractor/cookies.json`
- 不要提交浏览器 profile、下载资料或本地缓存
- 视频章节、交互式章节、没有文档对象的章节可能会被跳过
- 部分课程源文件本身就是 PDF，不一定都是 PPTX
- 本项目与学习通/超星无官方关联

## English

### Overview

This tool saves course materials from Chaoxing/Xuexitong to a local directory. It opens the course
page, reads the chapter catalog, finds document objects chapter by chapter, and downloads the best
available file.

For full-course archival, `prefer-source` is usually the most useful mode. It tries original source
files first, such as `pptx`, `pdf`, or `docx`; then it falls back to Chaoxing's converted PDF; as a
last resort, it rebuilds a PDF from page images.

This is an unofficial tool. Use it only for course materials you are allowed to access and save.

### When To Use It

- Back up courseware in bulk
- Organize course materials into local folders
- Export materials before giving them to an AI reader
- Prefer original `pptx`, `pdf`, or `docx` files over screenshots

### Course URL

Use the course chapter-list page URL. This is the page that shows the course catalog on the left
after you open a course. It usually looks like this:

```text
https://mooc2-ans.chaoxing.com/mooc2-ans/mycourse/stu?courseid=...&clazzid=...&cpi=...&enc=...&pageHeader=1
```

The URL usually includes:

- `courseid`
- `clazzid`
- `cpi`
- `enc`

Do not provide only the login page. If you only want the current chapter, use a single-chapter URL
with `--current-page-only`.

### Installation

Use an isolated Python environment. Do not install dependencies into `base`.

```bash
git clone https://github.com/MuQY1818/chaoxing-pdf-extractor-skill.git
cd chaoxing-pdf-extractor-skill

conda create -n chaoxing-pdf-extractor python=3.10 -y
conda activate chaoxing-pdf-extractor
env PYTHONNOUSERSITE=1 python -m pip install -r scripts/requirements.txt
```

Chrome is recommended on Linux. ChromeDriver is handled through `webdriver-manager`.

### First Run

The first run usually needs manual login because Chaoxing may ask for QR login, verification codes,
or secondary verification.

```bash
conda activate chaoxing-pdf-extractor
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --output-dir './downloads' \
  --browser chrome
```

Complete login in the browser, then return to the terminal and press Enter.

Cookies are saved to:

```text
~/.cache/chaoxing-pdf-extractor/cookies.json
```

### Later Runs

After cookies have been saved, use `--skip-login`:

```bash
conda activate chaoxing-pdf-extractor
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --output-dir './downloads' \
  --browser chrome \
  --skip-login
```

If cookies expire, the script falls back to manual login and refreshes the cookie file.

### Common Commands

List chapters without downloading:

```bash
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --dry-run \
  --skip-login
```

Download the first chapter only:

```bash
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --limit 1 \
  --skip-login
```

Archive a full course and prefer original source files:

```bash
env PYTHONNOUSERSITE=1 python scripts/chaoxing_pdf_extractor.py \
  --course-url '<COURSE_URL>' \
  --output-dir './downloads' \
  --browser chrome \
  --skip-login \
  --download-mode prefer-source
```

### Download Modes

| Mode | Behavior |
| --- | --- |
| `prefer-source` | Try original source files, then direct PDF, then image PDF |
| `source` | Only try original source files; useful for `pptx`, `pdf`, or `docx` |
| `prefer-direct-pdf` | Try Chaoxing converted PDF first, then image PDF |
| `direct-pdf` | Only try Chaoxing converted PDF |
| `image-pdf` | Download page images and rebuild a PDF locally |

The default mode is `prefer-direct-pdf`. Use `prefer-source` when you want the best chance of
getting original PPTX files.

### Install As A Codex Skill

Clone the repository into your Codex skills directory:

```bash
git clone https://github.com/MuQY1818/chaoxing-pdf-extractor-skill.git \
  ~/.codex/skills/chaoxing-pdf-extractor
```

Then restart Codex or reload skills.

### Prompt For Another Agent

You can copy this prompt to another agent:

```text
Install and use this Codex skill for me:

Repository: https://github.com/MuQY1818/chaoxing-pdf-extractor-skill

Goals:
1. Clone the repository to ~/.codex/skills/chaoxing-pdf-extractor
2. Create or use an isolated Python environment; do not install dependencies into base
3. Install dependencies from scripts/requirements.txt
4. Run the extractor with the Chaoxing course URL I provide
5. If the first run requires login, open the browser and wait for me to finish login
6. Save cookies after login and use --skip-login for later runs
7. Prefer --download-mode prefer-source and save materials to my requested output directory

I will provide:
- The Chaoxing course chapter-list URL
- The output directory

Check the environment and dependencies before running.
```

### Notes

- Keep `~/.cache/chaoxing-pdf-extractor/cookies.json` private
- Do not commit browser profiles, downloaded materials, cookies, or local cache files
- Video-only, interactive, or document-less chapters may be skipped
- Some course source files are PDFs, not PPTX files
- This project is not affiliated with Chaoxing or Xuexitong
