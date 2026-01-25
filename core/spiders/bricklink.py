import json
import scrapy
from w3lib.html import remove_tags
import csv

def csv_to_dicts(csv_path, encoding="utf-8"):
    """
    Convert a CSV file to a list of dictionaries (no pandas).
    """
    with open(csv_path, newline="", encoding=encoding) as f:
        reader = csv.DictReader(f)
        return list(reader)

class BricklinkSpider(scrapy.Spider):
    name = "bricklink"
    custom_settings = {
        'DOWNLOAD_DELAY':20
    }
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "fr-FR,fr;q=0.9,ar-DZ;q=0.8,ar;q=0.7,en-US;q=0.6,en;q=0.5",
        "cache-control": "no-cache",
        "dnt": "1",
        "pragma": "no-cache",
        "priority": "u=0, i",
        "referer": "https://www.bricklink.com/",
        "sec-ch-ua": "\"Google Chrome\";v=\"129\", \"Not=A?Brand\";v=\"8\", \"Chromium\";v=\"129\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Linux\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "cross-site",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    }
    codes = {
        'N':"New",
        'U':'Used'
    }
    complete = {
        'S':'Sealed',
        'C':'Complete',
        'I':'Incomplete',
        'U': 'Used',
        'N': 'New'
    }


    def start_requests(self):
        yield scrapy.Request(
            url="https://www.bricklink.com/catalogTree.asp?itemType=S",
            headers=self.headers,
            callback=self.parse_categories,
        )

    def parse_categories(self, response):
        slugs = response.xpath(".//table[@id='id-main-legacy-table']//tr[contains(@class, 'catalog-tree__spacing-reset')][1]//a/@href").getall()
        for slug in slugs:
            cat_id = slug.split('=')[-1]
            is_not_last_cat = response.xpath(f"//tr[contains(@class, 'catalog-tree__spacing-reset')][1]//a[contains(@href,'/catalogList.asp?catType=S&catString={cat_id}.')]").get()
            if is_not_last_cat:
                continue
            base_xpath = "//tr[contains(@class, 'catalog-tree__spacing-reset')][1]//a[@href='/catalogList.asp?catType=S&catString={}']"
            all_ids = []
            for cat  in cat_id.split('.'):
                if not all_ids:
                    all_ids += [cat]
                else:
                    all_ids += [f"{all_ids[len(all_ids)-2]}.{cat}"]
            path = [response.xpath(f"{base_xpath.format(cat)}//text()").get() for cat in all_ids]
            yield scrapy.Request(
                url=f"https://www.bricklink.com{slug}",
                headers=self.headers,
                callback=self.parse_products,
                meta={'path':path}
            )

    def parse_products(self, response):
        slugs = response.xpath("//table[contains(@class,  'catalog-list__body-main--alternate-row')]//tr//a[contains(@href,'/v2/catalog/catalogitem.page')]/@href").getall()
        for slug in slugs:
            yield scrapy.Request(
                url=f"https://www.bricklink.com{slug}",
                headers=self.headers,
                callback=self.parse,
                meta=response.meta
            )

        if next_page := response.xpath("//a[contains(., 'Next')]/@href").get(): 
            yield scrapy.Request(
                url=f"https://www.bricklink.com{next_page}",
                headers=self.headers,
                callback=self.parse_products,
                meta=response.meta
            )

    def parse(self, response):
        item = {
                'name': response.css('#item-name-title::text').get(),
                'set_id': response.xpath("//span[contains(.,'Item No:')]/span/text()").get(),
                'year': response.css('td[width="38%"] font[style="font-size:12px; line-height:18px;"] > a::text').get(),
                'weight': response.css('#item-weight-info::text').get(),
                'dim': response.css('#dimSec::text').get(),
                'parts': response.css('td[width="31%"] font[style="font-size:12px; line-height:18px;"] > a::text').get(),
                'sellers': [],
                'category':response.meta['path'],
                'image': f"https:{response.css('.pciMainImageHolder img::attr(src)').get()}",
                'url': response.url,
            }
        item_id = response.css('#_idAddToWantedLink::attr(data-itemid)').get()
        url = (
            "https://www.bricklink.com/ajax/clone/catalogifs.ajax"
            f"?itemid={item_id}&pi=1&iconly=0&rpp=500"
        )

        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-language": "fr-FR,fr;q=0.9,ar-DZ;q=0.8,ar;q=0.7,en-US;q=0.6,en;q=0.5",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "dnt": "1",
            "priority": "u=1, i",
            "referer": "https://www.bricklink.com/v2/catalog/catalogitem.page?S=3061-1",
            "sec-ch-ua": '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/129.0.0.0 Safari/537.36"
            ),
            "x-requested-with": "XMLHttpRequest",
        }
        yield scrapy.Request(
            url=url,
            headers=headers,
            callback=self.parse_sellers,
            meta={'item':item, 'item_id': item_id}
        )


    def parse_sellers(self, response):
        item = response.meta['item']
        item['source'] = 'BrickLink'
        data = response.json()
        sellers = data.get('list',[])
        for seller in sellers:
            item['sellers'] += [{
                'seller_name': seller['strStorename'],
                'seller_description': seller['strDesc'],
                'condition': seller['codeNew'].upper(),
                'country':seller['strSellerCountryName'],
                'complete': seller['codeComplete'].upper(),
                'usd_price':float(seller['mDisplaySalePrice'].split(' ')[-1]),
                'real_price':float(seller['mInvSalePrice'].split(' ')[-1]),
                'quantity': seller['n4Qty'],
                'buy_url':f'https://store.bricklink.com/ModernoBricks?itemID={seller["idInv"]}'
            }]
        if not sellers:
            return
        if (int(data['rpp'])*int(data['pi']))< int(data['total_count']):
            url = (
                "https://www.bricklink.com/ajax/clone/catalogifs.ajax"
                f"?itemid={response.meta['item_id']}&pi={int(data['pi']) + 1}&iconly=0&rpp=500"
            )
            response.meta['item'] = item
            yield scrapy.Request(
                url=url,
                headers=self.headers,
                callback=self.parse_sellers,
                meta=response.meta
            )
        else:
            yield item
            yield scrapy.Request(
                url="https://lego1.up.railway.app/api/ingest-set/",
                method="POST",
                body=json.dumps(item),
                callback=self.check,
                headers={"Content-Type": "application/json"},
            )

    def check(self, response):
        pass