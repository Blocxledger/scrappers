import subprocess
import time

while True:
    subprocess.run(
        ["scrapy", "crawl", "bricksandminifigsanaheim"],
        check=True
    )
    time.sleep(60*60*24*3)