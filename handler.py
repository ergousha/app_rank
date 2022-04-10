import os
import uuid
import boto3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

root_address = os.environ['RootAddress']
countries = os.environ['Countries'].split()
sqs_url = os.environ['QueueUrl']


def get_category_list(browser):
    categories = []
    browser.find_element(By.XPATH, '//span[text()="Categories"]//ancestor::button').click()
    for elem in browser.find_elements(By.CSS_SELECTOR, "a[href*='/store/apps/category/']"):
        href = elem.get_attribute('href')
        categories.append(href[href.rfind('/')+1:])
    return categories


def write_sqs(params):
    sqs_client = boto3.client("sqs")
    max_batch_size = 10  # current maximum allowed
    chunks = [params[x:x + max_batch_size] for x in range(0, len(params), max_batch_size)]
    for chunk in chunks:
        entries = []
        for x in chunk:
            entry = {'Id': str(uuid.uuid4()),
                     'MessageBody': str(x)}
            entries.append(entry)
        sqs_client.send_message_batch(QueueUrl=sqs_url, Entries=entries)


def main(event, context):
    options = Options()
    options.binary_location = '/opt/headless-chromium'
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--single-process')
    options.add_argument('--disable-dev-shm-usage')

    browser = webdriver.Chrome('/opt/chromedriver', chrome_options=options)

    params = []
    for country in countries:
        browser.get(root_address.format(country))
        categories = get_category_list(browser)
        for category in categories:
            params.append({
                "country": country,
                "category": category
            })

    browser.close()
    browser.quit()

    print('params', params)
    write_sqs(params)

    return 'success'
