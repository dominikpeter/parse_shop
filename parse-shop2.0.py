# coding: utf-8

import bs4 as bs
import urllib.request
import pandas as pd
import numpy as np
import re
from itertools import chain
from multiprocessing import Pool
import functools
import csv
import requests
from collections import defaultdict
import json
import argparse
from requests import ConnectionError


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

def get_category(session):
    s = requests.Session()
    r = s.get(session)
    soup = bs.BeautifulSoup(r.text, 'lxml', parse_only=bs.SoupStrainer('a'))
    links = set()
    for i in soup.find_all("a", href = re.compile(r'.+cat=\d.+')):
        links.add("http://www.dfshop.com/"+i['href'])
    links = list(links)
    links.sort()
    return links

def next_page_by_cat(session):
    s = requests.Session()
    session = re.sub("&f=cat&cat=\d.+", "&f=listpage&nav=next", session)
    r = s.get(session)
    soup = bs.BeautifulSoup(r.text, "lxml")
    return soup


def init_session(session):
    s = requests.Session()
    r = s.get(session)
    #return print("Session Initialized")


def loop_article_href(session):
    init_session(session)
    links = set()
    from_, to_ = int(0), int(1)
    while to_ > from_:
        try:
            soup = next_page_by_cat(session)

            for i in soup.find_all('a', href = re.compile(r'.+art=\w{2}\d+')):
                links.add(re.findall(r'art=\w{2}\d+',i['href'])[0][4:])

            indexes = [re.findall(r'\d+', i.text) for i in soup.find_all('div',{"id": "artListFooter"})][0]

            from_ = int(indexes[1])
            to_ = int(indexes[2])

            percent = float(indexes[1]) / float(indexes[2])

            if round(percent,1) in range(10, 110, 10):
                print("Parsing: %s of %s (%s)" % (str(indexes[1]), str(indexes[2]), str(round(percent,1))))
        except (ConnectionError, Exception) as e:
            print(e)
            continue

    links = list(links)
    links.sort()

    return links


def get_all_article_links(categorys):
    container = {}
    for c in categorys:
        cat_string = str(re.findall(r'(cat=\d+\.\d+\.\d+\.\d+)', c)[0])
        print("Parsing: %s" % (re.sub("=", " = ", cat_string)))
        container[cat_string] = loop_article_href(c)

    return container

def output_json_file(data, filename):
    with open(filename, 'w') as outfile:
        json.dump(data, outfile)

    return print("Writing %s" % (str(filename)))

def read_json_file(filename):
    with open(filename) as data_file:
        data = json.load(data_file)
    return data


def parse_article(session, idArticle):
    container = {}
    for article in idArticle.values():
        for i in article:
            try:
                s = requests.Session()
                r = s.get(session + "&f=art&art=" + str(i))

                soup = bs.BeautifulSoup(r.text, 'lxml', parse_only=bs.SoupStrainer('div', {"id": "artDetailMain"}))
                text = [re.sub("\n", "", i.text) for i in soup.find_all("div", {'id': 'artDetailDescRow'})]
                idsupplier = [re.sub("\n", "", i.text) for i in soup.find_all("div", {'id': 'artDetailLiefArnumRow'})]
                price = [re.findall("\d+\.\d+", i.text)[0] for i in soup.find_all("div", {'id': 'artDetailLiefPriceRow'})]

                container[str(i)] = [text, idsupplier, price]
            except:
                continue
    return container

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Parse Sanitary Shop",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--shop', type=str,
                    dest='shop', default="", help='Which Shop to Parse')

    parser.add_argument('--outputId', type=str,
                        dest='outputId', default="data_article.json", help='To Catalog')

    parser.add_argument('--outputMain', type=str,
                        dest='outputMain', default="data_shop.json", help='To Catalog')

    parser.add_argument('--refresh', dest='refresh', default=True, help="Parse Article ID's")


    args = parser.parse_args()

    session = get_session(args.shop)[0]
    cats = get_category(session)

    if args.refresh:
        print("Parse Article ID's")
        article_hrefs = get_all_article_links(cats)
        output_json_file(article_hrefs, args.outputId)


    data = read_json_file(args.outputId)

    print("Parse Shop...")
    parsed_data = parse_article(session, data)


    print("Writing File")
    output_json_file(parsed_data, args.outputMain)
