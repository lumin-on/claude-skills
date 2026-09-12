#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print an HTML report to PDF with a locally installed Chromium browser (Chrome or Edge), headless.

Why a browser: the report is styled HTML with Korean text and inline SVG charts; a browser's print engine
keeps the layout identical, while pure-Python PDF libraries either need native GTK (weasyprint) or a
hand-built layout (reportlab). Windows 11 ships Edge and most machines have Chrome.

Quirk handled here: the Edge executable under "Program Files (x86)" is a launcher that hands off to a
background process and returns immediately, so we poll for the PDF instead of trusting the exit.
Chrome is tried first because it prints synchronously.

Usage:
  python export_pdf.py report.html [report.pdf] [--browser "C:/path/to/chrome.exe"]
"""
import argparse, os, pathlib, shutil, subprocess, tempfile, time

CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]
NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"]


def find_browsers(explicit=None):
    if explicit:
        return [explicit]
    found = [p for p in CANDIDATES if os.path.isfile(p)]
    for n in NAMES:
        w = shutil.which(n)
        if w and w not in found:
            found.append(w)
    return found


def _try(exe, url, pdf_path, wait):
    profile = tempfile.mkdtemp(prefix="kakao-pdf-")
    cmd = [exe, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
           f"--user-data-dir={profile}", "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", url]
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=wait)
    except subprocess.TimeoutExpired:
        pass
    deadline = time.time() + wait
    while time.time() < deadline:  # Edge launcher returns early; wait for the file to land and settle
        if os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 1000:
            s = os.path.getsize(pdf_path); time.sleep(0.7)
            if os.path.getsize(pdf_path) == s:
                shutil.rmtree(profile, ignore_errors=True); return True
        time.sleep(0.4)
    shutil.rmtree(profile, ignore_errors=True)
    return False


def html_to_pdf(html_path, pdf_path=None, browser=None, wait=60):
    html_path = os.path.abspath(html_path)
    pdf_path = os.path.abspath(pdf_path or os.path.splitext(html_path)[0] + ".pdf")
    if os.path.isfile(pdf_path):
        os.remove(pdf_path)
    browsers = find_browsers(browser)
    if not browsers:
        raise RuntimeError("no Chromium-based browser found (Chrome/Edge). Install one or pass --browser <path>.")
    url = pathlib.Path(html_path).as_uri()
    for exe in browsers:
        if _try(exe, url, pdf_path, wait):
            return pdf_path
    raise RuntimeError("PDF was not produced by any of: " + ", ".join(browsers))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html"); ap.add_argument("pdf", nargs="?"); ap.add_argument("--browser")
    a = ap.parse_args()
    out = html_to_pdf(a.html, a.pdf, a.browser)
    print(f"wrote {out} ({os.path.getsize(out):,} bytes)")


if __name__ == "__main__":
    main()
