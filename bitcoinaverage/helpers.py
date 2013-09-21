from decimal import Decimal
import os
import time
import json
from email import utils
import datetime
import requests
from lxml import etree

import bitcoinaverage as ba


def write_log(log_string, message_type='ERROR'):
    timestamp = utils.formatdate(time.time())

    with open(ba.server.LOG_PATH, 'a') as log_file:
        log_string = '%s; %s: %s' % (timestamp, message_type, log_string)
        print log_string
        log_file.write(log_string+'\n')


def write_js_config():
    global ba

    js_config_template = 'var config = $CONFIG_DATA;'

    config_data = {}
    config_data['apiIndexUrl'] = ba.server.API_INDEX_URL
    config_data['apiIndexUrlNoGox'] = ba.server.API_INDEX_URL_NOGOX
    config_data['apiHistoryIndexUrl'] = ba.server.API_INDEX_URL_HISTORY
    config_data['refreshRate'] = str(ba.config.FRONTEND_QUERY_FREQUENCY*1000) #JS requires value in milliseconds
    config_data['currencyOrder'] = ba.config.CURRENCY_LIST
    config_data['legendSlots'] = ba.config.FRONTEND_LEGEND_SLOTS
    config_data['majorCurrencies'] = ba.config.FRONTEND_MAJOR_CURRENCIES
    config_string = js_config_template.replace('$CONFIG_DATA', json.dumps(config_data))

    with open(os.path.join(ba.server.WWW_DOCUMENT_ROOT, 'js', 'config.js'), 'w') as config_file:
        config_file.write(config_string)


def write_fiat_rates_config():
    global ba
    js_config_template = "var fiatCurrencies = $FIAT_CURRENCIES_RATES;"

    google_api_url_template = 'http://www.google.com/ig/calculator?hl=en&q=1USD%3D%3F'

    rate_list = {}

    for currency in ba.config.CURRENCY_LIST:
        api_url = google_api_url_template + currency
        result = requests.get(api_url, headers=ba.config.API_REQUEST_HEADERS).text
        result = result.replace('lhs', '"lhs"')
        result = result.replace('rhs', '"rhs"')
        result = result.replace('error', '"error"')
        result = result.replace('icc', '"icc"')
        result = json.loads(result)
        rate_string = result['rhs']
        rate = ''
        for c in rate_string:
            if c == ' ':
                break
            else:
                rate = rate + c
        try:
            rate = float(rate)
        except ValueError:
            return
        rate = Decimal(rate).quantize(ba.config.DEC_PLACES)
        rate_list[currency] = str(rate)

    config_string = js_config_template
    config_string = config_string.replace('$FIAT_CURRENCIES_RATES', json.dumps(rate_list))

    with open(os.path.join(ba.server.WWW_DOCUMENT_ROOT, 'js', 'fiat_rates.js'), 'w') as fiat_exchange_config_file:
        fiat_exchange_config_file.write(config_string)


def write_html_currency_pages():
    global ba

    template_file_path = os.path.join(ba.server.WWW_DOCUMENT_ROOT, '_currency_page_template.htm')
    with open(template_file_path, 'r') as template_file:
        template = template_file.read()

    api_all_url = '%sticker/all' % ba.server.API_INDEX_URL
    all_rates = requests.get(api_all_url, headers=ba.config.API_REQUEST_HEADERS).json()

    if not os.path.exists(os.path.join(ba.server.WWW_DOCUMENT_ROOT, ba.config.CURRENCY_DUMMY_PAGES_SUBFOLDER_NAME)):
        os.makedirs(os.path.join(ba.server.WWW_DOCUMENT_ROOT, ba.config.CURRENCY_DUMMY_PAGES_SUBFOLDER_NAME))

    for currency_code in ba.config.CURRENCY_LIST:
        currency_rate = all_rates[currency_code]['last']
        currency_page_contents = template
        currency_page_contents = currency_page_contents.replace('$RATE$', str(Decimal(currency_rate).quantize(ba.config.DEC_PLACES)))
        currency_page_contents = currency_page_contents.replace('$CURRENCY_CODE$', currency_code)

        with open(os.path.join(ba.server.WWW_DOCUMENT_ROOT,
                               ba.config.CURRENCY_DUMMY_PAGES_SUBFOLDER_NAME,
                               ('%s.htm' % currency_code.lower())), 'w') as currency_page_file:
            currency_page_file.write(currency_page_contents)

    template_file_path = os.path.join(ba.server.WWW_DOCUMENT_ROOT, '_charts_page_template.htm')
    with open(template_file_path, 'r') as template_file:
        template = template_file.read()

    if not os.path.exists(os.path.join(ba.server.WWW_DOCUMENT_ROOT, ba.config.CHARTS_DUMMY_PAGES_SUBFOLDER_NAME)):
        os.makedirs(os.path.join(ba.server.WWW_DOCUMENT_ROOT, ba.config.CHARTS_DUMMY_PAGES_SUBFOLDER_NAME))

    index = 0
    for currency_code in ba.config.CURRENCY_LIST:
        currency_rate = all_rates[currency_code]['last']
        chart_page_contents = template
        chart_page_contents = chart_page_contents.replace('$RATE$', str(Decimal(currency_rate).quantize(ba.config.DEC_PLACES)))
        chart_page_contents = chart_page_contents.replace('$CURRENCY_CODE$', currency_code)
        with open(os.path.join(ba.server.WWW_DOCUMENT_ROOT,
                               ba.config.CHARTS_DUMMY_PAGES_SUBFOLDER_NAME,
                               ('%s.htm' % currency_code.lower())), 'w') as chart_page_file:
            chart_page_file.write(chart_page_contents)


        index = index + 1
        if index == ba.config.FRONTEND_MAJOR_CURRENCIES:
            break


