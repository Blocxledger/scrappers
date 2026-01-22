import base64
import json
import scrapy



class BrickeconomySpider(scrapy.Spider):
    name = "brickeconomy"
    headers = {
        "accept-language": "fr-FR,fr;q=0.9,ar-DZ;q=0.8,ar;q=0.7,en-US;q=0.6,en;q=0.5",
        "cache-control": "no-cache",
        "dnt": "1",
        "pragma": "no-cache",
        "priority": "u=0, i",
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
    custom_settings = {
        'DOWNLOADER_MIDDLEWARES':{
            'core.middlewares.CurlCffiDownloaderMiddleware': 200,
            "scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware": None,
        },
        'DOWNLOAD_DELAY':10
    }  


    def start_requests(self):
        yield scrapy.Request(
            url="https://www.brickeconomy.com/sets#google_vignette",
            headers=self.headers,
            callback=self.parse,
        )


    def parse(self, response):
        for theme in response.css('.themewrap'):
            cat = theme.css('.theme a::text').get()
            sub_themes = theme.css('.subtheme')
            if not sub_themes:
                yield scrapy.Request(
                    url=f"https://www.brickeconomy.com{theme.css('.theme a::attr(href)').get()}",
                    headers=self.headers,
                    callback=self.parse_items,
                    meta={'path':[cat]}
                )
            else:
                for sub_theme in sub_themes.css('a'):
                    sub_cat = sub_theme.css('::text').get()
                    yield scrapy.Request(
                        url=f"https://www.brickeconomy.com{sub_themes.css('::attr(href)').get()}",
                        headers=self.headers,
                        callback=self.parse_items,
                        meta={'path':[cat, sub_cat]}
                    )


    def parse_items(self, response):
        for set in response.css('.ctlsets-table h4 > a::attr(href)'):
            yield scrapy.Request(
                url=f'https://www.brickeconomy.com{set}',
                headers=self.headers,
                callback=self.parse_details,
                meta=response.meta
            )
        if next_page :=  response.xpath("//a[text()='Next']/@href").get() and response.css('input[name="__VIEWSTATE"]::attr(value)').get():
            next_page = next_page.split("$ctlSets$GridViewSets','")[1].split("')")[0]
            headers = {
                "accept": "*/*",
                "accept-language": "fr-FR,fr;q=0.9,ar-DZ;q=0.8,ar;q=0.7,en-US;q=0.6,en;q=0.5",
                "cache-control": "no-cache",
                "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
                "dnt": "1",
                "origin": "https://www.brickeconomy.com",
                "pragma": "no-cache",
                "priority": "u=1, i",
                "sec-ch-ua": '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Linux"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
                "x-microsoftajax": "Delta=true",
                "x-requested-with": "XMLHttpRequest",
            }

            formdata = {
                "ctl00$ScriptManager1": (
                    "ctl00$ContentPlaceHolder1$ctlSets$UpdatePanelMain|"
                    "ctl00$ContentPlaceHolder1$ctlSets$GridViewSets"
                ),
                "__EVENTTARGET": "ctl00$ContentPlaceHolder1$ctlSets$GridViewSets",
                "__EVENTARGUMENT": next_page,
                "ctl00$txtSearchHeader2": "",
                "ctl00$txtSearchHeader": "",
                "subthemesorter": "",
                "setsorter": "YearDESC",
                "__VIEWSTATEGENERATOR": response.css('input[name="__VIEWSTATEGENERATOR"]::attr(value)').get(),
                "__VIEWSTATE": response.css('input[name="__VIEWSTATE"]::attr(value)').get(),
                "__ASYNCPOST": "true",
            }
            response.meta['p']  = True
            yield scrapy.FormRequest(
                url=response.url,
                method="POST",
                headers=headers,
                formdata=formdata,
                callback=self.parse_items,
                dont_filter=True,
                meta=response.meta
            )


    def parse_details(self, response):
        item = {
            'name': response.css('h1.setheader::text').get(),
            'set_id': response.xpath("//div[contains(text(),'Set number')]/../div[2]/text()").get(),
            'year': response.xpath("//div[text()='Year']/../div[2]/a/text()").get(),
            'description': ' '.join(response.css('#setdescription_content::text').getall()),
            'sellers': [],
            'category':response.meta['path'],
            'images': [f"https://www.brickeconomy.com{img}" for img in response.css('#setmediagallery img::attr(src)').getall()],
            'url': response.url,
        }
        item['source'] = 'BrickEconomy'
        for seller in response.css('#sales_region_table tr'):
            item['sellers'] += [{
                'usd_price':seller.css('.a.bold::text').get(),
                'price_change':seller.css('div.text-small::text').get(),
                'condition':'New/Sealed',
                'country':seller.css('::attr(data-region)').get(),
                'buy_url':base64.b64decode(seller.css('::attr(data-outbound)').get()).decode('utf-8') if seller.css('::attr(data-outbound)').get() else None,
            }]

        for seller in response.css('#sales_region_used_table tr'):
            item['sellers'] += [{
                'usd_price':seller.css('.a.bold::text').get(),
                'price_change':seller.css('div.text-small::text').get(),
                'condition':'Used',
                'country':seller.css('::attr(data-region)').get(),
                'buy_url':base64.b64decode(seller.css('::attr(data-outbound)').get()).decode('utf-8') if seller.css('::attr(data-outbound)').get() else None,
            }]
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