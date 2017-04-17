
# coding: utf-8

# In[1]:

import bs4 as bs
import urllib.request
import pandas as pd
import numpy as np
import re
import progressbar
from itertools import chain
from multiprocessing import Pool
import functools
import csv
import requests
from collections import defaultdict
import json
import argparse

def get_session(shop):
    source = urllib.request.urlopen("http://www.dfshop.com/TeamShop/")
    soup = bs.BeautifulSoup(source, 'lxml', parse_only=bs.SoupStrainer('td'))

    g = [i[0]+1 for i in enumerate(soup) if re.match(".+"+str(shop)+".+", str(i[1]))]
    link = [i[1] for i in enumerate(soup) if i[0] == g[0]]
    html = [i['href'] for i in link[0].find_all("a")]

    s = requests.Session()
    r = s.get(html[0])
    soup = bs.BeautifulSoup(r.text, "lxml")
    html = ["http://www.dfshop.com"+i['href'] for i in soup.find_all("a")]
    return html

def post_request(session, page):
    s = requests.Session()
    r = s.get(session[0]+"&f=search&txtArnum="+str(page))
    soup = bs.BeautifulSoup(r.text, "lxml")
    return soup

def clean_article(article):
    article = re.sub("\D+", "", article)
    return article

def clean_price(price):
    price = re.sub("[^0-9.]", "", price)
    return float(price)

def next_page(session):
    s = requests.Session()
    r = s.get(session[0]+"&f=listpage&nav=next")
    soup = bs.BeautifulSoup(r.text, "lxml")
    return soup

def get_category(session):
    links = set()
    for i in soup.find_all("a", href = re.compile(r'.+cat=\d.+')):
        links.add("http://www.dfshop.com/TeamShop"+i['href'])
    return links

def loop_page(session, page):
    l = {}
    pages = []
    from_ = 0
    to_ = 1
    while from_ != to_:
        try:
            if from_ == 0:
                s = post_request(session, page)
            else:
                s = next_page(session)
            page_string = [re.findall("Seite.\d+\svon\s\d+", i.text)[0] for i in s.select("#artListFooter")]
            page = re.findall("\d+", page_string[0])
            from_, to_ = page[0], page[1]
            pages.append([from_, to_])

            article = s.select(".artdesc")
            dimension = s.select(".artdimension")
            price = s.select(".artprice")

            for x, y, z in zip(article, dimension, price):
                artnumbr = re.findall("art=\w{2}\d+", str(x))
                text = re.findall("art=.+>.+<", str(x))
                text2 = re.findall("arttext.+<", str(x))
                price_ = re.findall("artprice.+>\d+.+<", str(z))
                try:
                    artnumbr = clean_article(" ".join(artnumbr))
                    #text = text[0]
                    text3 = " ".join(text2)
                    price_ = clean_price(" ".join(price_))
                    l[artnumbr] = [text2, price_]
                except:
                    continue
        except:
            continue
    return l

def loop_article_href(session):

    init_session(session)

    links = set()
    from_ = int(0)
    to_ = int(1)

    while to_ > from_:
        try:
            soup = next_page_by_cat(session)

            for i in soup.find_all('a', href = re.compile(r'.+art=\w{2}\d+')):
                links.add("http://www.dfshop.com/"+i['href'])

            indexes = [re.findall(r'\d+', i.text) for i in soup.find_all('div',{"id": "artListFooter"})][0]

            from_ = int(indexes[1])
            to_ = int(indexes[2])

            #print(indexes[1], indexes[2])

        except:
            pass

    links = list(links)
    links.sort()

    return links

def init_session(session):
    s = requests.Session()
    r = s.get(session)
    return print("Session Initialized")

def next_page_by_cat(session):
    s = requests.Session()
    session = re.sub("&f=cat&cat=\d.+", "&f=listpage&nav=next", session)
    r = s.get(session)
    soup = bs.BeautifulSoup(r.text, "lxml")
    return soup

def get_all_article_links(categorys):

    container = {}

    for c in categorys:
        cat_string = str(re.findall(r'(cat=\d+\.\d+\.\d+\.\d+)', c)[0])
        print("Parsing: %s" % (re.sub("=", " = ", cat_string)))
        container[cat_string] = loop_article_href(c)

    return container

def parse_shop(shop, catalog=(0,10)):
    session = get_session(shop)
    container = defaultdict(lambda: defaultdict(list))

    for p in range(catalog[0], catalog[1]):
        print("Parsing Catalog Number: %s" % (str(p)))
        container[shop][str(p)] = loop_page(session, p)

    return container

def output_json_file(data, filename):
    with open(args.output, 'w') as outfile:
        json.dump(container, outfile)

    return print("Writing %s to %s" % (str(data), str(filenmae)))


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Parse Sanitary Shop",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--shop', type=str,
                    dest='shop', default="", help='Which Shop to Parse')

    parser.add_argument('--from', type=int,
                        dest='fromcat', default=0, help='From Catalog')

    parser.add_argument('--to', type=int,
                        dest='tocat', default=9, help='To Catalog')

    parser.add_argument('--output', type=str,
                        dest='output', default="data.json", help='To Catalog')

    args = parser.parse_args()

    print("Parsing Shop (%s)" % (str(args.shop)))
    container = parse_shop(args.shop, catalog=(args.fromcat,args.tocat+1))

    print("Writing File...")
        with open(args.output, 'w') as outfile:
        json.dump(container, outfile)
