import urllib
import urllib2
from bs4 import BeautifulSoup
import requests
from geopy.geocoders import Nominatim
import json
from collections import defaultdict
import StringIO
import pandas as pd
import codecs
import csv
import cStringIO

headers = ["street_address",
           "housing_address",
           "full_address",
           "postal_code",
           "lat",
           "lon",
           "municipality",
           "city",
           "country",
           "sold_for",
           "date_sold",
           "sales_type",
           "price_per_square_meter",
           "nRooms",
           "housing_type",
           "size_square_meters",
           "housing_built",
           "price_percentage_difference"
           ]


class UnicodeWriter:
    def __init__(self, f, dialect=csv.excel, encoding="utf-8-sig", **kwds):
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        '''writerow(unicode) -> None
        This function takes a Unicode string and encodes it to the output.
        '''
        self.writer.writerow([s.encode("utf-8") for s in row])
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        data = self.encoder.encode(data)
        self.stream.write(data)
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)



def read_json(filepath):
    with open(filepath, "rb") as f:
        for row in f:
            yield json.loads(row)


def convert_json_to_csv(files):
    csv_sales = []
    for f in files:
        print "Parsing {0}".format(f)
        sales = read_json(f)
        for sale in sales:
            csv_sales.append(sale)

    with open("./all_addresses.csv", "wb") as fo:
        writer = UnicodeWriter(fo)
        for sale in csv_sales:
            writer.writerow([sale['street_address'], sale['city'], sale['postal_code'], "None"])
    """
    with codecs.open("./all_addresses.csv", "wb", "utf-8") as fo:
        writer = csv.DictWriter(fo, fieldnames=csv_sales[0].keys())
        for sale in csv_sales:
            try:
                print dict((k, v.decode("utf-8").encode('utf-8')) if isinstance(v, str) else (k, v) for k, v in sale.items())
                writer.writerow(dict((k, v) if isinstance(v, str) else (k, v) for k, v in sale.items()))
            except TypeError:
                print sale
                return sale
    """




def parse_row(tds):
    """ Specific row parser for boliga data """
    address = tds[0]
    # Parse address
    # To do this get street name and number, as well as postal code and municipality
    # Furthermore get convert address to lat and lon.
    iterator = address.stripped_strings

    row = {}

    # Param
    full_address = iterator.next()
    row["full_address"] = full_address
    # If the street address contains a comma it also contains information on the exact housing.
    if "," in full_address:
        split_address = full_address.split(",")
        # Params
        row["street_address"] = split_address[0].strip()
        # Params
        row["housing_address"] = split_address[1].strip()
    else:
        # Params
        row["street_address"] = full_address
        # Params
        row["housing_address"] = None


    municipality_and_postal_code = iterator.next().split(" ")

    # Params
    row["postal_code"] = municipality_and_postal_code[0]
    row["municipality"] = municipality_and_postal_code[1]

    # Param
    row["sales_price"] = float(tds[1].text.replace(".", "").replace(",", ""))

    sales_date_and_type = tds[2]

    iterator = sales_date_and_type.stripped_strings
    # Params
    row["date"] = iterator.next()
    row["sales_type"] = iterator.next()
    try:
        row["price_per_square_meter"] = float(tds[3].text.replace(".", "").replace(",", ""))
    except:
        row["price_per_square_meter"] = row["sales_price"] / float(tds[6].text)
    row["nRooms"] = int(tds[4].text)
    row["housing_type"] = "Appartment"
    row["city"] = "Copenhagen"
    row["size_square_meters"] = float(tds[6].text.replace(".", "").replace(",", ""))
    row["housing_built"] = int(tds[7].text)
    if tds[8].text.replace("%", "").strip() in ["", None]:
        row["price_percentage_difference"] = None
    else:
        row["price_percentage_difference"] = float(tds[8].text.replace("%", "").strip()) / 100.0
    return row


def get_results(page):
    """ Parses the current page for the search results and appends it to the data """
    soup = BeautifulSoup(page, "lxml")
    for tr in soup.find(id="searchresult").findAll("tr")[1:]:
        sale = {}
        tds = tr.findAll("td")
        row = parse_row(tds)
    results = []
    return results


def get_all_pages():
    website = "http://www.boliga.dk/salg/resultater?so=1&sort=omregnings_dato-d&maxsaledate=today&iPostnr=1000-2730&gade=&type=Ejerlejlighed&minsaledate=1992&p=[page_num]"
    i = 1

    search_results = parse_result_rows(website.replace("[page_num]", str(1)))
    sales = []
    while search_results != []:
        print ">> Parsing page number {0}".format(i)
        for row in search_results:
            row_elements = row.findAll("td")
            sale = parse_row(row_elements)
            sales.append(sale)
        i += 1
        # Load next page
        search_results = parse_result_rows(website.replace("[page_num]", str(i)))

        # Write rows to file
        if (i % 100) == 0:
            with codecs.open("./sales_info_newer_{0}.json".format(i / 100), "w") as fo:
                for sale in sales:
                    fo.write(json.dumps(sale) + "\n")
            sales = []

    if sales != []:
        with codecs.open("./sales_info_newer_last_{0}.json".format(i / 100 + 1), "w") as fo:
            for sale in sales:
                fo.write(json.dumps(sale) + "\n")


def parse_result_rows(url):
    html = parse_site(url)
    soup = BeautifulSoup(html, "lxml")
    search_results = soup.find(id="searchresult").findAll("tr")[1:]
    return search_results


def parse_site(url):
    """ Gets a given url as a html string """
    req = urllib2.Request(url)
    response = urllib2.urlopen(req)
    return response.read()



