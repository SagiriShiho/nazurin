# -*- coding: utf-8 -*-
import json
import time
import os
from config import NAZURIN_DATA, DOWNLOAD_DIR
from sites.Pixiv.config import DOCUMENT, USER, PASSWORD
from utils import NazurinError, logger, sanitizeFilename
from database import Database
from pixivpy3 import AppPixivAPI, PixivError

class Pixiv(object):
    api = AppPixivAPI()
    db = Database().driver()
    collection = db.collection(NAZURIN_DATA)
    document = collection.document(DOCUMENT)
    updated_time = 0

    def login(self, refresh=False):
        if not refresh:
            tokens = Pixiv.document.get()
            if tokens:
                Pixiv.api.refresh_token = tokens['refresh_token']
                Pixiv.updated_time = tokens['updated_time']
            else: # Initialize database
                self._login()
                return
        if refresh or time.time() - Pixiv.updated_time >= 3600: # Access token expired
            self._refreshToken()
            Pixiv.document.update({
                'access_token': Pixiv.api.access_token,
                'updated_time': Pixiv.updated_time
            })
            logger.info('Pixiv tokens cached')
        else:
            Pixiv.api.access_token = tokens['access_token']
            logger.info('Pixiv logged in through cached tokens')

    def getArtwork(self, artwork_id):
        """Fetch an artwork."""
        response = self.call(Pixiv.api.illust_detail, artwork_id)
        if 'illust' in response.keys():
            illust = response.illust
        else:
            error = response.error
            msg = error.user_message or error.message
            raise NazurinError(msg)
        if illust.restrict != 0:
            raise NazurinError("Artwork is private")
        return illust

    def view_illust(self, artwork_id):
        illust = self.getArtwork(artwork_id)
        if illust.type == 'ugoira':
            raise NazurinError('Ugoira view is not supported.')
        details = self.buildCaption(illust)
        imgs = self.getImages(illust)
        return imgs, details

    def download_illust(self, artwork_id=None, illust=None):
        """Download and return images of an illustration."""
        if not illust:
            imgs, _ = self.view_illust(artwork_id)
        else:
            imgs = self.getImages(illust)
        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)
        for img in imgs:
            filename = DOWNLOAD_DIR + img['name']
            if (not os.path.exists(filename)) or os.stat(filename).st_size == 0:
                Pixiv.api.download(img['url'], path=DOWNLOAD_DIR, name=img['name'])
        return imgs

    def download_ugoira(self, illust):
        """Download ugoira zip file and store animation data."""
        metadata = json.dumps(Pixiv.api.ugoira_metadata(illust.id).ugoira_metadata)
        url = illust.meta_single_page.original_image_url
        zip_url = url.replace('/img-original/', '/img-zip-ugoira/')
        zip_url = zip_url.split('_ugoira0')[0] + '_ugoira1920x1080.zip'
        filename = str(illust.id) + '_ugoira1920x1080.zip'
        metafile = str(illust.id) + '_ugoira.json'
        imgs = [{'url': zip_url, 'name': filename}, {'name': metafile}]
        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)
        with open(DOWNLOAD_DIR + metafile, 'w') as f:
            f.write(metadata)
        Pixiv.api.download(zip_url, path=DOWNLOAD_DIR, name=filename)
        return imgs

    def bookmark(self, artwork_id):
        response = self.call(Pixiv.api.illust_bookmark_add, artwork_id)
        if 'error' in response.keys():
            logger.error(response)
            raise NazurinError(response['error']['user_message'])
        else:
            logger.info('Bookmarked artwork ' + str(artwork_id))
            return True

    def _login(self):
        Pixiv.api.login(USER, PASSWORD)
        Pixiv.updated_time = time.time()
        Pixiv.collection.insert(DOCUMENT, {
            'access_token': Pixiv.api.access_token,
            'refresh_token': Pixiv.api.refresh_token,
            'updated_time': Pixiv.updated_time
        })
        logger.info('Pixiv logged in with password')

    def _refreshToken(self):
        try:
            Pixiv.api.auth()
            Pixiv.updated_time = time.time()
            logger.info('Pixiv access token updated')
        except PixivError: # Refresh token may be expired, try to login with password
            Pixiv.document.delete()
            self._login()

    def call(self, func, *args):
        """Call API with login state check."""
        if not Pixiv.api.access_token or not Pixiv.api.refresh_token:
            self.login()
        response = func(*args)
        if 'error' in response.keys() and 'invalid_grant' in response.error.message: # Access token expired
            self.login(refresh=True)
            response = func(*args)
        return response

    def getImages(self, illust):
        """Get images from an artwork."""
        imgs = list()
        if illust.meta_pages: # Contains more than one image
            pages = illust.meta_pages
            for page in pages:
                url = page.image_urls.original
                name = self.getFilename(url, illust)
                imgs.append({'url': url, 'name': name})
        else:
            url = illust.meta_single_page.original_image_url
            name = self.getFilename(url, illust)
            imgs.append({'url': url, 'name': name})
        return imgs

    def buildCaption(self, illust):
        """Build media caption from an artwork."""
        tags = str()
        for tag in illust.tags:
            tags += '#' + tag.name + ' '
            tags = tags.replace('#クレー', '#可莉')
            tags = tags.replace('#Klee', '#可莉')
            tags = tags.replace('#klee', '#可莉')
            tags = tags.replace('#Mona', '#莫娜')
            tags = tags.replace('#mona', '#莫娜')
            tags = tags.replace('#アストローギスト・モナ・メギストス', '#莫娜')
            tags = tags.replace('#アストローギスト・モナ・メギス', '#莫娜')
            tags = tags.replace('#モナ', '#莫娜')
            tags = tags.replace('#Diona', '#迪奥娜')
            tags = tags.replace('#diona', '#迪奥娜')
            tags = tags.replace('#ディオナ', '#迪奥娜')
            tags = tags.replace('#Keqing', '#刻晴')
            tags = tags.replace('#keqing', '#刻晴')
            tags = tags.replace('#qiqi', '#七七')
            tags = tags.replace('#パイモン', '#派蒙')
            tags = tags.replace('#Paimon', '#派蒙')
            tags = tags.replace('#paimon', '#派蒙')
            tags = tags.replace('#フィッシュル・ヴォン・ルフシュロス・ナフィードット', '#皇女')
            tags = tags.replace('#フィッシュル', '#皇女')
            tags = tags.replace('#Fischl', '#皇女')
            tags = tags.replace('#fischl', '#皇女')
            tags = tags.replace('#菲谢尔', '#皇女')
            tags = tags.replace('#谢菲尔', '#皇女')
            tags = tags.replace('#Barbara', '#芭芭拉')
            tags = tags.replace('#barbara', '#芭芭拉')
            tags = tags.replace('#babara', '#芭芭拉')
            tags = tags.replace('#バーバラ', '#芭芭拉')
            tags = tags.replace('#Noelle', '#诺艾尔')
            tags = tags.replace('#noelle', '#诺艾尔')
            tags = tags.replace('#ノエル', '#诺艾尔')
            tags = tags.replace('#アンバー', '#安柏')
            tags = tags.replace('#Amber', '#安柏')
            tags = tags.replace('#amber', '#安柏')
            tags = tags.replace('#Ganyu', '#甘雨')
            tags = tags.replace('#ganyu', '#甘雨')
            tags = tags.replace('#감우', '#甘雨')
            tags = tags.replace('#リサ', '#丽莎')
            tags = tags.replace('#ガイア', '#凯亚')
            tags = tags.replace('#ディルック', '#迪卢克')
            tags = tags.replace('#レザー', '#雷泽')
            tags = tags.replace('#雷蛍術師', '#雷萤术士')
            tags = tags.replace('#神里綾華', '#神里绫华')
            tags = tags.replace('#ウェンティ', '#温迪')
            tags = tags.replace('#スクロース', '#砂糖')
            tags = tags.replace('#ジン・グンヒルド', '#琴')
            tags = tags.replace('#ジン', '#琴')
            tags = tags.replace('#蛍', '#荧')
            tags = tags.replace('#辛焱', '#辛炎')
            tags = tags.replace('#Hutao', '#胡桃')
            tags = tags.replace('#hutao', '#胡桃')
            tags = tags.replace('#hu_tao', '#胡桃')
            tags = tags.replace('#HuTao ', '#胡桃')
            tags = tags.replace('#ロサリア', '#罗莎莉亚')
            tags = tags.replace('#Rosaria', '#罗莎莉亚')
            tags = tags.replace('#rosaria', '#罗莎莉亚')
            tags = tags.replace('#loli', '#萝莉')
            tags = tags.replace('#ロリ', '#萝莉')
            tags = tags.replace('#R-18G', '#R18G #NSFW')
            tags = tags.replace('#R-18', '#R18 #NSFW')
            tags = tags.replace('#Genshin_Impact ', '')
            tags = tags.replace('#GenshinImpact ', '')
            tags = tags.replace('#Genshin ', '')
            tags = tags.replace('#genshinimpact ', '')
            tags = tags.replace('#genshin ', '')
            tags = tags.replace('#原神Project ', '')
            tags = tags.replace('#原神project ', '')
            tags = tags.replace('#원신 ', '')
            tags = tags.replace('#女の子 ', '')
            tags = tags.replace('#少女 ', '')
            tags = tags.replace('#女孩子 ', '')
            tags = tags.replace('#Genshin_Impact', '')
            tags = tags.replace('#GenshinImpact', '')
            tags = tags.replace('#Genshin', '')
            tags = tags.replace('#genshinimpact', '')
            tags = tags.replace('#genshin', '')
            tags = tags.replace('#原神Project', '')
            tags = tags.replace('#原神project', '')
            tags = tags.replace('#원신', '')
            tags = tags.replace('#女の子', '')
            tags = tags.replace('#少女', '')
            tags = tags.replace('#女孩子', '')
            tags = tags.replace('(原神)', '')
            tags = tags.replace('(GenshinImpact)', '')
            tags = tags.replace('(genshinimpact)', '')
            tags = tags.replace('#可莉 #可莉', '#可莉')
            tags = tags.replace('#莫娜 #莫娜', '#莫娜')
            tags = tags.replace('#迪奥娜 #迪奥娜', '#迪奥娜')
            tags = tags.replace('#刻晴 #刻晴', '#刻晴')
            tags = tags.replace('#七七 #七七', '#七七')
            tags = tags.replace('#派蒙 #派蒙', '#派蒙')
            tags = tags.replace('#皇女 #皇女', '#皇女')
            tags = tags.replace('#芭芭拉 #芭芭拉', '#芭芭拉')
            tags = tags.replace('#诺艾尔 #诺艾尔', '#诺艾尔')
            tags = tags.replace('#安柏 #安柏', '#安柏')
            tags = tags.replace('#甘雨 #甘雨', '#甘雨')
            tags = tags.replace('#丽莎 #丽莎', '#丽莎')
            tags = tags.replace('#凯亚 #凯亚', '#凯亚')
            tags = tags.replace('#雷泽 #雷泽', '#雷泽')
            tags = tags.replace('#雷萤术士 #雷萤术士', '#雷萤术士')
            tags = tags.replace('#温迪 #温迪', '#温迪')
            tags = tags.replace('#砂糖 #砂糖', '#砂糖')
            tags = tags.replace('#琴 #琴', '#琴')
            tags = tags.replace('#荧 #荧', '#荧')
            tags = tags.replace('#胡桃 #胡桃', '#胡桃')
        details = {
            'title': illust.title,
            'author': illust.user.name,
            'tags': tags,
            #'total_bookmarks': illust.total_bookmarks,
            'url': 'pixiv.net/i/' + str(illust.id)
        }
        #details['bookmarked'] = illust.is_bookmarked
        return details

    def getFilename(self, url, illust):
        basename = os.path.basename(url)
        filename, extension = os.path.splitext(basename)
        name = "%s - %s - %s(%d)%s" % (filename, illust.title, illust.user.name, illust.user.id, extension)
        return sanitizeFilename(name)
