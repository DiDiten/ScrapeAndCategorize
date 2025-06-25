import os
import sys
import requests
import time
from urllib.parse import urlparse, quote_plus

# --- Determine the base directory for 'clash' ---
# This correctly calculates the path to the 'Clash' directory
# by going up two levels from the current script's location (clash/scripts/generator.py)
# e.g., /home/runner/work/repo/repo/Clash/scripts/generator.py -> /home/runner/work/repo/repo/Clash/scripts -> /home/runner/work/repo/repo/Clash
CLASH_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- File and Folder Names (paths are now relative to CLASH_ROOT_DIR) ---
# These paths directly point to files and directories within the 'Clash' folder.
TEMPLATE_FILE = os.path.join(CLASH_ROOT_DIR, 'template.yaml')
SUBS_FILE = os.path.join(CLASH_ROOT_DIR, 'subscriptions.txt')
FORMAT_FILE = os.path.join(CLASH_ROOT_DIR, 'format.txt')
OUTPUT_DIR = os.path.join(CLASH_ROOT_DIR, 'output')
PROVIDERS_DIR = os.path.join(CLASH_ROOT_DIR, 'providers')
README_FILE = os.path.join(CLASH_ROOT_DIR, 'README.md') # README.md is now expected directly inside the 'Clash' directory
GITHUB_REPO = os.environ.get('GITHUB_REPOSITORY')


def get_filename_from_url(url):
    """Function to extract filename from URL"""
    path = urlparse(url).path
    filename = os.path.basename(path)
    return os.path.splitext(filename)[0]


def update_readme(output_files):
    """Function to update the README.md file"""
    if not GITHUB_REPO:
        sys.exit("Critical Error: GITHUB_REPOSITORY environment variable is not set.")

    print(f"Updating README.md for repository: {GITHUB_REPO}")

    links_md_content = "## 🔗 لینک‌های کانفیگ آماده (Raw)\n\n"
    links_md_content += "برای استفاده، لینک‌های زیر را مستقیما در کلش کپی کنید.\n\n"
    for filename in sorted(output_files):
        # The GitHub raw URL needs to reflect the full path from the repo root
        # e.g., https://raw.githubusercontent.com/DiDiten/ScrapeAndCategorize/main/Clash/output/filename.yaml
        clash_dir_name = os.path.basename(CLASH_ROOT_DIR) # This will correctly be 'Clash'
        output_sub_dir_name = os.path.basename(OUTPUT_DIR) # This will correctly be 'output'
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{clash_dir_name}/{output_sub_dir_name}/{filename}"
        title = os.path.splitext(filename)[0]
        links_md_content += f"* **{title}**: `{raw_url}`\n"

    try:
        # Use the correct path for README_FILE, which is in CLASH_ROOT_DIR
        with open(README_FILE, 'r', encoding='utf-8') as f:
            readme_content = f.read()
    except FileNotFoundError:
        sys.exit(f"CRITICAL ERROR: The '{README_FILE}' file was not found. Make sure it's in the '{os.path.basename(CLASH_ROOT_DIR)}' directory.")

    start_marker = ""
    end_marker = ""

    if start_marker not in readme_content or end_marker not in readme_content:
        sys.exit(f"CRITICAL ERROR: Markers not found in {README_FILE}. Please add '' and '' to {README_FILE}.")

    before_part = readme_content.split(start_marker)[0]
    after_part = readme_content.split(end_marker)[1]

    new_readme_content = (
        before_part + start_marker + "\n\n" +
        links_md_content + "\n" + end_marker + after_part
    )

    # Write to the correct README_FILE path
    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(new_readme_content)

    print("README.md updated successfully.")


def main():
    """
    Main function that uses simple text replacement and retry logic for downloads.
    """
    print("Starting robust generation process with retry logic...")
    try:
        # Use the correct paths for input files
        with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
            template_content = f.read()

        with open(FORMAT_FILE, 'r', encoding='utf-8') as f:
            format_string = f.read().strip()

        if "[URL]" not in format_string:
            print(f"Warning: Placeholder [URL] not found in {FORMAT_FILE}.")
            format_string = "[URL]"

    except FileNotFoundError as e:
        sys.exit(f"CRITICAL ERROR: A required file is missing: {e.filename}. Make sure it's in the '{os.path.basename(CLASH_ROOT_DIR)}' directory.")

    # Create the main 'Clash' directory and then its subdirectories
    os.makedirs(CLASH_ROOT_DIR, exist_ok=True) # Ensure 'Clash' exists (redundant if repo structure is fixed, but harmless)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(PROVIDERS_DIR, exist_ok=True)

    try:
        # Use the correct path for SUBS_FILE
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
        provider_path = os.path.join(PROVIDERS_DIR, provider_filename) # This path will be 'Clash/providers/...'

        # --- Key section: Retry logic ---
        response = None
        max_retries = 3
        retry_delay = 5  # 5 seconds delay between each attempt

        for attempt in range(max_retries):
            try:
                response = requests.get(wrapped_url, timeout=45) # Increased timeout
                response.raise_for_status() # Check for HTTP errors like 4xx/5xx
                print(f"  -> Successfully downloaded on attempt {attempt + 1}.")
                break  # Exit loop if successful
            except requests.RequestException as e:
                print(f"  -> Attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    print(f"  -> Waiting for {retry_delay} seconds before retrying...")
                    time.sleep(retry_delay)
                else:
                    print(f"  -> All retries failed. Skipping this subscription.")

        # If download failed after all retries, skip to next link
        if response is None or not response.ok:
            continue

        # Save downloaded content
        with open(provider_path, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"  -> Successfully saved content to {provider_path}")

        if not GITHUB_REPO:
            continue

        # The raw_provider_url needs to include CLASH_ROOT_DIR (i.e., 'Clash')
        # e.g., https://raw.githubusercontent.com/DiDiten/ScrapeAndCategorize/main/Clash/providers/filename.txt
        clash_dir_name = os.path.basename(CLASH_ROOT_DIR)
        providers_sub_dir_name = os.path.basename(PROVIDERS_DIR)
        raw_provider_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{clash_dir_name}/{providers_sub_dir_name}/{provider_filename}"


        modified_content = template_content
        modified_content = modified_content.replace("%%URL_PLACEHOLDER%%", raw_provider_url)
        # The PATH_PLACEHOLDER needs to be relative from the output file.
        # Output files are in OUTPUT_DIR, provider files are in PROVIDERS_DIR.
        # Both OUTPUT_DIR and PROVIDERS_DIR are inside CLASH_ROOT_DIR.
        # So, the relative path from 'Clash/output' to 'Clash/providers' would be '../providers/filename.txt'
        relative_provider_path = os.path.relpath(provider_path, start=OUTPUT_DIR)
        modified_content = modified_content.replace("%%PATH_PLACEHOLDER%%", f"./{relative_provider_path}")

        output_filename = f"{file_name_base}.yaml"
        output_path = os.path.join(OUTPUT_DIR, output_filename) # This path will be 'Clash/output/...'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(modified_content)

        generated_files.append(output_filename)
        print(f"  -> Generated final config: {output_path}\n")

    if generated_files:
        update_readme(generated_files)

if __name__ == "__main__":
    main()
