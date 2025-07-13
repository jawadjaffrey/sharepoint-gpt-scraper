from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from urllib.parse import unquote
import time
import traceback

app = Flask(__name__)
last_called = 0
cooldown = 15  # seconds

@app.route('/get_sharepoint_files', methods=['POST'])
def get_files():
    global last_called
    now = time.time()
    if now - last_called < cooldown:
        wait_time = int(cooldown - (now - last_called))
        return jsonify({
            "error": "Rate limit exceeded",
            "message": f"Please wait {wait_time} more second(s) before retrying."
        }), 429

    try:
        data = request.get_json()
        folder_url = unquote(data.get("shared_folder_url", ""))  # ✅ Fix applied here
        ext_filter = data.get("file_extension_filter", "all").lower()

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920x1080')
        options.binary_location = "/usr/bin/chromium"
        options.add_argument('--user-agent=Mozilla/5.0')

        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)

        driver.get(folder_url)
        time.sleep(15)  # Wait for JS to load content

        links = driver.find_elements(By.TAG_NAME, "a")
        files = []

        for link in links:
            href = link.get_attribute("href")
            text = link.text.strip()
            if href and ("download" in href.lower() or "guestaccess" in href.lower()):
                if ext_filter == "all" or text.lower().endswith(f".{ext_filter}"):
                    files.append({"filename": text, "download_link": href})

        driver.quit()

        return jsonify({
            "status": "success",
            "total_files_found": len(files),
            "files": files
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": "Unexpected server error",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
