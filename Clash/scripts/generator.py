import os
import sys
import requests
import time
from urllib.parse import urlparse, quote_plus

# --- تعیین مسیر اصلی پوشه 'Clash' ---
# این خط مسیر دقیق پوشه 'Clash' را محاسبه می‌کند.
# فرض بر این است که generator.py در 'Clash/scripts/' قرار دارد.
CLASH_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- تعریف مسیر فایل‌ها و پوشه‌ها (نسبت به CLASH_ROOT_DIR) ---
TEMPLATE_FILE = os.path.join(CLASH_ROOT_DIR, 'template.yaml')
SUBS_FILE = os.path.join(CLASH_ROOT_DIR, 'subscriptions.txt')
FORMAT_FILE = os.path.join(CLASH_ROOT_DIR, 'format.txt')
OUTPUT_DIR = os.path.join(CLASH_ROOT_DIR, 'output')
PROVIDERS_DIR = os.path.join(CLASH_ROOT_DIR, 'providers')
README_FILE = os.path.join(CLASH_ROOT_DIR, 'README.md') # README.md در ریشه پوشه Clash
GITHUB_REPO = os.environ.get('GITHUB_REPOSITORY')

# --- محتوای پایه برای README.md در صورت عدم وجود فایل ---
# این متن دقیقاً همان چیزی است که شما می‌خواهید در README جدید قرار گیرد.
# شامل نشانگرهای START_LINKS و END_LINKS است.
BASE_README_CONTENT = """
# 🏭 کارخانه کانفیگ کلش | Clash Config Factory

[![Workflowname](https://github.com/DiDiten/ScrapeAndCategorize/actions/workflows/main.yml/badge.svg)](https://github.com/DiDiten/ScrapeAndCategorize/actions/workflows/main.yml)

این مخزن به صورت خودکار، فایل‌های کانفیگ پایدار و به‌روز برای **Clash** از روی لیستی از لینک‌های اشتراک (Subscription) شما می‌سازد. هدف اصلی این پروژه، داشتن کانفیگ‌هایی است که حتی در صورت از دسترس خارج شدن لینک اشتراک اصلی، همچنان فعال باقی بمانند.

---

<!-- START_LINKS -->
<!-- END_LINKS -->

---

## ✨ نحوه عملکرد

این سیستم تماماً خودکار است و با استفاده از **GitHub Actions** کار می‌کند. فرآیند به شرح زیر است:

1.  **خواندن قالب**: در هر بار اجرا، اسکریپت ابتدا **قالب کلی** کانفیگ شما را از فایل `template.yaml` (واقع در `Clash/template.yaml`) می‌خواند.
2.  **خواندن فرمت لینک**: سپس به فایل `format.txt` (واقع در `Clash/format.txt`) مراجعه کرده و **قالب پردازش لینک** را از آنجا می‌خواند. این قالب مشخص می‌کند که لینک‌های اشتراک شما چگونه باید پردازش شوند (مثلاً با استفاده از یک سرویس مبدل).
3.  **پردازش لینک‌ها**: اسکریپت به سراغ فایل `subscriptions.txt` (واقع در `Clash/subscriptions.txt`) رفته و لینک‌های اشتراک شما را یک به یک برمی‌دارد. هر لینک را طبق فرمت مرحله قبل، پردازش کرده و **لینک نهایی** را می‌سازد.
4.  **دانلود و ذخیره محتوا**: محتوای هر لینک نهایی دانلود شده و به صورت یک فایل متنی مجزا در پوشه `Clash/providers/` ذخیره می‌شود. این کار باعث **پایداری ابدی** کانفیگ شما می‌شود.
5.  **تولید کانفیگ نهایی**: در نهایت، اسکریپت با استفاده از قالب مرحله اول، یک فایل کانفیگ کامل در پوشه `Clash/output/` می‌سازد که مستقیماً به محتوای دانلود شده در مخزن خودتان اشاره می‌کند.
6.  **به‌روزرسانی README**: این فایل `Clash/README.md` به طور خودکار با لیست جدید کانفیگ‌های تولید شده به‌روز می‌شود.

---

## 🚀 نحوه استفاده و شخصی‌سازی

شما می‌توانید این مخزن را به سادگی برای خودتان شخصی‌سازی کنید.

### ۱. افزودن لینک‌های اشتراک

فایل `subscriptions.txt` (واقع در `Clash/subscriptions.txt`) را باز کرده و لینک‌های اشتراک خود را در آن وارد کنید.

* **حالت عادی (نام خودکار):**
    ```
    [https://example.com/your-sub-link.txt](https://example.com/your-sub-link.txt)
    ```
* **با نام دلخواه (توصیه می‌شود):**
    ```
    [https://example.com/your-sub-link.txt,My-Custom-Name](https://example.com/your-sub-link.txt,My-Custom-Name)
    ```

### ۲. تغییر سرویس مبدل لینک (اختیاری)

اگر می‌خواهید از یک سرویس دیگر برای پردازش لینک‌ها استفاده کنید، فایل `format.txt` (واقع در `Clash/format.txt`) را ویرایش کنید. فقط مطمئن شوید که محل قرارگیری لینک اشتراک اصلی را با `[URL]` مشخص کرده‌اید.

**مثال `format.txt`:**

https://example.com/convert?url=[URL]&param=value
"""


