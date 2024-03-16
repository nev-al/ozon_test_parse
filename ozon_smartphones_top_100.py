import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium import webdriver
from openai_api_key import api_key
import time

ITEM_QTY_TO_PARSE = 100
PAGE = 1


def extract_from_description(descr: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
             "content": "You will be provided with a smartphone description, and your task is to extract an operating "
                        "system name and its version from it. Do not include any explanations, only provide one "
                        "string, for example like these 'iOS 16', 'Android 13', 'MIUI 14', 'HyperOS 11'. "
                        "If you could not find any relatable data just send empty string like this ''."},
            {"role": "user", "content": descr}
        ]
    )

    return completion.choices[0].message.content


def write_tuple_to_csv(tup: tuple):
    import csv
    with open('result-file.txt', 'a') as fl:
        writer = csv.writer(fl)
        writer.writerow(tup,)


def create_driver() -> uc.Chrome:
    options = uc.ChromeOptions()
    options.binary_location = '/usr/bin/brave-browser'
    options.add_argument('--start-maximized')
    driver = uc.Chrome(options=options, debug=True)
    driver.implicitly_wait(60)
    driver.set_page_load_timeout(60)
    driver.set_script_timeout(60)
    return driver


def open_link(driver: uc.Chrome):
    driver.get("https://ozon.ru")
    time.sleep(20)


def open_category(driver: uc.Chrome):
    elem = driver.find_element(By.ID, 'stickyHeader')
    div = elem.find_element(By.TAG_NAME, 'div')
    div.click()
    time.sleep(1)
    driver.find_element(By.XPATH, "//*[contains(text(), 'Телефоны и смарт-часы')]").click()
    driver.close()
    driver.switch_to.window(driver.window_handles[0])


def apply_filter_high_rate(driver: uc.Chrome):
    f = driver.find_element(By.NAME, 'filter')
    f.click()
    for i in range(5):
        f.send_keys(webdriver.Keys.ARROW_DOWN)
    f.send_keys(webdriver.Keys.ENTER)
    time.sleep(5)


def go_to_next_page(driver: uc.Chrome, page_count_forward: int = 1):
    global PAGE
    for i in range(page_count_forward):
        url = driver.current_url[driver.current_url.index('ozon.ru') + len('ozon.ru'):driver.current_url.index('/?')]
        next_list = driver.find_elements(By.XPATH, f'//a[contains(@href,"{url}")]')
        next_page = None
        for i in next_list:
            if i.text == 'Дальше':
                next_page = i
        if next_page:
            next_page.click()
        PAGE += 1
        time.sleep(5)


def get_all_phones_on_page(driver: uc.Chrome) -> list:
    time.sleep(3)
    paginator = driver.find_element(By.ID, 'paginatorContent')
    lst = paginator.find_elements(By.XPATH, '//*[@id="paginatorContent"]/div/div/*')
    phones = []
    for i in lst:
        phones.append(i) if 'Тип: Смартфон' in i.text else None
    return phones


def process(driver: uc.Chrome):
    result = []
    counter = 0
    while counter < ITEM_QTY_TO_PARSE:
        time.sleep(3)
        phones = get_all_phones_on_page(driver)
        for i in range(len(phones)):
            link = phones[i].find_element(By.XPATH, './div[1]/a')
            link.send_keys(webdriver.Keys.CONTROL, webdriver.Keys.ENTER)
            driver.switch_to.window(driver.window_handles[1])
            parsed = parse_phone_page(driver)
            result.append(parsed)
            write_tuple_to_csv(parsed)
            counter += 1
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            print([i[2] for i in result])
        go_to_next_page(driver)
    return result


def parse_phone_page(driver: uc.Chrome) -> (str, str):
    os_ver = None
    try:
        os_name_parent = driver.find_element(By.XPATH, "//*[contains(text(), 'Операционная система')]/..") \
            .find_element(By.XPATH, './..')
        os_name = os_name_parent.text.split('\n')[1]
        os_ver_parent = driver.find_element(By.XPATH, f"//*[contains(text(), 'Версия {os_name}')]/..") \
            .find_element(By.XPATH, './..')
        os_ver = os_ver_parent.text.split('\n')[1]
    except:
        t = time.time()
        descr = driver.find_element(By.ID, 'section-description').text
        os_ver = extract_from_description(descr)
        print('openai parse time: ', time.time() - t)

    return driver.title, driver.current_url, os_ver, PAGE


def pd_count_os_data(csv_file_paht: str = 'result-file.txt'):
    import pandas as pd
    df = pd.read_csv(csv_file_paht, header=None)
    df.columns = ['titile', 'link', 'os', 'page']
    df1 = df['os'].apply(lambda x: x.rstrip('.x'))
    df1.value_counts()


if __name__ == '__main__':
    driver = create_driver()
    open_link(driver)
    open_category(driver)
    apply_filter_high_rate(driver)
    go_to_next_page(driver, 4)
    print(process(driver))
    driver.close()
    driver.quit()
