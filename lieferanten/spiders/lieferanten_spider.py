import scrapy
import configparser

config = configparser.ConfigParser()
config.read('lieferanten/config.cfg')

USER_NAME = config['login']['Username']
PASSWORD = config['login']['Password']
# here you can add more pages with keywords to be crawled, for now just 'Software'
PAGES = ["https://www.lieferanten.de/produkt-Software.html?seite=1&sort=&land=&ort=&geo=&umkreis=&typ2=&empf="]

class LieferantenSpider(scrapy.Spider):
        name = "lieferanten"
        start_urls = ["https://www.lieferanten.de/ek1-login.php"]

        def parse(self, response):
            yield scrapy.FormRequest.from_response(
                    response, 
                    formdata={
                        'LogEmail': USER_NAME,
                        'LogPassword': PASSWORD
                    },
                    callback=self.after_login)

        def after_login(self, response):
            for page in PAGES:
                yield scrapy.Request(
                        url=page,
                        callback=self.parse_main_page)
        
        def parse_main_page(self, response):
            for supplier in response.css('div.lieferantenBoxItem'):
                data = {
                    'name': supplier.css('a::text').extract_first(),
                    'profile_link': "https://www.lieferanten.de/" + supplier.css('a::attr(href)').extract_first(),
                    'supplier_type': supplier.css('span::text').extract_first(),
                    'employees': supplier.css('ul.bullets li::text').re_first('.*Mitarbeiter'),
                    'foundation': supplier.css('ul.bullets li::text').re_first('.*gegründet')
                }
                # passing additional data to callback functions in scrapy
                # (extending information of current item from another url)
                # https://doc.scrapy.org/en/latest/topics/request-response.html#topics-request-response-ref-request-callback-arguments
                request = scrapy.Request(
                        url=data['profile_link'], 
                        callback=self.parse_profile)
                request.meta['data'] = data
                yield request
            next_page = None
            next_page_ref = response.css('div.pageNaviPages ul li')[-1].css('a::attr(href)').extract_first()
            if next_page_ref is not None:
                next_page = "https://www.lieferanten.de/" + next_page_ref
            if next_page is not None:
                yield response.follow(
                        url=next_page, 
                        callback=self.parse_main_page)

        def parse_profile(self, response):
            data = response.meta['data']
            data['address_strasse'] = response.css('div[id=lieferantenDetailData] ul li').re_first('.*Straße.*</em>(.*)</li>')
            data['plz_city'] = response.css('div[id=lieferantenDetailData] ul li').re_first('.*PLZ.*</em>(.*)</li>')
            data['country'] = response.css('div[id=lieferantenDetailData] ul li').re_first('.*Land.*</em>(.*)</li>')
            data['telephone'] = response.css('div[id=lieferantenDetailData] ul li').re_first('.*Telefon.*</em>(.*)</li>')
            data['mobile'] = response.css('div[id=lieferantenDetailData] ul li').re_first('.*Mobil.*</em>(.*)</li>')
            data['unternehmensart'] = response.css('div[id=lieferantenDetailData] ul li').re_first('.*Unternehmensart.*</em>(.*)</li>') 
            data['website'] = response.css('div[id=lieferantenDetailData] ul li a::text').extract_first()
            data['languages'] = response.css('div[id=lieferantenDetailData] ul li').re_first('.*Sprachen.*</em>(.*)</li>') 
            data['categories'] = response.css('div.lieferantenDetailProducts strong::text').extract()
            yield data
