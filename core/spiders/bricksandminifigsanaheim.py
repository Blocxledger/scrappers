import json
import scrapy
import re
from w3lib.html import remove_tags


class BricksandminifigsanaheimSpider(scrapy.Spider):
    name = "bricksandminifigsanaheim"
    custom_settings = {
        'DOWNLOAD_DELAY':60
    }
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "fr-FR,fr;q=0.9,ar-DZ;q=0.8,ar;q=0.7,en-US;q=0.6,en;q=0.5",
        "cache-control": "no-cache",
        "dnt": "1",
        "pragma": "no-cache",
        "priority": "u=0, i",
        "referer": "https://www.bricksandminifigsanaheim.com/",
        "sec-ch-ua": "\"Google Chrome\";v=\"141\", \"Not=A?Brand\";v=\"8\", \"Chromium\";v=\"141\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Linux\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "cross-site",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
    }

    def start_requests(self):
        yield scrapy.Request(
            url="https://www.bricksandminifigsanaheim.com/collections/current-new-sets",
            headers=self.headers,
            callback=self.parse
        )

    def parse(self, response):
        for product in response.css('.product-card__title a::attr(href)').getall():
            yield scrapy.Request(
                url=f"https://www.bricksandminifigsanaheim.com{product}",
                headers=self.headers,
                callback=self.parse_pdp
                )
            
        if next_page := response.css('a[rel="next"]::attr(href)').get():
            yield scrapy.Request(
                url=f"https://www.bricksandminifigsanaheim.com{next_page}",
                headers=self.headers,
                callback=self.parse
            )
    
    def parse_pdp(self, response):
        name = response.css('h1.product-info__title::text').get()
        match = re.search(r"\b\d{5,6}\b", name)
        code = ''
        if match:
            code = match.group()

        item = {
            'name':name,
            'price':''.join(response.css('sale-price.text-lg::text').getall()).replace('\n', '').strip(),
            'set_id':code,
            'url':response.url,
            'images':[
                img if img.startswith("https:")
                else f"https:{img}"
                for img in response.css("media-carousel img::attr(src)").getall()
            ],
            'source':'bricksandminifigsanaheim',
            'category':response.css('.product-info__text p::text').get(),
            'description':remove_tags(response.css('.product-info__description').get('')).strip(),
        }
        yield item
        yield scrapy.Request(
            url="https://yourdomain.com/api/ingest-set/",
            method="POST",
            body=json.dumps(item),
            callback=self.check,
            headers={"Content-Type": "application/json"},
        )

    def check(self, response):
        pass