# coding: utf-8

import bs4 as bs
import urllib.request
import re
import functools
import csv
import requests
from collections import defaultdict
import json
import argparse
from requests import ConnectionError
import time
from tqdm import *


def output_json_file(data, filename):
    with open(filename, 'w') as outfile:
        json.dump(data, outfile)

    return print("Writing %s" % (str(filename)))

def read_json_file(filename):
    with open(filename) as data_file:
        data = json.load(data_file)
    return data


class shop_parser:
    def __init__(self, shop):

        source = urllib.request.urlopen("http://www.dfshop.com/TeamShop/")
        soup = bs.BeautifulSoup(source, 'lxml', parse_only=bs.SoupStrainer('td'))
        g = [i[0]+1 for i in enumerate(soup) if re.match(".+"+str(shop)+".+", str(i[1]))]
        link = [i[1] for i in enumerate(soup) if i[0] == g[0]]
        html = [i['href'] for i in link[0].find_all("a")]

        s = requests.Session()
        r = s.get(html[0])

        soup = bs.BeautifulSoup(r.text, "lxml")
        html = ["http://www.dfshop.com"+i['href'] for i in soup.find_all("a")]

        self.session = html[0]
        print(self.session)

        s = requests.Session()
        r = s.get(self.session)

        self.all_article_id = {} #all article id's
        self.categorys = []
        #self.article_hrefs = []
        self.data = {}

    def init_session(self):
        s = requests.Session()
        r = s.get(self.session)

    def get_category(self):
        # get category links
        s = requests.Session()
        r = s.get(self.session)
        links = set()
        soup = bs.BeautifulSoup(r.text, 'lxml', parse_only=bs.SoupStrainer('a'))
        for i in soup.find_all("a", href = re.compile(r'.+cat=\d.+')):
            links.add("http://www.dfshop.com/"+i['href'])
        links = list(links)
        links.sort()
        self.categorys = links

    def next_page_by_cat(self):
        # jump to next page
        s = requests.Session()
        self.session = re.sub("&f=cat&cat=\d.+", "&f=listpage&nav=next", self.session)
        r = s.get(self.session)
        soup = bs.BeautifulSoup(r.text, "lxml", parse_only=bs.SoupStrainer("div", { "id" : "mainArea" }))
        return soup

    def loop_article_href(self):
        # get all article id's (loop function)
        self.init_session()
        links = set()
        from_, to_ = int(0), int(1)
        while to_ > from_:
            try:
                soup = self.next_page_by_cat()
                for i in soup.find_all('a', href = re.compile(r'.+art=\w{2}\d+')):
                    links.add(re.findall(r'art=\w{2}\d+',i['href'])[0][4:])

                indexes = [re.findall(r'\d+', i.text) for i in soup.find_all('div',{"id": "artListFooter"})][0]
                from_, to_ = int(indexes[1]), int(indexes[2])
                percent = round(float(indexes[1]) / float(indexes[2])*100, 1)
                print("Parsed %s Pages of %s (%s %%)" % (str(from_), str(to_), str(percent)), end="\r")
            except ConnectionError as e:
                print(e)
                time.sleep(1)
                continue
                #break
        links = list(links)
        links.sort()
        return links


    def get_all_article_links(self):
        # get all article ids
        for c in self.categorys:
            self.session = c
            cat_string = str(re.findall(r'(cat=\d+\.\d+\.\d+\.\d+)', c)[0])
            print("Parsing: %s" % (re.sub("=", " = ", cat_string)), flush=True)
            self.all_article_id[cat_string] = self.loop_article_href()

    def parse_article(self):
        for article in self.all_article_id.values():
            for i in tqmd(article):
                try:
                    s = requests.Session()
                    r = s.get(self.session + "&f=art&art=" + str(i))

                    soup = bs.BeautifulSoup(r.text, 'lxml', parse_only=bs.SoupStrainer('div', {"id": "artDetailMain"}))
                    text = [re.sub("\n", "", i.text) for i in soup.find_all("div", {'id': 'artDetailDescRow'})]
                    idsupplier = [re.sub("\n", "", i.text) for i in soup.find_all("div", {'id': 'artDetailLiefArnumRow'})]
                    price = [re.findall("\d+\.\d+", i.text)[0] for i in soup.find_all("div", {'id': 'artDetailLiefPriceRow'})]

                    self.data[str(i)] = [text, idsupplier, price]
                except (ConnectionError, Exception) as e:
                    print(e)
                    continue


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Parse Sanitary Shop",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--shop', type=str,
                    dest='shop', default="", help='Which Shop to Parse')

    parser.add_argument('--output', type=str,
                        dest='output', default="data.json", help='To Catalog')

    args = parser.parse_args()

    e = shop_parser(args.shop)

    # get categorys
    e.get_category()
    # get all article id's
    print("Getting Article ID's")
    e.get_all_article_links()

    #get all article
    e.parse_article()

    print("Writing File (%s)" % str(args.output))
    output_json_file(e.data, args.output)
