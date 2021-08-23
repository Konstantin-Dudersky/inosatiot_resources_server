"""
Загрузка статических библиотек из интернета
"""

import urllib.request
from pathlib import Path
bootstrap_version = '5.0.2'


def download_file(download_url, filename):
    response = urllib.request.urlopen(urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'}))
    file = open(filename, 'wb')
    file.write(response.read())
    file.close()
    print(f"File loaded: {filename}")


# js
Path("main/static/js/bootstrap").mkdir(parents=True, exist_ok=True)

download_file(f"https://cdn.jsdelivr.net/npm/bootstrap@{bootstrap_version}/dist/js/bootstrap.bundle.min.js",
              "main/static/js/bootstrap/bootstrap.bundle.min.js")

# css
Path("main/static/css/bootstrap").mkdir(parents=True, exist_ok=True)
download_file(f"https://cdn.jsdelivr.net/npm/bootstrap@{bootstrap_version}/dist/css/bootstrap.min.css",
              "main/static/css/bootstrap/bootstrap.min.css")

download_file(f"https://bootswatch.com/5/darkly/bootstrap.min.css",
              "main/static/css/bootstrap/bootstrap.darkly.min.css")

download_file(f"https://bootswatch.com/5/flatly/bootstrap.min.css",
              "main/static/css/bootstrap/bootstrap.flatly.min.css")

download_file(f"https://bootswatch.com/5/sandstone/bootstrap.min.css",
              "main/static/css/bootstrap/bootstrap.sandstone.min.css")
