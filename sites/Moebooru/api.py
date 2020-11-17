from urllib.parse import unquote
import requests
from requests.exceptions import HTTPError
import json
import os
from config import DOWNLOAD_DIR
from utils import NazurinError, downloadImages, logger, sanitizeFilename
from pybooru import Moebooru as moebooru
from bs4 import BeautifulSoup

class Moebooru(object):
    def site(self, site_url='yande.re'):
        self.url = site_url
        return self

    def getPost(self, post_id):
        url = 'https://'+ self.url + '/post/show/' + str(post_id)
        response = requests.get(url)
        try:
            response.raise_for_status()
        except HTTPError as err:
            raise NazurinError(err)

        response = response.text
        soup = BeautifulSoup(response, 'html.parser')
        tag = soup.find(id="post-view").find(recursive=False)
        if tag.name == 'script':
            content = str.strip(tag.string)
        elif tag.name == 'div' and ('status-notice' in tag['class']):
            raise NazurinError(tag.get_text(strip=True))
        else:
            logger.error(tag)
            raise NazurinError('Unknown error')

        info = content[19:-2]
        try:
            info = json.loads(info)
            post = info['posts'][0]
            tags = info['tags']
        except json.decoder.JSONDecodeError as err:
            logger.error(err)
        return post, tags

    def view(self, post_id):
        post, tags = self.getPost(post_id)
        imgs = self.getImages(post)
        caption = self.buildCaption(post, tags)
        return imgs, caption

    def download(self, post_id=None, post=None):
        if post:
            imgs = self.getImages(post)
        else:
            imgs, _ = self.view(post_id)
        downloadImages(imgs)
        return imgs

    def pool(self, pool_id, jpeg=False):
        client = moebooru(self.site)
        info = client.pool_posts(id=pool_id)
        posts = info['posts']
        imgs = list()
        for post in posts:
            if not jpeg:
                url = post['file_url']
            else:
                url = post['jpeg_url']
            name, _ = self.parseUrl(url)
            imgs.append({'name': name, 'url': url})
        details = {'name': info['name'], 'description': info['description']}
        return imgs, details

    def download_pool(self, pool_id, jpeg=False):
        imgs, details = self.pool(pool_id, jpeg)
        pool_name = details['name']
        if not os.path.exists(DOWNLOAD_DIR + pool_name):
            os.makedirs(DOWNLOAD_DIR + pool_name)
        for key, img in enumerate(imgs):
            filename = str(key + 1)
            filename = '0' * (3 - len(filename)) + filename
            _, ext = self.parseUrl(img['url'])
            filename += ext
            downloadImages([{'url': img['url'], 'name': pool_name + '/' + filename}]) #TODO

    def getImages(self, post):
        file_url = post['file_url']
        name = sanitizeFilename(unquote(os.path.basename(file_url)))
        imgs = [{'url': file_url, 'name': name}]
        return imgs

    def buildCaption(self, post, tags):
        """Build media caption from an post."""
        title = post['tags']
        source = post['source']
        tag_string = artists = str()
        for tag, tag_type in tags.items():
            if tag_type == 'artist':
                artists += tag + ' '
            else:
                tag_string += '#' + tag + ' '
            tag_string = tag_string.replace('(genshin_impact)', '')
            tag_string = tag_string.replace('#klee_', '#可莉')
            tag_string = tag_string.replace('#mona_', '#莫娜')
            tag_string = tag_string.replace('#diona_', '#迪奥娜')
            tag_string = tag_string.replace('#keqing_', '#刻晴')
            tag_string = tag_string.replace('#qiqi_', '#七七')
            tag_string = tag_string.replace('#paimon_', '#派蒙')
            tag_string = tag_string.replace('#fischl_', '#皇女')
            tag_string = tag_string.replace('#barbara_', '#芭芭拉')
            tag_string = tag_string.replace('#noelle_', '#诺艾尔')
            tag_string = tag_string.replace('#amber_', '#安柏')
            tag_string = tag_string.replace('#lisa_', '#丽莎')
            tag_string = tag_string.replace('#venti_', '#温迪')
            tag_string = tag_string.replace('#sucrose_', '#砂糖')
            tag_string = tag_string.replace('#jean_', '#琴')
            tag_string = tag_string.replace('#ningguang_', '#凝光')
            tag_string = tag_string.replace('#lumine_', '#荧')
            tag_string = tag_string.replace('#loli_', '#萝莉')
            tag_string = tag_string.replace('#uncensored_', '#无修正 #R18 #NSFW')
            tag_string = tag_string.replace('#censored_', '#马赛克 #R18 #NSFW')
            tag_string = tag_string.replace('#topless_', '#裸体 #R18 #NSFW')
            tag_string = tag_string.replace('#klee', '#可莉')
            tag_string = tag_string.replace('#mona', '#莫娜')
            tag_string = tag_string.replace('#diona', '#迪奥娜')
            tag_string = tag_string.replace('#keqing', '#刻晴')
            tag_string = tag_string.replace('#qiqi', '#七七')
            tag_string = tag_string.replace('#paimon', '#派蒙')
            tag_string = tag_string.replace('#fischl', '#皇女')
            tag_string = tag_string.replace('#barbara', '#芭芭拉')
            tag_string = tag_string.replace('#noelle', '#诺艾尔')
            tag_string = tag_string.replace('#amber', '#安柏')
            tag_string = tag_string.replace('#lisa', '#丽莎')
            tag_string = tag_string.replace('#venti', '#温迪')
            tag_string = tag_string.replace('#sucrose', '#砂糖')
            tag_string = tag_string.replace('#jean', '#琴')
            tag_string = tag_string.replace('#ningguang', '#凝光')
            tag_string = tag_string.replace('#lumine', '#荧')
            tag_string = tag_string.replace('#loli', '#萝莉')
            tag_string = tag_string.replace('#uncensored', '#无修正 #R18 #NSFW')
            tag_string = tag_string.replace('#censored', '#马赛克 #R18 #NSFW')
            tag_string = tag_string.replace('#topless', '#裸体 #R18 #NSFW')
        details = dict()
        #if title:
        #    details['title'] = title
        if artists:
            details['artists'] = artists
        details['url'] = 'https://'+ self.url + '/post/show/' + str(post['id'])
        if tag_string:
            details['tags'] = tag_string
        if source:
            details['source'] = source
        if post['parent_id']:
            details['parent_id'] = post['parent_id']
        if post['has_children']:
            details['has_children'] = True
        return details

    def parseUrl(self, url):
        name = os.path.basename(url)
        return os.path.splitext(name)
