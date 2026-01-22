import subprocess
import time

while True:
    subprocess.run(
        ["scrapy", "crawl", "bricklink"],
        check=True
    )
    time.sleep(60*60*12)