def write_sitemap():
    def _sitemap_append_url(url_str, lastmod_date=None, changefreq_str=None, priority_str=None):
        url = etree.Element('url')
        loc = etree.Element('loc')
        loc.text = url_str
        url.append(loc)
        if lastmod_date is not None:
            lastmod = etree.Element('lastmod')
            lastmod.text = lastmod_date.strftime('%Y-%m-%d')
            url.append(lastmod)
        if changefreq_str is not None:
            changefreq = etree.Element('changefreq')
            changefreq.text = changefreq_str
            url.append(changefreq)
        if priority_str is not None:
            priority = etree.Element('priority')
            priority.text = priority_str
            url.append(priority)
        return url

    urlset = etree.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')

    index_url = '%s%s' % (ba.server.FRONTEND_INDEX_URL, 'index.htm')
    today = datetime.datetime.today()
    urlset.append(_sitemap_append_url('%s%s' % (ba.server.FRONTEND_INDEX_URL, 'index.htm'), today, 'hourly', '1.0'))
    urlset.append(_sitemap_append_url('%s%s' % (ba.server.FRONTEND_INDEX_URL, 'faq.htm'), today, 'monthly', '0.5'))
    urlset.append(_sitemap_append_url('%s%s' % (ba.server.FRONTEND_INDEX_URL, 'blog.htm'), today, 'weekly', '1.0'))
    urlset.append(_sitemap_append_url('%s%s' % (ba.server.FRONTEND_INDEX_URL, 'charts.htm'), today, 'hourly', '0.8'))

    currency_static_seo_pages_dir = os.path.join(ba.server.WWW_DOCUMENT_ROOT, ba.config.CURRENCY_DUMMY_PAGES_SUBFOLDER_NAME)
    for dirname, dirnames, filenames in os.walk(currency_static_seo_pages_dir):
        for filename in filenames:
            urlset.append(_sitemap_append_url('%s%s/%s' % (ba.server.FRONTEND_INDEX_URL,
                                                        ba.config.CURRENCY_DUMMY_PAGES_SUBFOLDER_NAME,
                                                        filename), today, 'hourly', '1.0'))
    charts_static_seo_pages_dir = os.path.join(ba.server.WWW_DOCUMENT_ROOT, ba.config.CHARTS_DUMMY_PAGES_SUBFOLDER_NAME)
    for dirname, dirnames, filenames in os.walk(currency_static_seo_pages_dir):
        for filename in filenames:
            urlset.append(_sitemap_append_url('%s%s/%s' % (ba.server.FRONTEND_INDEX_URL,
                                                        ba.config.CHARTS_DUMMY_PAGES_SUBFOLDER_NAME,
                                                        filename), today, 'hourly', '0.8'))

    xml_sitemap_contents = '<?xml version="1.0" encoding="UTF-8"?>\n' + etree.tostring(urlset, pretty_print=True)
    with open(os.path.join(ba.server.WWW_DOCUMENT_ROOT, 'sitemap.xml'), 'w') as sitemap_file:
        sitemap_file.write(xml_sitemap_contents)





