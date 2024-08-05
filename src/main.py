from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import date, timedelta
import requests
import json

def get_ttdetail(browser, golf_course, search_date, params):
    url = (
        f'https://www.golfnow.com/tee-times/facility/{golf_course}/search'
        f'#sortby=Date&view=List&date={search_date}&holes={params["holes"]}&timemax={params["timemax"] * 2}'
        f'&timemin={params["timemin"] * 2}&players={params["players"]}&pricemax={params["pricemax"]}'
        f'&pricemin={params["pricemax"]}&timeperiod=3&promotedcampaignsonly=false&hotdealsonly=true'
    )

    browser.get(url)
    time.sleep(1)
    soup = BeautifulSoup(browser.page_source, 'html.parser')
    hotdeal = soup.find_all(attrs={'class': 'hot-deal-flame tt-details'})
    
    if hotdeal:
        tdetail = soup.find_all(attrs={'class': 'tt-detail'})
        players_lst = [x.find('div', class_='players').text.strip() if x.find('div', class_='players') else '' for x in tdetail]
        holes_lst = [x.find('div', class_='holes').text.strip().split(' ')[0] if x.find('div', class_='holes') else '' for x in tdetail]
        carts_lst = [x.find('div', class_='carts').text.strip().replace('Included', 'Cart') if x.find('div', class_='carts') else '' for x in tdetail]

        tprices = soup.find_all(attrs={'class': 'price'})
        prices_lst = ["$" + x.text.strip() for x in tprices]
        if len(prices_lst) < len(tdetail):
            prices_lst += ["$"] * (len(tdetail) - len(prices_lst))

        ttimes = soup.find_all(attrs={'class': 'columns small-7 large-6 time-meridian'})
        ttimes_lst = [x.text.strip().split(' ')[0] for x in ttimes]

        course_name = soup.find(id="master-page-title").text
        ttdetail = { 
            'Golf Course': course_name[:-3].replace(' Tee Times', ''),
            'Tee Time': ttimes_lst,
            'Date': search_date,
            'Price': prices_lst,
            'Player': players_lst,
            'Hole': holes_lst,
            'Cart': carts_lst,
        }
        return pd.DataFrame(ttdetail)
    
    return pd.DataFrame()

def get_courses(browser, city, search_date, params):
    url = (
        f'https://www.golfnow.com/tee-times/hot-deals#qc=GeoLocation&q={city.lower().replace(" ", "+")}'
        f'&sortby=Facilities.Distance.0&view=Course&date={search_date}&holes={params["holes"]}'
        f'&radius={params["radius"]}&timemax={params["timemax"] * 2}&timemin={params["timemin"] * 2}'
        f'&players={params["players"]}&pricemax={params["pricemax"]}&pricemin={params["pricemax"]}'
        f'&promotedcampaignsonly=false&hotdealsonly=true&longitude=-121.893028&latitude=37.335480'
    )
    browser.get(url)
    time.sleep(1)
    soup = BeautifulSoup(browser.page_source, 'html.parser')
    links = soup.find_all('a', href=True)
    results = [link['href'].split('/')[3] for link in links if '/tee-times/facility/' in link['href']]
    return list(set(results))

def send_message_to_topic(bot_token, chat_id, topic_id, message):
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    params = {
        'chat_id': chat_id,
        'parse_mode': 'Markdown',
        'text': message,
        'reply_to_message_id': topic_id
    }
    response = requests.get(url, params=params)
    return response.json()

def delete_message(bot_token, chat_id, topic_id, message_id):
    url = f'https://api.telegram.org/bot{bot_token}/deleteMessage'
    params = {
        'chat_id': chat_id,
        'message_thread_id': topic_id,
        'message_id': message_id
    }
    try:
        response = requests.get(url, params=params)
        return response.json().get('ok', False)
    except Exception:
        return False
    
def delete_all_messages(bot_token, chat_id, topic_id):
    message_id = send_message_to_topic(bot_token, chat_id, topic_id, 'Last message')['result']['message_id']
    while delete_message(bot_token, chat_id, topic_id, message_id):
        message_id -= 1

### MAIN ###

golf_courses_favorite = [
    '460-bay-view-golf-club',
    '1720-gilroy-golf-course',
    '9126-coyote-creek-golf-club-valley-course',
    '9127-coyote-creek-golf-club-tournament-course',
    '3821-cinnabar-hills-golf-club',
    '160-spring-valley-golf-course',
    '1497-sunnyvale-golf-course',
    '2908-rancho-del-pueblo-golf-course',
]

geckodriver_path = r'/usr/local/bin/geckodriver'

options = FirefoxOptions()
options.headless = True
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

service = FirefoxService(executable_path=geckodriver_path)
browser = webdriver.Firefox(service=service, options=options)

params = {
    'holes': 3,
    'radius': 30,
    'timemin': 10,
    'timemax': 15,
    'players': 0,
    'pricemin': 10,
    'pricemax': 60
}

tee_df = pd.DataFrame()

for golf_course in golf_courses_favorite:
    for i in range(1, 2):
        search_date = (date.today() + timedelta(i)).strftime('%b+%d+%Y')
        course_df = get_ttdetail(browser, golf_course, search_date, params)
        if not course_df.empty:
            tee_df = pd.concat([tee_df, course_df], axis=0)

browser.quit()

jsonfile = r'.dot_files/Telegram_bot'
with open(jsonfile, 'r') as f:
    telegram_bot = json.load(f)

bot_token = telegram_bot['bot_token']
scan_time = time.strftime('%H:%M %a, %Y/%m/%d')
message_scan_time = f'Hot Deals in next 2 weeks were scanned at *{scan_time}*\n'

message_ids_file = r'.dot_files/message_ids'
with open(message_ids_file, 'r') as f:
    message_ids = json.load(f)

chat_id = telegram_bot['chat_id_18']
topic_id = telegram_bot['topic_id']

tee_18 = tee_df[tee_df['Hole'] == '18'].drop('Hole', axis=1)
golfcourses = tee_18['Golf Course'].unique()

delete_all_messages(bot_token, chat_id, topic_id)

message_detail = send_message_to_topic(bot_token, chat_id, topic_id, message_scan_time)
if message_detail['ok']:
    message_ids['message_ids_18'].append(message_detail['result']['message_id'])

for golfcourse in golfcourses:
    df = tee_18[tee_18['Golf Course'] == golfcourse].drop('Golf Course', axis=1)
    message = f'*{golfcourse}*\n{df.to_string(header=False, index=False)}\n\n'
    message = message.replace('  ', ' ')
    message_detail = send_message_to_topic(bot_token, chat_id, topic_id, message)
    if message_detail['ok']:
       message_ids['message_ids_18'].append(message_detail['result']['message_id'])

with open(message_ids_file, 'w') as f:
    json.dump(message_ids, f)
