import os
import sys
import requests
import time
from urllib.parse import urlparse, quote_plus

# --- تعریف پوشه اصلی clash ---
CLASH_DIR = 'clash' # پوشه جدید ما

# --- نام فایل‌ها و پوشه‌ها (مسیردهی جدید) ---
TEMPLATE_FILE = os.path.join(CLASH_DIR, 'template.yaml')
SUBS_FILE = os.path.join(CLASH_DIR, 'subscriptions.txt')
FORMAT_FILE = os.path.join(CLASH_DIR, 'format.txt')
OUTPUT_DIR = os.path.join(CLASH_DIR, 'output')
PROVIDERS_DIR = os.path.join(CLASH_DIR, 'providers')
README_FILE = os.path.join(CLASH_DIR, 'README.md') # README.md هم به داخل clash میرود
GITHUB_REPO = os.environ.get('GITHUB_REPOSITORY')


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

    links_md_content = "## 🔗 لینک‌های کانفیگ آماده (Raw)\n\n"
    links_md_content += "برای استفاده، لینک‌های زیر را مستقیما در کلش کپی کنید.\n\n"
    for filename in sorted(output_files):
        # تغییر در اینجا: اضافه کردن CLASH_DIR به مسیر URL
        # ما فقط نام "output" را نیاز داریم، نه کل مسیر "clash/output"
        output_sub_dir_name = os.path.basename(OUTPUT_DIR)
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{CLASH_DIR}/{output_sub_dir_name}/{filename}"
        title = os.path.splitext(filename)[0]
        links_md_content += f"* **{title}**: `{raw_url}`\n"

    try:
        # تغییر در اینجا: استفاده از مسیر جدید README_FILE
        with open(README_FILE, 'r', encoding='utf-8') as f:
            readme_content = f.read()
    except FileNotFoundError:
        sys.exit(f"CRITICAL ERROR: The '{README_FILE}' file was not found. Make sure it's in the '{CLASH_DIR}' directory.")

    start_marker = ""
    end_marker = ""

    if start_marker not in readme_content or end_marker not in readme_content:
        sys.exit(f"CRITICAL ERROR: Markers not found in {README_FILE}.")

    before_part = readme_content.split(start_marker)[0]
    after_part = readme_content.split(end_marker)[1]

    new_readme_content = (
        before_part + start_marker + "\n\n" +
        links_md_content + "\n" + end_marker + after_part
    )

    # تغییر در اینجا: استفاده از مسیر جدید README_FILE
    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(new_readme_content)

    print("README.md updated successfully.")


def main():
    """
    تابع اصلی که از جایگزینی متن ساده و تلاش مجدد برای دانلود استفاده می‌کند.
    """
    print("Starting robust generation process with retry logic...")
    try:
        # تغییر در اینجا: استفاده از مسیرهای جدید فایل‌ها
        with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
            template_content = f.read()

        with open(FORMAT_FILE, 'r', encoding='utf-8') as f:
            format_string = f.read().strip()

        if "[URL]" not in format_string:
            print(f"Warning: Placeholder [URL] not found in {FORMAT_FILE}.")
            format_string = "[URL]"

    except FileNotFoundError as e:
        sys.exit(f"CRITICAL ERROR: A required file is missing: {e.filename}. Make sure it's in the '{CLASH_DIR}' directory.")

    # ایجاد پوشه اصلی 'clash' و سپس زیرپوشه‌های آن
    os.makedirs(CLASH_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PROVIDERS_DIR, exist_ok=True)

    try:
        # تغییر در اینجا: استفاده از مسیر جدید SUBS_FILE
        with open(SUBS_FILE, 'r', encoding='utf-8') as f:
            subscriptions = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        sys.exit(f"CRITICAL ERROR: Subscription file '{SUBS_FILE}' not found. Make sure it's in the '{CLASH_DIR}' directory.")

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
        provider_path = os.path.join(PROVIDERS_DIR, provider_filename) # این مسیر حالا به 'clash/providers/...' اشاره میکند

        # --- بخش کلیدی و جدید: منطق تلاش مجدد ---
        response = None
        max_retries = 3
        retry_delay = 5  # 5 ثانیه تأخیر بین هر تلاش

        for attempt in range(max_retries):
            try:
                response = requests.get(wrapped_url, timeout=45) # افزایش زمان انتظار
                response.raise_for_status() # بررسی خطاهای HTTP مثل 4xx/5xx
                print(f"  -> Successfully downloaded on attempt {attempt + 1}.")
                break  # اگر موفق بود، از حلقه خارج شو
            except requests.RequestException as e:
                print(f"  -> Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    print(f"  -> Waiting for {retry_delay} seconds before retrying...")
                    time.sleep(retry_delay)
                else:
                    print(f"  -> All retries failed. Skipping this subscription.")

        # اگر بعد از تمام تلاش‌ها، دانلود ناموفق بود، به لینک بعدی برو
        if response is None or not response.ok:
            continue

        # ذخیره محتوای دانلود شده
        with open(provider_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"  -> Successfully saved content to {provider_path}")

        if not GITHUB_REPO:
            continue

        # تغییر در اینجا: مسیر raw_provider_url باید شامل CLASH_DIR باشد
        # فرض میکنیم GITHUB_REPO به ریشه مخزن اشاره میکند
        # پس مسیر در گیت‌هاب خواهد بود: main/clash/providers/filename.txt
        raw_provider_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{CLASH_DIR}/{os.path.basename(PROVIDERS_DIR)}/{provider_filename}"


        modified_content = template_content
        modified_content = modified_content.replace("%%URL_PLACEHOLDER%%", raw_provider_url)
        # تغییر در اینجا: مسیر PATH_PLACEHOLDER باید نسبت به فایل نهایی باشد
        # اگر فایل نهایی در clash/output است و provider در clash/providers، مسیر نسبی اینگونه میشود
        relative_provider_path = os.path.relpath(provider_path, OUTPUT_DIR)
        modified_content = modified_content.replace("%%PATH_PLACEHOLDER%%", f"./{relative_provider_path}")

        output_filename = f"{file_name_base}.yaml"
        output_path = os.path.join(OUTPUT_DIR, output_filename) # این مسیر حالا به 'clash/output/...' اشاره میکند
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)

        generated_files.append(output_filename)
        print(f"  -> Generated final config: {output_path}\n")

    if generated_files:
        update_readme(generated_files)

if __name__ == "__main__":
    main()
