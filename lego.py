import subprocess
import time
while True:
    subprocess.run(
        ["scrapy", "crawl", "lego"],
        check=True
    )
    time.sleep(60*60*24)