def get_filename_from_url(url):
    """تابعی برای استخراج نام فایل از URL"""
    path = urlparse(url).path
    filename = os.path.basename(path)
    return os.path.splitext(filename)[0]


def update_readme(output_files):
    """تابعی برای به‌روزرسانی فایل README.md"""
    if not GITHUB_REPO:
        sys.exit("Critical Error: GITHUB_REPOSITORY environment variable is not set.")

    print(f"Updating README.md for repository: {GITHUB_REPO}")

    readme_content = ""
    # ابتدا تلاش می کنیم فایل README را بخوانیم. اگر وجود نداشت، آن را ایجاد می کنیم.
    try:
        with open(README_FILE, 'r', encoding='utf-8') as f:
            readme_content = f.read()
    except FileNotFoundError:
        print(f"Warning: '{README_FILE}' not found. Creating a new one with base content.")
        os.makedirs(os.path.dirname(README_FILE), exist_ok=True) # اطمینان از وجود پوشه والد
        with open(README_FILE, 'w', encoding='utf-8') as f:
            f.write(BASE_README_CONTENT.strip()) # نوشتن محتوای پایه
        readme_content = BASE_README_CONTENT.strip() # محتوای جدید را برای پردازش قرار می دهیم

    start_marker = "<!-- START_LINKS -->"
    end_marker = "<!-- END_LINKS -->"

    if start_marker not in readme_content or end_marker not in readme_content:
        # اگر نشانگرها حتی در فایل تازه ایجاد شده هم نباشند، خطای بحرانی می دهیم.
        # این حالت نباید رخ دهد اگر BASE_README_CONTENT به درستی تعریف شده باشد.
        sys.exit(f"CRITICAL ERROR: Markers '{start_marker}' and/or '{end_marker}' not found in {README_FILE}. Please ensure they are present in the base content or the existing file.")

    links_md_content = "## 🔗 لینک‌های کانفیگ آماده (Raw)\n\n"
    links_md_content += "برای استفاده، لینک‌های زیر را مستقیما در کلش کپی کنید.\n\n"
    for filename in sorted(output_files):
        clash_dir_name = os.path.basename(CLASH_ROOT_DIR)
        output_sub_dir_name = os.path.basename(OUTPUT_DIR)
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{clash_dir_name}/{output_sub_dir_name}/{filename}"
        title = os.path.splitext(filename)[0]
        links_md_content += f"* **{title}**: `{raw_url}`\n"

    # تقسیم متن README بر اساس نشانگرها
    before_part = readme_content.split(start_marker)[0]
    after_part = readme_content.split(end_marker)[1]

    new_readme_content = (
        before_part + start_marker + "\n\n" +
        links_md_content + "\n" + end_marker + after_part
    )

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(new_readme_content)

    print("README.md updated successfully.")


