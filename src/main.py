from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from bs4 import BeautifulSoup
import pandas as pd
import time, os
from datetime import date, timedelta
import requests
import json
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

jsonfile = '/home/debian/hotdeals/.dot_files/Telegram_bot'
with open(jsonfile, 'r') as f:        
    telegram_bot = json.load(f)

bot_token = telegram_bot['bot_token']
chat_id = telegram_bot['chat_id_18']
topic_id = telegram_bot['topic_id']

def get_ttdetail(browser, golf_course, date_, params):

    search_date=date_.strftime('%b+%d+%Y')
    url = f'https://www.golfnow.com/tee-times/facility/{golf_course}/search' \
        f'#date={search_date}' \
        f'&promotedcampaignsonly=false' \
        f'&hotdealsonly={params["hotdealsonly"]}' \
        f'&sortby=Date&view=List' \
        f'&holes={params["holes"]}' \
        f'&players={params["players"]}' \
        f'&timemin={params["timemin"]}' \
        f'&timemax={params["timemax"]}' \
        f'&pricemin={params["pricemin"]}' \
        f'&pricemax={params["pricemax"]}' 
        
    browser.get(url)
    # print(f"\nSeaching at {browser.title} on {date_.strftime('%a, %b %d')}")
    # print(url)
    time.sleep(1)
    soup = BeautifulSoup(browser.page_source, 'html.parser')

    hotdeal = soup.find_all(attrs={'class': 'hot-deal-flame tt-details'})
    course_df = pd.DataFrame()
    
    if hotdeal:
        tdetail = soup.find_all(attrs={'class':'tt-detail'})
        if 'Golfers' in str(tdetail):
            players_lst = [str(x).split('<')[3].split('>')[1].strip() for x in tdetail] 
        else:
            players_lst = ['']*len(tdetail)
        if 'Holes' in str(tdetail):
            holes_lst = [str(x).split('<')[5].split(' ')[1].strip() for x in tdetail] 
        else:
            holes_lst = ['']*len(tdetail)
        if 'Cart' in str(tdetail):
            carts_lst = [str(x).split('<')[7].split('>')[1].strip().replace('Included','Cart') for x in tdetail]
        else:
            carts_lst = ['']*len(tdetail)

        tprices = soup.find_all(attrs={'class':'price'})
        prices_lst = ['$'+str(x).split('"')[3] for x in tprices]

        ttimes = soup.find_all(attrs={'class':'columns small-7 large-6 time-meridian display-font color-black'})
        ttimes_lst = [x.text.strip().split(' ')[0] for x in ttimes]

        # Pad lists to ensure all lists are of the same length as tdetail
        max_len = len(tdetail)
        players_lst += [''] * (max_len - len(players_lst))
        holes_lst += [''] * (max_len - len(holes_lst))
        carts_lst += [''] * (max_len - len(carts_lst))
        prices_lst += ['$'] * (max_len - len(prices_lst))
        ttimes_lst += [''] * (max_len - len(ttimes_lst))
        
        # Extract course name and create DataFrame
        course_name = soup.find(id="master-page-title").text

        ttdetail = { 'Golf Course': course_name[:-3].replace(' Tee Times',''),
                'Tee Time': ttimes_lst,
                'Date': date_.strftime('%a, %b %d'),
                'Price': prices_lst,
                'Player': players_lst,
                'Hole': holes_lst,
                'Cart': carts_lst,
            }
        # print(ttdetail)
        course_df = pd.DataFrame(ttdetail)
        message = f'{course_df.to_string(header=False, index=False)}\n'
        print(message.replace('  ', ' '))
        
    return course_df

