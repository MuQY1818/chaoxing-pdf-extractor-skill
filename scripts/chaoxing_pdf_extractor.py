"""Extract Chaoxing course document images into PDF files.

This script is adapted for Codex skill usage from:
https://github.com/Acselerator/chaoxing-pdf-extractor.git

It keeps the original manual-login flow because Chaoxing usually requires
interactive QR or verification-code login.
"""

from __future__ import annotations

import argparse
import io
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Iterable
from urllib.parse import parse_qs
from urllib.parse import unquote
from urllib.parse import urljoin
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import img2pdf
from PIL import Image
import requests
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

try:
    from selenium.webdriver.chrome.service import Service as ChromeService
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    ChromeDriverManager = None
    ChromeService = None


LOGIN_URL = (
    "https://passport2.chaoxing.com/login?fid=&newversion=true&"
    "refer=http%3A%2F%2Fi.chaoxing.com"
)
DEFAULT_OUTPUT_DIR = "downloads"
DEFAULT_USER_DATA_DIR = "~/.cache/chaoxing-pdf-extractor/chrome-profile"
DEFAULT_COOKIE_FILE = "~/.cache/chaoxing-pdf-extractor/cookies.json"
UI_IMAGE_MARKERS = (
    "/css/",
    "/images/",
    "/icon/",
    "loading",
    "button",
    "logo",
    "blank",
)
DOCUMENT_IMAGE_MARKERS = (
    "/doc/",
    "ananas.chaoxing.com",
    "preview",
    "thumb",
    "objectid",
)
OFFICE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
ZIP_MAGIC = b"PK\x03\x04"
SOURCE_DOWNLOAD_URLS = (
    "https://mooc1-1.chaoxing.com/ananas/status/{object_id}?flag=normal",
    "https://mooc1.chaoxing.com/ananas/status/{object_id}?flag=normal",
    "https://d0.ananas.chaoxing.com/download/{object_id}",
    "http://d0.ananas.chaoxing.com/download/{object_id}",
)
CONTENT_TYPE_EXTENSIONS = {
    "application/pdf": ".pdf",
    "application/vnd.ms-powerpoint": ".ppt",
    (
        "application/vnd.openxmlformats-officedocument.presentationml."
        "presentation"
    ): ".pptx",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def _configure_stdout() -> None:
    """Force UTF-8 output when possible."""
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def sanitize_filename(name: str, default: str = "untitled") -> str:
    """Return a filesystem-safe filename component."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name or "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or default


def parse_url_params(url: str) -> dict[str, str]:
    """Extract common Chaoxing query parameters."""
    params = parse_qs(urlparse(url).query)
    normalized = {}
    for source, target in (
        ("courseid", "courseId"),
        ("courseId", "courseId"),
        ("clazzid", "clazzId"),
        ("clazzId", "clazzId"),
        ("cpi", "cpi"),
        ("enc", "enc"),
    ):
        values = params.get(source)
        if values and target not in normalized:
            normalized[target] = values[0]
    return normalized


def make_options(browser: str, headless: bool, user_data_dir: str | None):
    """Create browser options for Chrome or Edge."""
    if browser == "edge":
        options = webdriver.EdgeOptions()
    else:
        options = webdriver.ChromeOptions()

    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--log-level=3")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    if user_data_dir:
        profile_dir = Path(user_data_dir).expanduser().resolve()
        profile_dir.mkdir(parents=True, exist_ok=True)
        options.add_argument(f"--user-data-dir={profile_dir}")
    return options


def build_driver(browser: str, headless: bool, user_data_dir: str | None):
    """Start a Selenium WebDriver session."""
    options = make_options(browser, headless, user_data_dir)
    try:
        if browser == "edge":
            return webdriver.Edge(options=options)
        if ChromeDriverManager and ChromeService:
            service = ChromeService(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=options)
        return webdriver.Chrome(options=options)
    except WebDriverException as exc:
        raise RuntimeError(
            f"Unable to start {browser} WebDriver. Install the browser and a "
            "matching driver, or let Selenium Manager download it."
        ) from exc


def normalize_cookie_for_selenium(cookie: dict) -> dict:
    """Keep only fields Selenium can reliably add back."""
    allowed = {"name", "value", "domain", "path", "secure", "httpOnly", "expiry"}
    normalized = {key: value for key, value in cookie.items() if key in allowed}
    if "expiry" in normalized:
        try:
            normalized["expiry"] = int(normalized["expiry"])
        except (TypeError, ValueError):
            normalized.pop("expiry", None)
    return normalized


def save_cookie_file(driver, cookie_file: str) -> None:
    """Persist Selenium cookies for later reuse."""
    path = Path(cookie_file).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(driver.get_cookies(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved cookies: {path}")


def load_cookie_file(driver, cookie_file: str) -> bool:
    """Load persisted cookies into a fresh browser session."""
    path = Path(cookie_file).expanduser().resolve()
    if not path.exists():
        print(f"Cookie file not found: {path}")
        return False

    cookies = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cookies, list) or not cookies:
        print(f"Cookie file is empty: {path}")
        return False

    domains = []
    for cookie in cookies:
        domain = str(cookie.get("domain", "")).lstrip(".")
        if domain and domain not in domains:
            domains.append(domain)

    added = 0
    for domain in domains:
        try:
            driver.get(f"https://{domain}/")
            time.sleep(0.5)
        except Exception:
            pass
        for cookie in cookies:
            cookie_domain = str(cookie.get("domain", "")).lstrip(".")
            if cookie_domain != domain:
                continue
            try:
                driver.add_cookie(normalize_cookie_for_selenium(cookie))
                added += 1
            except Exception as exc:
                print(f"Could not restore cookie {cookie.get('name')}: {exc}")

    print(f"Restored {added} cookies from: {path}")
    return added > 0


def maybe_wait_for_login(
    driver,
    login_url: str,
    course_url: str,
    skip_login: bool,
    cookie_file: str,
) -> None:
    """Open the login page unless an existing browser profile is reused."""
    if skip_login:
        print("Skipping explicit login step.")
        load_cookie_file(driver, cookie_file)
        driver.get(course_url)
        return

    print(f"Opening login page: {login_url}")
    driver.get(login_url)
    print("")
    print("Manual step required:")
    print("1. Complete Chaoxing login in the browser window.")
    print("2. Confirm that the account is logged in.")
    print("3. Return to this terminal and press Enter.")
    input("Press Enter after login is complete...")
    print(f"Opening target course page: {course_url}")
    driver.get(course_url)


def copy_cookies_to_session(driver) -> tuple[requests.Session, dict[str, str]]:
    """Copy Selenium cookies into a requests session."""
    session = requests.Session()
    user_agent = driver.execute_script("return navigator.userAgent;")
    headers = {
        "User-Agent": user_agent,
        "Referer": driver.current_url,
    }
    for cookie in driver.get_cookies():
        session.cookies.set(cookie["name"], cookie["value"])
    return session, headers


def detect_course_dir(driver, output_dir: Path) -> Path:
    """Detect a course title and create the target course directory."""
    course_title = driver.title or "Chaoxing Course"
    for selector in ("h1", ".courseName", ".title", ".f18"):
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        for element in elements:
            text = element.text.strip()
            if text and len(text) < 80:
                course_title = text
                break
        if course_title:
            break
    course_dir = output_dir / sanitize_filename(course_title, "chaoxing-course")
    course_dir.mkdir(parents=True, exist_ok=True)
    print(f"Detected course title: {course_title}")
    print(f"Output directory: {course_dir}")
    return course_dir


def get_hidden_params(soup: BeautifulSoup, fallback_url: str) -> dict[str, str]:
    """Read hidden Chaoxing course parameters, falling back to URL params."""
    params = parse_url_params(fallback_url)
    for field_id, key in (
        ("courseId", "courseId"),
        ("courseid", "courseId"),
        ("clazzId", "clazzId"),
        ("clazzid", "clazzId"),
        ("cpi", "cpi"),
        ("enc", "enc"),
    ):
        field = soup.find("input", id=field_id)
        if field and field.get("value"):
            params[key] = field["value"]
    return params


def build_studentstudy_url(chapter_id: str, params: dict[str, str]) -> str:
    """Build the legacy studentstudy URL used by Chaoxing chapter pages."""
    return (
        "https://mooc1.chaoxing.com/mycourse/studentstudy"
        f"?chapterId={chapter_id}"
        f"&courseId={params.get('courseId', '')}"
        f"&clazzid={params.get('clazzId', '')}"
        f"&cpi={params.get('cpi', '')}"
        f"&enc={params.get('enc', '')}"
        "&mooc2=1&hidetype=0"
    )


def add_chapter(
    chapters: list[dict[str, str]],
    title: str,
    url: str,
    folder: str,
) -> None:
    """Append a chapter if the URL has not already been seen."""
    if not url:
        return
    if any(chapter["url"] == url for chapter in chapters):
        return
    cid_match = re.search(r"chapterId=(\d+)", url)
    chapters.append(
        {
            "title": sanitize_filename(title, "chapter"),
            "url": url,
            "cid": cid_match.group(1) if cid_match else url,
            "folder": sanitize_filename(folder, "misc"),
        }
    )


def parse_chapters_from_html(
    html: str,
    base_url: str,
    current_folder: str = "misc",
) -> list[dict[str, str]]:
    """Parse Chaoxing chapter links from one document or frame."""
    soup = BeautifulSoup(html, "html.parser")
    params = get_hidden_params(soup, base_url)
    chapters = []
    folder = current_folder

    all_elements = soup.find_all("div", class_=["chapter_unit", "chapter_item"])
    for element in all_elements:
        classes = element.get("class", [])
        if "chapter_unit" in classes:
            title_element = element.find(class_="catalog_title")
            title_element = title_element or element.find(class_="catalog_sbar")
            folder = sanitize_filename(
                title_element.get_text(strip=True)
                if title_element
                else element.get_text(strip=True),
                "misc",
            )
            continue

        chapter_num = ""
        num_span = element.find("span", class_="catalog_sbar")
        if num_span:
            chapter_num = num_span.get_text(strip=True)

        title_text = element.get("title")
        if not title_text:
            title_span = element.find("span", class_="catalog_title")
            title_text = (
                title_span.get_text(strip=True)
                if title_span
                else element.get_text(strip=True)
            )
        if chapter_num and title_text and not title_text.startswith(chapter_num):
            title = f"{chapter_num} {title_text}"
        else:
            title = title_text or chapter_num or "chapter"

        onclick = element.get("onclick", "")
        if "toOld" in onclick:
            args = re.findall(r"'([^']*)'", onclick)
            if len(args) >= 2:
                add_chapter(
                    chapters,
                    title,
                    build_studentstudy_url(args[1], params),
                    folder,
                )

    for element in soup.find_all(href=True):
        href = element["href"]
        if "studentstudy" not in href:
            continue
        title = element.get_text(strip=True) or element.get("title") or "chapter"
        add_chapter(chapters, title, urljoin(base_url, href), folder)

    for element in soup.find_all(attrs={"data-chapterid": True}):
        chapter_id = element["data-chapterid"]
        title = element.get_text(strip=True) or f"chapter-{chapter_id}"
        add_chapter(chapters, title, build_studentstudy_url(chapter_id, params), folder)

    for element in soup.find_all(attrs={"onclick": True}):
        onclick = element["onclick"]
        match = re.search(
            r"getTeacherAjax\(['\"](\d+)['\"],\s*['\"](\d+)['\"],\s*['\"](\d+)['\"]",
            onclick,
        )
        if not match:
            continue
        chapter_id, course_id, clazz_id = match.groups()
        params_with_match = dict(params)
        params_with_match["courseId"] = course_id
        params_with_match["clazzId"] = clazz_id
        title = element.get_text(strip=True) or element.get("title") or "chapter"
        add_chapter(
            chapters,
            title,
            build_studentstudy_url(chapter_id, params_with_match),
            folder,
        )

    return chapters


def merge_chapters(
    existing: list[dict[str, str]],
    new: Iterable[dict[str, str]],
) -> None:
    """Merge parsed chapters while preserving order."""
    seen = {chapter["url"] for chapter in existing}
    for chapter in new:
        if chapter["url"] not in seen:
            existing.append(chapter)
            seen.add(chapter["url"])


def parse_chapter_links(driver, course_url: str) -> list[dict[str, str]]:
    """Parse chapter links from the main document and accessible iframes."""
    driver.switch_to.default_content()
    chapters: list[dict[str, str]] = []
    merge_chapters(chapters, parse_chapters_from_html(driver.page_source, course_url))

    try:
        frame = WebDriverWait(driver, 5).until(
            ec.presence_of_element_located((By.ID, "frame_content-zj"))
        )
        driver.switch_to.frame(frame)
        merge_chapters(
            chapters,
            parse_chapters_from_html(driver.page_source, course_url),
        )
        driver.switch_to.default_content()
    except Exception:
        driver.switch_to.default_content()

    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for index in range(len(frames)):
        try:
            frames = driver.find_elements(By.TAG_NAME, "iframe")
            driver.switch_to.frame(frames[index])
            merge_chapters(
                chapters,
                parse_chapters_from_html(driver.page_source, driver.current_url),
            )
        except Exception:
            pass
        finally:
            driver.switch_to.default_content()

    return chapters


def normalize_url(src: str, base_url: str) -> str:
    """Convert protocol-relative or relative image URLs into absolute URLs."""
    if src.startswith("//"):
        return "https:" + src
    return urljoin(base_url, src)


def extract_images_from_current_frame(driver) -> list[str]:
    """Extract likely document image URLs from the current frame."""
    soup = BeautifulSoup(driver.page_source, "html.parser")
    images = []
    for img in soup.find_all("img"):
        src = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-original")
            or img.get("file")
        )
        if not src:
            continue
        src = normalize_url(src, driver.current_url)
        lower_src = src.lower()
        if any(marker in lower_src for marker in UI_IMAGE_MARKERS):
            continue
        if any(marker in lower_src for marker in DOCUMENT_IMAGE_MARKERS):
            images.append(src)

    ordered = []
    seen = set()
    for image_url in images:
        if image_url not in seen:
            ordered.append(image_url)
            seen.add(image_url)
    return ordered


def extract_object_ids_from_html(html: str, base_url: str) -> list[str]:
    """Extract likely Chaoxing object IDs from HTML and frame URLs."""
    soup = BeautifulSoup(html, "html.parser")
    object_ids = []

    for element in soup.find_all(True):
        for attr_name in ("src", "href", "data", "value", "data-src"):
            attr_value = element.get(attr_name)
            if not attr_value:
                continue
            attr_url = normalize_url(str(attr_value), base_url)
            query = parse_qs(urlparse(attr_url).query)
            for key, values in query.items():
                if key.lower() in ("objectid", "object_id"):
                    object_ids.extend(values)

    patterns = (
        r"(?i)objectid[\"']?\s*[:=]\s*[\"']?([0-9a-f]{24,64})",
        r"(?i)objectid=([0-9a-f]{24,64})",
        r"(?i)/download/([0-9a-f]{24,64})",
    )
    for pattern in patterns:
        object_ids.extend(re.findall(pattern, html))

    ordered = []
    seen = set()
    for object_id in object_ids:
        object_id = object_id.strip()
        if object_id and object_id not in seen:
            ordered.append(object_id)
            seen.add(object_id)
    return ordered


def collect_object_ids_from_frames(
    driver,
    max_depth: int,
    frame_delay: float,
    depth: int = 0,
) -> list[str]:
    """Recursively search current document and nested frames for object IDs."""
    object_ids = extract_object_ids_from_html(driver.page_source, driver.current_url)
    if depth >= max_depth:
        return object_ids

    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for index in range(len(frames)):
        try:
            frames = driver.find_elements(By.TAG_NAME, "iframe")
            driver.switch_to.frame(frames[index])
            time.sleep(frame_delay)
            object_ids.extend(
                collect_object_ids_from_frames(
                    driver,
                    max_depth=max_depth,
                    frame_delay=frame_delay,
                    depth=depth + 1,
                )
            )
            driver.switch_to.parent_frame()
        except Exception as exc:
            print(f"    Object ID frame {depth}.{index} failed: {exc}")
            try:
                driver.switch_to.parent_frame()
            except Exception:
                driver.switch_to.default_content()

    ordered = []
    seen = set()
    for object_id in object_ids:
        if object_id not in seen:
            ordered.append(object_id)
            seen.add(object_id)
    return ordered


def collect_image_urls_from_frames(
    driver,
    max_depth: int,
    frame_delay: float,
    depth: int = 0,
) -> list[str]:
    """Recursively search the current document and nested frames for images."""
    image_urls = extract_images_from_current_frame(driver)
    if image_urls or depth >= max_depth:
        return image_urls

    frames = driver.find_elements(By.TAG_NAME, "iframe")
    for index in range(len(frames)):
        try:
            frames = driver.find_elements(By.TAG_NAME, "iframe")
            driver.switch_to.frame(frames[index])
            time.sleep(frame_delay)
            image_urls = collect_image_urls_from_frames(
                driver,
                max_depth=max_depth,
                frame_delay=frame_delay,
                depth=depth + 1,
            )
            driver.switch_to.parent_frame()
            if image_urls:
                return image_urls
        except Exception as exc:
            print(f"    Frame {depth}.{index} failed: {exc}")
            try:
                driver.switch_to.parent_frame()
            except Exception:
                driver.switch_to.default_content()
    return []


def download_image(
    url: str,
    session: requests.Session,
    headers: dict[str, str],
) -> bytes | None:
    """Download one image URL."""
    try:
        response = session.get(url, headers=headers, timeout=20)
        if response.status_code == 200 and response.content:
            return response.content
        print(f"    Image download failed: {response.status_code} {url}")
    except Exception as exc:
        print(f"    Image download failed: {exc} {url}")
    return None


def download_images(
    image_urls: Iterable[str],
    session: requests.Session,
    headers: dict[str, str],
) -> list[bytes]:
    """Download image URLs into bytes."""
    image_data = []
    for image_url in image_urls:
        content = download_image(image_url, session, headers)
        if content:
            image_data.append(content)
    return image_data


def parse_content_disposition_filename(header_value: str | None) -> str | None:
    """Parse filename from a Content-Disposition header."""
    if not header_value:
        return None
    header_value = header_value.encode("latin-1", errors="ignore").decode(
        "utf-8",
        errors="replace",
    )
    filename_star = re.search(
        r"filename\*\s*=\s*UTF-8''([^;]+)",
        header_value,
        flags=re.IGNORECASE,
    )
    if filename_star:
        return sanitize_filename(unquote(filename_star.group(1)))

    filename = re.search(
        r"filename\s*=\s*\"?([^\";]+)\"?",
        header_value,
        flags=re.IGNORECASE,
    )
    if filename:
        decoded = unquote(filename.group(1))
        return sanitize_filename(decoded)
    return None


def infer_extension(
    content_type: str,
    content: bytes,
    default_extension: str,
) -> str:
    """Infer an output extension from HTTP metadata and file magic."""
    normalized_type = content_type.split(";")[0].strip().lower()
    if normalized_type in CONTENT_TYPE_EXTENSIONS:
        return CONTENT_TYPE_EXTENSIONS[normalized_type]
    if content.startswith(b"%PDF"):
        return ".pdf"
    if content.startswith(OFFICE_MAGIC):
        return ".ppt"
    if content.startswith(ZIP_MAGIC):
        return ".pptx"
    return default_extension


def is_probable_binary_download(response: requests.Response) -> bool:
    """Return true when a response looks like a file, not HTML or JSON."""
    if response.status_code != 200 or not response.content:
        return False
    content_type = response.headers.get("Content-Type", "").lower()
    if "text/html" in content_type or "application/json" in content_type:
        return False
    prefix = response.content[:200].lstrip().lower()
    return not prefix.startswith((b"<!doctype", b"<html", b"{"))


def parse_status_download_response(response: requests.Response) -> str | None:
    """Extract a source-file download URL from an ananas status response."""
    content_type = response.headers.get("Content-Type", "").lower()
    text = response.text.strip()
    if response.status_code != 200:
        return None
    if "json" not in content_type and not text.startswith(("{", "[")):
        return None

    try:
        payload = response.json()
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    if not isinstance(payload, dict):
        return None
    download_url = payload.get("download")
    if not isinstance(download_url, str) or not download_url:
        return None
    return download_url.replace("http://", "https://", 1)


def unique_path(path: Path) -> Path:
    """Return an unused path by adding a numeric suffix when needed."""
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Unable to find a free path near {path}")


def output_path_with_extension(base_path: Path, extension: str) -> Path:
    """Build an output path from a base path and extension."""
    if not extension.startswith("."):
        extension = "." + extension
    return base_path.with_suffix(extension)


def derive_direct_pdf_urls(image_urls: Iterable[str]) -> list[str]:
    """Derive Chaoxing converted-PDF URLs from document image URLs."""
    pdf_urls = []
    for image_url in image_urls:
        parsed = urlparse(image_url)
        match = re.search(
            r"(?P<prefix>/doc/.*/(?P<object_id>[0-9a-f]{32}))(?:/|$)",
            parsed.path,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        base = f"{parsed.scheme}://{parsed.netloc}{match.group('prefix')}"
        pdf_urls.append(
            f"{base}/pdf/{match.group('object_id')}.pdf"
        )

    ordered = []
    seen = set()
    for pdf_url in pdf_urls:
        if pdf_url not in seen:
            ordered.append(pdf_url)
            seen.add(pdf_url)
    return ordered


def download_binary_url(
    url: str,
    target_base_path: Path,
    session: requests.Session,
    headers: dict[str, str],
    default_extension: str,
) -> Path | None:
    """Download a binary URL into a target path if it returns a real file."""
    try:
        response = session.get(url, headers=headers, timeout=30)
    except Exception as exc:
        print(f"    Direct download failed: {exc} {url}")
        return None

    if not is_probable_binary_download(response):
        print(
            "    Direct download rejected: "
            f"{response.status_code} {response.headers.get('Content-Type', '')}"
        )
        return None

    filename = parse_content_disposition_filename(
        response.headers.get("Content-Disposition")
    )
    extension = infer_extension(
        response.headers.get("Content-Type", ""),
        response.content,
        default_extension,
    )
    if filename:
        target_path = target_base_path.with_name(filename)
    else:
        target_path = output_path_with_extension(target_base_path, extension)

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path = unique_path(target_path)
    target_path.write_bytes(response.content)
    return target_path


def wait_for_browser_download(
    download_dir: Path,
    before: set[Path],
    timeout: float,
) -> Path | None:
    """Wait for Chrome to finish a browser-managed download."""
    deadline = time.time() + timeout
    last_candidate = None
    stable_count = 0
    last_size = -1
    while time.time() < deadline:
        candidates = [
            path
            for path in download_dir.iterdir()
            if path not in before and not path.name.endswith(".crdownload")
        ]
        partials = list(download_dir.glob("*.crdownload"))
        if candidates and not partials:
            candidate = max(candidates, key=lambda path: path.stat().st_mtime)
            size = candidate.stat().st_size
            if candidate == last_candidate and size == last_size:
                stable_count += 1
            else:
                stable_count = 0
            last_candidate = candidate
            last_size = size
            if stable_count >= 2 and size > 0:
                return candidate
        time.sleep(1)
    return None


def browser_download_url(
    driver,
    url: str,
    download_dir: Path,
    timeout: float,
) -> Path | None:
    """Use the authenticated browser context to download one URL."""
    download_dir.mkdir(parents=True, exist_ok=True)
    before = {path for path in download_dir.iterdir()}
    try:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": str(download_dir)},
        )
    except Exception as exc:
        print(f"    Could not set Chrome download directory: {exc}")

    driver.execute_script(
        """
        const url = arguments[0];
        const link = document.createElement('a');
        link.href = url;
        link.download = '';
        document.body.appendChild(link);
        link.click();
        link.remove();
        """,
        url,
    )
    return wait_for_browser_download(download_dir, before, timeout)


def download_source_file(
    object_ids: Iterable[str],
    target_base_path: Path,
    session: requests.Session,
    headers: dict[str, str],
    driver=None,
    browser_download_timeout: float = 60,
) -> Path | None:
    """Try to download the original uploaded file from Chaoxing object IDs."""
    for object_id in object_ids:
        for url_template in SOURCE_DOWNLOAD_URLS:
            download_url = url_template.format(object_id=object_id)
            if "/ananas/status/" in download_url:
                try:
                    response = session.get(
                        download_url,
                        headers=headers,
                        timeout=20,
                    )
                except Exception as exc:
                    print(f"    Status request failed: {exc} {download_url}")
                    continue

                source_url = parse_status_download_response(response)
                if not source_url:
                    print(
                        "    Status request rejected: "
                        f"{response.status_code} "
                        f"{response.headers.get('Content-Type', '')}"
                    )
                    continue

                output_path = download_binary_url(
                    source_url,
                    target_base_path,
                    session,
                    headers,
                    default_extension=".pptx",
                )
                if output_path:
                    return output_path
                if driver is not None:
                    output_path = browser_download_url(
                        driver,
                        source_url,
                        target_base_path.parent,
                        timeout=browser_download_timeout,
                    )
                    if output_path:
                        return output_path
                continue

            output_path = download_binary_url(
                download_url,
                target_base_path,
                session,
                headers,
                default_extension=".pptx",
            )
            if output_path:
                return output_path
            if driver is not None:
                output_path = browser_download_url(
                    driver,
                    download_url,
                    target_base_path.parent,
                    timeout=browser_download_timeout,
                )
                if output_path:
                    return output_path
    return None


def download_direct_pdf(
    image_urls: Iterable[str],
    target_base_path: Path,
    session: requests.Session,
    headers: dict[str, str],
) -> Path | None:
    """Download Chaoxing's converted PDF when it can be derived from images."""
    for pdf_url in derive_direct_pdf_urls(image_urls):
        output_path = download_binary_url(
            pdf_url,
            target_base_path,
            session,
            headers,
            default_extension=".pdf",
        )
        if output_path:
            return output_path
    return None


def remove_alpha_channel(image_bytes: bytes) -> bytes:
    """Convert images with alpha channels to RGB PNG for PDF fallback."""
    with Image.open(io.BytesIO(image_bytes)) as image:
        if image.mode not in ("RGBA", "LA"):
            return image_bytes
        background = Image.new("RGB", image.size, (255, 255, 255))
        alpha = image.getchannel("A") if image.mode == "RGBA" else image.getchannel(1)
        background.paste(image.convert("RGB"), mask=alpha)
        output = io.BytesIO()
        background.save(output, format="PNG")
        return output.getvalue()


def write_pdf(image_data: list[bytes], pdf_path: Path) -> None:
    """Write images to a single PDF, retrying with RGB images if needed."""
    try:
        pdf_path.write_bytes(img2pdf.convert(image_data))
    except Exception:
        normalized = [remove_alpha_channel(content) for content in image_data]
        pdf_path.write_bytes(img2pdf.convert(normalized))


def make_pdf_path(course_dir: Path, chapter: dict[str, str], index: int) -> Path:
    """Build the chapter PDF path."""
    chapter_dir = course_dir / sanitize_filename(chapter.get("folder", "misc"), "misc")
    chapter_dir.mkdir(parents=True, exist_ok=True)
    safe_title = sanitize_filename(chapter["title"], f"chapter-{index + 1:02d}")
    if re.match(r"^\d", safe_title):
        filename = f"{safe_title}.pdf"
    else:
        filename = f"{index + 1:02d}_{safe_title}.pdf"
    return chapter_dir / filename


def process_chapter(
    driver,
    chapter: dict[str, str],
    pdf_path: Path,
    session: requests.Session,
    headers: dict[str, str],
    page_delay: float,
    frame_delay: float,
    max_frame_depth: int,
    download_mode: str,
    browser_download_timeout: float,
) -> bool:
    """Download one chapter into a source file, direct PDF, or image PDF."""
    driver.switch_to.default_content()
    driver.get(chapter["url"])
    time.sleep(page_delay)
    driver.switch_to.default_content()

    target_base_path = pdf_path.with_suffix("")
    image_urls: list[str] = []

    if download_mode in ("source", "prefer-source"):
        object_ids = collect_object_ids_from_frames(
            driver,
            max_depth=max_frame_depth,
            frame_delay=frame_delay,
        )
        driver.switch_to.default_content()
        print(f"  Found {len(object_ids)} candidate object IDs.")
        output_path = download_source_file(
            object_ids,
            target_base_path,
            session,
            headers,
            driver=driver,
            browser_download_timeout=browser_download_timeout,
        )
        if output_path:
            print(f"  Downloaded source file: {output_path}")
            return True
        if download_mode == "source":
            print("  Source file download failed.")
            return False

    if download_mode in ("direct-pdf", "prefer-direct-pdf", "prefer-source"):
        image_urls = collect_image_urls_from_frames(
            driver,
            max_depth=max_frame_depth,
            frame_delay=frame_delay,
        )
        driver.switch_to.default_content()
        print(f"  Found {len(image_urls)} image URLs.")
        output_path = download_direct_pdf(
            image_urls,
            target_base_path,
            session,
            headers,
        )
        if output_path:
            print(f"  Downloaded direct PDF: {output_path}")
            return True
        if download_mode == "direct-pdf":
            print("  Direct PDF download failed.")
            return False

    if pdf_path.exists():
        print(f"  Exists, skipping: {pdf_path}")
        return True

    if not image_urls:
        image_urls = collect_image_urls_from_frames(
            driver,
            max_depth=max_frame_depth,
            frame_delay=frame_delay,
        )
        driver.switch_to.default_content()

    if not image_urls:
        print("  No document images found.")
        return False

    print(f"  Found {len(image_urls)} image URLs.")
    image_data = download_images(image_urls, session, headers)
    if not image_data:
        print("  No images downloaded.")
        return False

    print(f"  Writing PDF: {pdf_path}")
    write_pdf(image_data, pdf_path)
    return True


def run(args: argparse.Namespace) -> int:
    """Run the extraction workflow."""
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    driver = build_driver(args.browser, args.headless, args.user_data_dir)

    try:
        maybe_wait_for_login(
            driver,
            args.login_url,
            args.course_url,
            args.skip_login,
            args.cookie_file,
        )
        time.sleep(args.page_delay)
        if "login" in (driver.title or "").lower() or driver.title == "用户登录":
            if not args.skip_login:
                print("The target page is still a login page. Login is required.")
                return 2
            print("Saved cookies are missing or expired. Manual login is required.")
            input("Press Enter after login is complete...")
            driver.get(args.course_url)
            time.sleep(args.page_delay)
            title = driver.title or ""
            if "login" in title.lower() or title == "用户登录":
                print("The target page is still a login page. Login is required.")
                return 2

        course_dir = detect_course_dir(driver, output_dir)
        save_cookie_file(driver, args.cookie_file)
        session, headers = copy_cookies_to_session(driver)
        chapters = []
        if args.current_page_only:
            chapters.append(
                {
                    "title": sanitize_filename(driver.title, "current-page"),
                    "url": driver.current_url,
                    "cid": driver.current_url,
                    "folder": "current-page",
                }
            )
        else:
            chapters = parse_chapter_links(driver, args.course_url)
            if not chapters:
                print("No chapter links found.")
                print("Retry with --current-page-only for a direct chapter page.")
                return 3

        if args.limit:
            chapters = chapters[: args.limit]
        print(f"Total chapters to process: {len(chapters)}")
        if args.dry_run:
            for index, chapter in enumerate(chapters, start=1):
                print(f"{index:03d}. {chapter['folder']} / {chapter['title']}")
                print(f"     {chapter['url']}")
            return 0

        successes = 0
        for index, chapter in enumerate(chapters):
            print("")
            print(f"[{index + 1}/{len(chapters)}] {chapter['title']}")
            pdf_path = make_pdf_path(course_dir, chapter, index)
            if process_chapter(
                driver,
                chapter,
                pdf_path,
                session,
                headers,
                page_delay=args.page_delay,
                frame_delay=args.frame_delay,
                max_frame_depth=args.max_frame_depth,
                download_mode=args.download_mode,
                browser_download_timeout=args.browser_download_timeout,
            ):
                successes += 1
        print("")
        print(f"Finished. PDFs created or present: {successes}/{len(chapters)}")
        return 0
    finally:
        if args.keep_browser_open:
            print("Browser left open by request.")
        else:
            driver.quit()


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Extract Chaoxing course PPT/document images into PDFs."
    )
    parser.add_argument("--course-url", required=True, help="Chaoxing course page URL.")
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated course folders.",
    )
    parser.add_argument(
        "--browser",
        choices=("chrome", "edge"),
        default="chrome",
        help="Browser to automate.",
    )
    parser.add_argument("--login-url", default=LOGIN_URL, help="Chaoxing login URL.")
    parser.add_argument(
        "--skip-login",
        action="store_true",
        help="Skip the login prompt; useful with --user-data-dir.",
    )
    parser.add_argument(
        "--user-data-dir",
        default=DEFAULT_USER_DATA_DIR,
        help="Browser profile directory for reusing an existing login session.",
    )
    parser.add_argument(
        "--cookie-file",
        default=DEFAULT_COOKIE_FILE,
        help="JSON file used to save and restore Chaoxing session cookies.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser headless. Use only with an already logged-in profile.",
    )
    parser.add_argument(
        "--current-page-only",
        action="store_true",
        help="Extract only the currently loaded target page.",
    )
    parser.add_argument("--limit", type=int, help="Process only the first N chapters.")
    parser.add_argument("--dry-run", action="store_true", help="List chapters only.")
    parser.add_argument(
        "--download-mode",
        choices=(
            "image-pdf",
            "direct-pdf",
            "source",
            "prefer-source",
            "prefer-direct-pdf",
        ),
        default="prefer-direct-pdf",
        help=(
            "Download strategy: image-pdf rebuilds from page images; "
            "direct-pdf downloads Chaoxing's converted PDF; source tries "
            "the original uploaded file; prefer modes fall back to image-pdf."
        ),
    )
    parser.add_argument(
        "--page-delay",
        type=float,
        default=4.0,
        help="Seconds to wait after page navigation.",
    )
    parser.add_argument(
        "--frame-delay",
        type=float,
        default=1.5,
        help="Seconds to wait after switching frames.",
    )
    parser.add_argument(
        "--max-frame-depth",
        type=int,
        default=4,
        help="Maximum nested iframe depth to inspect.",
    )
    parser.add_argument(
        "--browser-download-timeout",
        type=float,
        default=60,
        help="Seconds to wait for browser-managed source-file downloads.",
    )
    parser.add_argument(
        "--keep-browser-open",
        action="store_true",
        help="Leave the browser open after the run.",
    )
    return parser


def main() -> int:
    _configure_stdout()
    parser = build_arg_parser()
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
