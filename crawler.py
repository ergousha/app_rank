import os
import json
import boto3
from time import sleep
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

category_address = os.environ['CategoryAddress']
firehose_name = os.environ['Firehose']

client = boto3.client('firehose')


def close_cookie_modal(browser):
    iframes = browser.find_elements(by=By.TAG_NAME, value='iframe')
    for iframe in iframes:
        try:
            browser.switch_to.frame(iframe)
            browser.find_element(By.XPATH, '//button[text()="OK, Got it"]').click()
            print("Cookie acceptance dialog found!")
            return
        except:
            pass
    browser.switch_to.default_content()


def scroll_bottom(browser):
    browser.find_element(By.XPATH, '//a[text()="See more"]').click()
    for times in range(5):
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(2)


def get_ranks(browser, category, country):
    apps = []
    rank = 0
    for elem in browser.find_elements(By.CSS_SELECTOR, "a[href*='/store/apps/details?id=']"):
        try:
            elem_with_title = elem.find_element(By.XPATH, './/div')
            if elem_with_title.is_displayed():
                href = elem.get_attribute('href')
                app_code = href[href.rfind('=') + 1:]
                app_name = elem_with_title.get_attribute('title')
                apps.append({
                    "code": app_code,
                    "name": app_name,
                    "rank": rank + 1,
                    "category": category,
                    "country": country,
                    "store": 'Google',
                    "date": datetime.now().isoformat()
                })
                rank += 1
        except:
            pass
    return apps


def main(event, context):
    options = Options()
    options.binary_location = '/opt/headless-chromium'
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--single-process')
    options.add_argument('--disable-dev-shm-usage')

    print('params', event['Records'][0]['body'])
    params = json.loads(event['Records'][0]['body'].replace('\'', '"'))
    category_address_formatted = category_address.format(params['category'], params['country'])
    print('category_address_formatted', category_address_formatted)

    browser = webdriver.Chrome('/opt/chromedriver', chrome_options=options)
    browser.get(category_address_formatted)

    close_cookie_modal(browser)
    scroll_bottom(browser)
    rank_list = get_ranks(browser, params['category'], params['country'])
    print('rank_list', rank_list)

    records = []
    for rank in rank_list:
        records.append({
            "Data": json.dumps(rank)
        })

    response = client.put_record_batch(
        DeliveryStreamName=firehose_name,
        Records=records
    )
    print('response', response)

    return 'success'
