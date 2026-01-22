import subprocess
import time

while True:
    subprocess.run(
        ["scrapy", "crawl", "brickeconomy"],
        check=True
    )
    time.sleep(60*60*5)