def main():
    """
    تابع اصلی که از جایگزینی متن ساده و تلاش مجدد برای دانلود استفاده می‌کند.
    """
    print("Starting robust generation process with retry logic...")
    try:
        with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
            template_content = f.read()

        with open(FORMAT_FILE, 'r', encoding='utf-8') as f:
            format_string = f.read().strip()

        if "[URL]" not in format_string:
            print(f"Warning: Placeholder [URL] not found in {FORMAT_FILE}.")
            format_string = "[URL]"

    except FileNotFoundError as e:
        sys.exit(f"CRITICAL ERROR: A required file is missing: {e.filename}. Make sure it's in the '{os.path.basename(CLASH_ROOT_DIR)}' directory.")

    os.makedirs(CLASH_ROOT_DIR, exist_ok=True) # اطمینان از وجود پوشه اصلی Clash
    os.makedirs(OUTPUT_DIR, exist_ok=True) # ایجاد پوشه output داخل Clash
    os.makedirs(PROVIDERS_DIR, exist_ok=True) # ایجاد پوشه providers داخل Clash

    try:
        with open(SUBS_FILE, 'r', encoding='utf-8') as f:
            subscriptions = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        sys.exit(f"CRITICAL ERROR: Subscription file '{SUBS_FILE}' not found. Make sure it's in the '{os.path.basename(CLASH_ROOT_DIR)}' directory.")

    generated_files = []

    for sub_line in subscriptions:
        custom_name = None
        if ',' in sub_line:
            original_url, custom_name = [part.strip() for part in sub_line.split(',', 1)]
        else:
            original_url = sub_line

        file_name_base = custom_name if custom_name else get_filename_from_url(original_url)
        if not file_name_base:
            print(f"Warning: Could not determine a filename for URL: {original_url}. Skipping.")
            continue

        wrapped_url = format_string.replace("[URL]", quote_plus(original_url))

        print(f"Processing: {original_url}")
        print(f"  -> Wrapped URL: {wrapped_url}")

        provider_filename = f"{file_name_base}.txt"
        provider_path = os.path.join(PROVIDERS_DIR, provider_filename)

        response = None
        max_retries = 3
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                response = requests.get(wrapped_url, timeout=45)
                response.raise_for_status()
                print(f"  -> Successfully downloaded on attempt {attempt + 1}.")
                break
            except requests.RequestException as e:
                print(f"  -> Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    print(f"  -> Waiting for {retry_delay} seconds before retrying...")
                    time.sleep(retry_delay)
                else:
                    print(f"  -> All retries failed. Skipping this subscription.")

        if response is None or not response.ok:
            continue

        with open(provider_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"  -> Successfully saved content to {provider_path}")

        if not GITHUB_REPO:
            continue

        clash_dir_name = os.path.basename(CLASH_ROOT_DIR)
        providers_sub_dir_name = os.path.basename(PROVIDERS_DIR)
        raw_provider_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{clash_dir_name}/{providers_sub_dir_name}/{provider_filename}"

        modified_content = template_content
        modified_content = modified_content.replace("%%URL_PLACEHOLDER%%", raw_provider_url)
        relative_provider_path = os.path.relpath(provider_path, start=OUTPUT_DIR)
        modified_content = modified_content.replace("%%PATH_PLACEHOLDER%%", f"./{relative_provider_path}")

        output_filename = f"{file_name_base}.yaml"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)

        generated_files.append(output_filename)
        print(f"  -> Generated final config: {output_path}\n")

    if generated_files:
        update_readme(generated_files)

if __name__ == "__main__":
    main()