def get_courses(browser, city, radius, search_date, params):
    url = (
        f'https://www.golfnow.com/tee-times/hot-deals#qc=GeoLocation&q={city.lower().replace(" ", "+")}'
        f'&sortby=Facilities.Distance.0&view=Course&date={search_date}&holes={params["holes"]}'
        f'&radius={radius}&timemin={params["timemin"]}&timemax={params["timemax"]}'
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
        'message_thread_id': topic_id
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
        
def convert_time_to_mapping_value(time_str):
    """Convert standard time (e.g., '10:00AM') to the mapping value based on the provided logic."""
    time_map = {
        "5:00AM": 10,
        "5:30AM": 11,
        "6:00AM": 12,
        "6:30AM": 13,
        "7:00AM": 14,
        "7:30AM": 15,
        "8:00AM": 16,
        "8:30AM": 17,
        "9:00AM": 18,
        "9:30AM": 19,
        "10:00AM": 20,
        "10:30AM": 21,
        "11:00AM": 22,
        "11:30AM": 23,
        "12:00PM": 24,
        "12:30PM": 25,
        "1:00PM": 26,
        "1:30PM": 27,
        "2:00PM": 28,
        "2:30PM": 29,
        "3:00PM": 30,
        "3:30PM": 31,
        "4:00PM": 32,
        "4:30PM": 33,
        "5:00PM": 34,
        "5:30PM": 35,
        "6:00PM": 36,
        "6:30PM": 37,
        "7:00PM": 38,
        "7:30PM": 39,
        "8:00PM": 40
    }
    return time_map.get(time_str, 20)  # Default to 10:00AM if not found

def golfnow(golf_courses="Favorites", days=7, timemin="10:00AM", timemax="3:00PM", pricemin=8, pricemax=60, browser=None):
    # Convert standard time to mapping values
    timemin_mapped = convert_time_to_mapping_value(timemin)
    timemax_mapped = convert_time_to_mapping_value(timemax)
    
    # Set default value for golf_courses if not provided
    if golf_courses.lower() == "favorites":
        golf_courses = [
            '460-bay-view-golf-club',
            '1720-gilroy-golf-course',
            '9126-coyote-creek-golf-club-valley-course',
            '9127-coyote-creek-golf-club-tournament-course',
            '3821-cinnabar-hills-golf-club',
            '160-spring-valley-golf-course',
            '1497-sunnyvale-golf-course',
            '2908-rancho-del-pueblo-golf-course'
        ]
    else:
        golf_courses = [
            '460-bay-view-golf-club',
            '1720-gilroy-golf-course',
            '9126-coyote-creek-golf-club-valley-course',
            '9127-coyote-creek-golf-club-tournament-course',
            '3821-cinnabar-hills-golf-club',
            '160-spring-valley-golf-course',
            '1497-sunnyvale-golf-course',
            '2908-rancho-del-pueblo-golf-course',
            '241-san-ramon-golf-club',
            '929-deep-cliff-golf-course',
            '101-eagle-ridge-golf-club',
            '6012-shoreline-golf-links',
            '1450-los-lagos-golf-course'
            '586-pleasanton-golf-center',
            '432-the-course-at-wente-vineyards',
            '98-delaveaga-golf-course',
            '1323-fremont-park-golf-course',
            '8616-blackberry-farm-golf-course',
            '1432-callippe-preserve-golf-course',
            '15719-sunken-gardens-golf-course'
        ]

    params = {
        'hotdealsonly': 'true',
        'holes': 2,
        'players': 0,
        'timemin': timemin_mapped,
        'timemax': timemax_mapped,
        'pricemin': pricemin,
        'pricemax': pricemax
    }
    
    # Explanation of the Mapping
    # holes: 1 corresponds to 9-hole, 2 corresponds to 18-hole, 3 corresponds to any hole
    # players: 1-4 corresponds to 1-4 players, 0 corresponds to any players
    # timemin/timemax = 10 corresponds to 5:00AM. Each subsequent value increments by 30 minutes
    # timemin / timemax: 20 corresponds to 10:00AM, 24 corresponds to 12:00PM, 30 corresponds to 3:00PM

    tee_df = pd.DataFrame()
    
    for golf_course in golf_courses:
        for i in range(1, days):
            date_ = date.today() + timedelta(i)
            course_df = get_ttdetail(browser, golf_course, date_, params)
            if not course_df.empty:
                tee_df = pd.concat([tee_df, course_df], axis=0)
    
    return tee_df

def parse_command_params(command_args):
    params = {
        'golf_courses': "Favorites",
        'days': 7,
        'timemin': "12:00PM",  # Default to 12:00PM
        'timemax': "3:00PM",  # Default to 3:00PM
        'pricemin': 8,
        'pricemax': 60
    }
    args = command_args.split(',')
    for arg in args:
        key, value = arg.split('=', 1)
        key = key.strip()
        value = value.strip()
        if key == 'golf_courses':
            params[key] = value
        elif key == 'days':
            params[key] = int(value)
        elif key in ['timemin', 'timemax']:
            params[key] = value.replace(' ','')
        elif key in ['pricemin', 'pricemax']:
            params[key] = int(value)
    return params


async def handle_hotdeals(update: Update, context: CallbackContext):
    logger.info("Received command /hotdeals")
    command_args = ' '.join(context.args)
    params = parse_command_params(command_args)
    
    message = f"**Starting search Hotdeals on GolfNow with parameters:**\n`{params}`"
    response = send_message_to_topic(bot_token, chat_id, topic_id, message)
    
    # Check if the message was successfully sent
    if response.get('ok'):
        logger.info(f"Message sent successfully: {message}")
    else:
        logger.error(f"Failed to send message: {response}")
        
    logger.info(message)

    os.environ['MOZ_HEADLESS'] = '1'  # Run Firefox in headless mode
    
    geckodriver_path = r'/usr/local/bin/geckodriver'
    
    options = FirefoxOptions()
    options.headless = True
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    service = FirefoxService(executable_path=geckodriver_path)
    browser = webdriver.Firefox(service=service, options=options)

    tee_df = golfnow(
        golf_courses=params['golf_courses'],
        days=params['days'],
        timemin=params['timemin'],
        timemax=params['timemax'],
        pricemin=params['pricemin'],
        pricemax=params['pricemax'],
        browser=browser
    )
    browser.quit()

    tee_18 = tee_df[tee_df['Hole'] == '18'].drop('Hole', axis=1)
    golfcourses = tee_18['Golf Course'].unique()

    delete_all_messages(bot_token, chat_id, topic_id)

    scan_time = time.strftime('%H:%M %a, %Y/%m/%d')
    message_scan_time = f'Hot deals in next {params['days']} days, were scanned at *{scan_time}*\n'
    send_message_to_topic(bot_token, chat_id, topic_id, message_scan_time)

    for golfcourse in golfcourses:
        df = tee_18[tee_18['Golf Course'] == golfcourse].drop('Golf Course', axis=1)
        message = f'*{golfcourse}*\n{df.to_string(header=False, index=False)}\n\n'
        message = message.replace('  ', ' ')
        send_message_to_topic(bot_token, chat_id, topic_id, message)

    logger.info("Completed golfnow search and sent messages")

async def handle_unknown_command(update: Update, context: CallbackContext):
    logger.info(f"Received unknown command: {update.message.text}")

    chat_id = update.message.chat_id
    topic_id = update.message.message_thread_id
    bot_token = context.bot.token
    message = "**Search command:**\n`/hotdeals [golf_courses=SJ, days=7, timemin=10:00AM, timemax=3:00PM, pricemin=8, pricemax=60]`"
    error_message = f"Unrecognized command. Please use the correct format: {message}"
    logger.error(f"Unrecognized command received: {update.message.text}")
    send_message_to_topic(bot_token, chat_id, topic_id, error_message)

def main():

    # Log that the bot is starting
    logger.info("Starting bot")
    
    message = "**Search command:**\n`/hotdeals [golf_courses=SJ, days=7, timemin=10:00AM, timemax=3:00PM, pricemin=8, pricemax=60]`"
    send_message_to_topic(bot_token, chat_id, topic_id, message)
    
    application = Application.builder().token(bot_token).build()

    # Handler for the /hotdeals command
    application.add_handler(CommandHandler('hotdeals', handle_hotdeals))

    # Handler for any unknown commands
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_unknown_command))

    # Log that the bot is polling
    logger.info("Bot is polling for updates")
    application.run_polling()

if __name__ == '__main__':
    main()