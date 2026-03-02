from curl_cffi import requests as curl_requests
from scrapy.http import HtmlResponse
from scrapy import signals
from scrapy.extensions.httpcache import FilesystemCacheStorage

class CurlCffiDownloaderMiddleware:
    """Downloader middleware using curl_cffi + Scrapy cache"""

    def __init__(self, timeout=30, impersonate="chrome120"):
        self.timeout = timeout
        self.impersonate = impersonate
        self.cache_storage = None

    @classmethod
    def from_crawler(cls, crawler):
        mw = cls(
            timeout=crawler.settings.getint("CURL_CFFI_TIMEOUT", 30),
            impersonate=crawler.settings.get("CURL_CFFI_IMPERSONATE", "chrome"),
        )

        # Get Scrapy's cache storage
        if crawler.settings.getbool("HTTPCACHE_ENABLED", False):
            mw.cache_storage = FilesystemCacheStorage(crawler.settings)
        crawler.signals.connect(mw.spider_opened, signal=signals.spider_opened)
        return mw

    def spider_opened(self, spider):
        spider.logger.info("Using curl_cffi downloader middleware with Scrapy cache")

    def process_request(self, request, spider):
        """Fetch request using curl_cffi or return cached response if available"""

        # Skip non-http(s)
        if not request.url.startswith("http"):
            return None

        # --- Check cache first ---
        if self.cache_storage:
            cache_key = self.cache_storage._request_key(request)
            cached_response = self.cache_storage.retrieve_response(request, cache_key)
            if cached_response:
                spider.logger.info(f"Loaded cached response for {request.url}")
                return cached_response

        # --- Prepare headers & cookies ---
        headers = {k.decode(): v[0].decode() for k, v in request.headers.items()}
        cookies = request.cookies or {}

        try:
            resp = curl_requests.request(
                method=request.method,
                url=request.url,
                headers=headers,
                cookies=cookies,
                data=request.body if request.body else None,
                timeout=self.timeout,
                impersonate=self.impersonate,
                allow_redirects=True,
            )
        except Exception as e:
            spider.logger.error(f"curl_cffi error: {e}")
            return None

        # --- Convert to HtmlResponse ---
        scrapy_resp = HtmlResponse(
            url=resp.url,
            status=resp.status_code,
            headers=resp.headers,
            body=resp.content,
            encoding="utf-8",
            request=request,
        )

        # --- Save response to cache ---
        if self.cache_storage:
            cache_key = self.cache_storage._request_key(request)
            self.cache_storage.store_response(request, scrapy_resp, cache_key)

        return scrapy_resp                                                                                
