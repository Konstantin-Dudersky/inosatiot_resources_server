"""
Загрузка статических библиотек из интернета
"""

import shutil
import tarfile
import urllib.request
from pathlib import Path

# set version
bootstrap_version = '5.0.2'
bootswatch_version = '5.0.2'


def download_file(download_url, filename):
    response = urllib.request.urlopen(urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'}))
    file = open(filename, 'wb')
    file.write(response.read())
    file.close()
    print(f"File loaded: {filename}")


# ----------------------------------------------------------------------------------------------------------------------
# bootstrap
Path("main/static/js/bootstrap").mkdir(parents=True, exist_ok=True)

download_file(f"https://cdn.jsdelivr.net/npm/bootstrap@{bootstrap_version}/dist/js/bootstrap.bundle.min.js",
              "main/static/js/bootstrap/bootstrap.bundle.min.js")

Path("main/static/css/bootstrap").mkdir(parents=True, exist_ok=True)
download_file(f"https://cdn.jsdelivr.net/npm/bootstrap@{bootstrap_version}/dist/css/bootstrap.min.css",
              "main/static/css/bootstrap/bootstrap.min.css")

# ----------------------------------------------------------------------------------------------------------------------

# bootswatch

# load archive
Path("tmp").mkdir(parents=True, exist_ok=True)
download_file(f"https://github.com/thomaspark/bootswatch/archive/refs/tags/v{bootswatch_version}.tar.gz",
              "tmp/bootswatch.tar.gz")

# unpack
tar = tarfile.open("tmp/bootswatch.tar.gz", "r")
tar.extractall(path="tmp/")
tar.close()

# copy files
for theme in ['darkly', 'flatly', 'sandstone']:
    shutil.copy2(f"tmp/bootswatch-{bootswatch_version}/dist/{theme}/bootstrap.min.css",
                 f"main/static/css/bootstrap/bootstrap.{theme}.min.css")

# delete folder
shutil.rmtree("tmp/")
