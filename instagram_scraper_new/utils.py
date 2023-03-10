import random
from datetime import datetime
import coloredlogs, logging
import json
import sqlite3
import os

from pymongo import MongoClient, TEXT, IndexModel, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, InvalidName, DuplicateKeyError

logger = logging.getLogger(__name__)
coloredlogs.install(fmt='[%(asctime)s] %(message)s')

class FileNotFound(Exception):
    ''' Raised when a file required for the program to operate is missing. '''


class NoDataLoaded(Exception):
    ''' Raised when the file is empty. '''

def get_proxy(proxy_list):
    '''
    (list) -> dict
    Given a proxy list <proxy_list>, a proxy is selected and returned.
    '''
    # Choose a random proxy
    proxy = random.choice(proxy_list)

    # Set up the proxy to be used
    proxies = {
        "http": "http://" + str(proxy),
        "https": "https://" + str(proxy)
    }

    # Return the proxy
    return proxies


def read_from_txt(filename):
    '''
    (None) -> list of str
    Loads up all sites from the sitelist.txt file in the root directory.
    Returns the sites as a list
    '''
    # Initialize variables
    raw_lines = []
    lines = []

    #Added by ME 
    path = "data/" + filename

    # Load data from the txt file
    try:
        f = open(path, "r")
        raw_lines = f.readlines()
        f.close()

    # Raise an error if the file couldn't be found
    except:
        log('e', "Couldn't locate <" + path + ">.")
        raise FileNotFound()

    # Parse the data
    for line in raw_lines:
        list = line.strip()
        if list != "":
            lines.append(list)

    if(len(lines) == 0):
        raise NoDataLoaded()

    # Return the data
    return lines
    
def get_config(filename):
    path = "data/" + filename
    try:
        with open(path, 'r') as f:
            config = json.load(f)
    except Exception as e:
        raise FileNotFound()
    
    return config

def log(tag, text):
	# Info tag
    if(tag == 'i'):
        logger.info("[INFO] " + text)
    # Error tag
    elif(tag == 'e'):
        logger.error("[ERROR] " + text)
    # Success tag
    elif(tag == 's'):
        logger.warning("[SUCESS] " + text)
    # Warning tag
    elif(tag == 'w'):
        logger.warning("[WARNING] " + text)
    # Fail tag
    elif(tag == 'f'):
        logger.critical("[FAIL] " + text)


def create_table(tablename, db_name):
    tablename = tablename.strip().lower().replace(".", "")

    db_dir = "./dbs/"
    if not os.path.exists(db_dir):
        os.makedirs(db_dir)
    conn = sqlite3.connect(db_dir + db_name + '.db')
    c = conn.cursor()
    create_tbl_query = """CREATE TABLE IF NOT EXISTS """ + "tbl_" + tablename + \
        """(link TEXT UNIQUE not null PRIMARY KEY, product TEXT)"""
    try:
        c.execute(create_tbl_query)
    except Exception as e:
        raise(e)

    conn.commit()
    conn.close()

def add_to_post_mongodb(collection, shortcode, username, type):
    post = {}
    post.update({"_id": shortcode})
    post.update({"username": username})
    post.update({"type": type})
    alert = None
    try:
        collection.insert_one(post)
        alert = "New"
    except DuplicateKeyError:
        pass
    except Exception as e:
        print_error_log(3, "Add to post {}".format(repr(e)))
    return alert

def update_post_data(collection, shortcode, post):
    try:
        collection.find_one_and_update( 
            {'_id': shortcode}, 
            {'$set': {
                'postURL' : post['post_link'],
                'caption': post['caption'],
                'isGallery': post['isGallery'], 
                'isVideo': post['isVideo'], 
                'post_time': post['post_time'], 
                'imgurl': post['image_link'], 
                "added_datetime" : post['added_datetime']
            }})
    except Exception as e:
        print_error_log(3, "Update Post: {}".format(repr(e)))

def add_to_post_db(link, table_name, db_name):
    # Initialize variables
    table_name = table_name.strip().lower().replace(".", "")

    alert = None

    # Create database
    conn = sqlite3.connect("./dbs/" + db_name + '.db')
    c = conn.cursor()

    # Add product to database if it's unique
    try:
        c.execute("""INSERT INTO tbl_""" + table_name +
                  """(link, product) VALUES (?, ?)""", (link, table_name))
        log('s', "Found new post from [{}]--[{}]".format(table_name, db_name))
        alert = "New"
    except:
        pass

    # Close database
    conn.commit()
    conn.close()

    # Return whether or not it's a new product
    return alert

def print_error_log(type, error_message):
    monitor_time = datetime.now().strftime('%m-%d-%Y %H:%M:%S')
    if type == 1:
        filename = "post_hashtag_error_logs.txt"
    elif type == 2:
        filename = "tagged_story_error_logs.txt"
    else:
        filename = "offspring_post_error.txt"
    dir = "./logs/"
    if not os.path.exists(dir):
        os.makedirs(dir)

    with open(dir + filename, 'a+') as f:
        f.write("[{}] \t {} \n".format(monitor_time, error_message))