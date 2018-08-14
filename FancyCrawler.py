'Crawler fancy.com'
import sys
import logging
import requests
import time
import configparser
from selenium import webdriver
from datetime import datetime
from os.path import split, join, exists
from os import mkdir
from collections import namedtuple

Image = namedtuple('image', 'id url')

class ConfigError(Exception):
    pass

class FancyCrawler:
    'Crawler class'
    def __init__(self):
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        options.add_argument('--log-level=3')
        self.browser = webdriver.Chrome(chrome_options=options)

    def scroll_page_to_element(self, element):
        'Move to element'
        self.browser.execute_script("return arguments[0].scrollIntoView();", element)

    def get_last_link_batch(self):
        'Get URL of last batch'
        element = self.browser.find_element_by_css_selector('a.btn-more')
        return element.get_attribute('href')

    def page_processing(self):
        'Get batch of images URLs'
        while True:
            items = self.browser.find_elements_by_xpath('//*[@id="content"]/ol/li')
            self.scroll_page_to_element(items[-1])
            if len(items) >= 100:
                res = [
                    Image(id=item.get_attribute('tid'), url=item.get_attribute('timage')) 
                    for item in items 
                    if item.get_attribute('timage')]
                link = self.get_last_link_batch()
                return res, link

def read_archive(archive_path):
    'Read archived IDs'
    archive = []
    if not exists(archive_path):
        return archive

    with open (archive_path, 'r') as arch:
        for line in arch:
            archive.append(line.strip())
    logging.info('Read archived images IDs')
    return archive

def append_archive(items, archive_path):
    'Append archived IDs'
    with open (archive_path, 'a') as arch:
        for item in items:
            if item.id:
                arch.write('{id}\n'.format(id=item.id))
    logging.info('Appended images IDs')

def get_raw_image(url):
    'Get image'
    try:
        res = requests.get(url)
    except:
        logging.warning("Couldn't send request %s", url)
        time.sleep(5)
        return 
    else:
        return res.content

def save_images(images, arch_ids, images_path):
    'Saving images'
    for image in images:
        if image.id in arch_ids:
            logging.info('Image %s already archived', image.url)
            continue

        raw_data = get_raw_image('https:' + image.url)
        if not raw_data:
            continue

        if not exists(images_path):
            mkdir(images_path)

        image_path = join(images_path, split(image.url)[1])
        with open(image_path, 'wb') as img:
            img.write(raw_data)
        logging.info('Saved image %s', image_path)
        time.sleep(0.5)
    logging.info('Saved %s images', len(images))

def read_config(env):
    'Reading config-file'
    if not exists('config.ini'):
        raise ConfigError('Create configuration file config.ini')
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config

def get_datestring(url):
    'Get datesting from URL'
    date_string = url.split('cursor=')[1][:12]
    return date_string

def get_date(datestring):
    return datetime.strptime(datestring, '%y%m%d')

def main(env='production'):
    'Main steps'
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] - %(levelname)s - %(message)s',
        datefmt='%d-%m-%Y %I:%M:%S',
        stream=sys.stdout)

    main_config = read_config(env)
    if env not in main_config.sections():
        raise ConfigError('No such section "{0}" in config.ini'.format(env))
    config = main_config[env]

    url = 'https://fancy.com'
    crawler = FancyCrawler()
    try:
        arch_ids = read_archive(config['archive_path'])
        while True:
            crawler.browser.get(url)
            items, url = crawler.page_processing()

            save_images(items, arch_ids, config['images_path'])
            append_archive(items, config['archive_path'])

            batch_date = get_datestring(url)
            logging.info('Last batch %s', datetime.strptime(batch_date, '%y%m%d%H%M%S'))
    except Exception as ex:
        logging.exception(ex)
    finally:
        crawler.browser.quit()
        input('Press any key...')

main()
