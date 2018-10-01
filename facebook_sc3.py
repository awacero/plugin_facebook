#import sys
#sys.path.insert(0,'%s' %('/home/seiscomp/git/pluginFacebook'))

from datetime import datetime, timedelta
from StringIO import StringIO
import json
import os
import logging 
import pytz
import sqliteDbLib
import facebook
import requests


# Define a path for own libraries and log file
import sqliteFaceDB
import configFaceTweet

logging.basicConfig(filename=os.path.join(configFaceTweet.log_dir, "face_plugin.log"), level=logging.DEBUG)
token_file= configFaceTweet.token_file
local_time_zone = pytz.timezone(configFaceTweet.local_zone)
LIMIT_HOURS=configFaceTweet.LIMIT_HOURS
DATE_FORMAT_EQ=configFaceTweet.DATE_FORMAT_EQ




def get_event_fromDB(eventID):
    try:
        eventos = sqliteDbLib.outputDB(where="eventID='%s'" % (eventID))
        if eventos:
            return eventos[0]
        else:
            return -1
    except Exception as e:
        logging.debug("Error get_event_fromDB(): %s. Error: %s" % (eventID, str(e)))
        return -1
        

def convert_date_UTC2local(dateUTCstring):
    dateUTC = datetime.strptime(dateUTCstring, DATE_FORMAT_EQ)
    dateEC = dateUTC.replace(tzinfo=pytz.utc).astimezone(local_time_zone)
    return dateEC.strftime(DATE_FORMAT_EQ)

def check_antiquity(eventDateString):
    date_event_EC = convert_date_UTC2local(eventDateString)
    date_check = datetime.now() - timedelta(hours=LIMIT_HOURS)
    if date_check < datetime.strptime(date_event_EC, DATE_FORMAT_EQ):
        return 0
    else:
        return -1
        
  
def read_config_file(json_file):
    try:
        with open(json_file) as json_data_files:
            return json.load(json_data_files)
    except Exception as e:
        logging.debug("Error readConfigFile(): %s" % str(e))
        return -1

def check_post_existence(eventID):
    select = "*"
    where = "eventID='%s'" % eventID
    return sqliteFaceDB.getPost(select, where)


def status(stat):
    if stat == 'automatic':
        stat = 'Preliminar'
    elif stat == 'manual':
        stat == 'Revisado'
    else:
        stat = ' '
    return stat
   

def create_post_message(evD):
    post_text = "#SISMO ID: %s %s %s TL Magnitud:%s Prof %.2f km, %s Latitud:%s Longitud:%s" % (evD['eventID'], status(evD['status']), evD['LocalTime'], evD['magVal'], evD['depth'], evD['localizacion'], evD['latitude'], evD['longitude'])
    image_path = '%s/%s/%s-gmapa.png' % (configFaceTweet.eqevents_path, evD['eventID'], evD['eventID'])
    return post_text, image_path

def upload_post(evD):
    post = create_post_message(evD)
    try:
        api_facebook = facebook.GraphAPI(token_facebook['token'])
        post_id = api_facebook.put_photo(image=open(post[1]), message=post[0])
        if post_id:
            logging.debug("Ok upload_post(). ID: %s" % post_id['post_id'])
            # insertar post info en BD
            post_DB = {'eventID':'%s' % evD['eventID'], 'faceID':'%s' % post_id['post_id']}
            if sqliteFaceDB.savePost(post_DB) == 0:
                logging.debug("Post inserted in DB")
            else:
                logging.debug("Failed to insert post in DB. Something bad will happen!")
            return 0
    except Exception as e:
        logging.debug("Error in upload_post(%s). Error: %s" % (evD['eventID'], str(e)))
        return -1


def resend_post(msg_post, post_id):
    face_url = 'https://graph.facebook.com/'
    headers = {'Authorization':'OAuth %s' % token_facebook['token']}
    payload = {'batch':'[{"method":"POST","body":"message=%s","name":"editPost","omit_response_on_success":false,"relative_url":"%s"}]' % (msg_post, post_id)}
    buffer_temporal = StringIO("")
    try:
        logging.debug("Trying resen_post():"+ str(requests.post(face_url, headers=headers, data=payload, files=buffer_temporal)))
        return 0
    except Exception as e:
        logging.debug("Error in resend_post(): %s" % str(e))
        return -1     


def check_facebook_post(fID):
    try:
        api_facebook = facebook.GraphAPI(token_facebook['token'])
        post_object = api_facebook.get_object('%s' % fID)
        if post_object:
            return 0
        else:
            return -1
    except Exception as e:
        logging.debug("Error in check_facebook_post: %s" % str(e))
        return -1

def face_plugin(evID):
    '''
    Read token file and set token global variables
    '''
    token = read_config_file(token_file)
    if token == -1:
        logging.debug('Error while reading token file: %s' % (token_file))
        exit (-1)
    else:
        
        global token_facebook
        token_facebook = token['DGTEST']

    
    '''
    Check if event exist in events.db and set
    '''
    eventDict = get_event_fromDB(evID)
    if eventDict == -1:
        logging.debug("Error getting event dictionary")
        exit(-1)
    
    '''
    Check antiquity of event according to LIMIT_HOURS
    '''
    antiquity = check_antiquity(eventDict['timestampSec'])
    if antiquity == -1:
        logging.debug("Event too old to publish")
        exit (-1)
    
    '''
    Create postDB according to configFaceTweet.py
    '''
    create_postDB = sqliteFaceDB.initDatabase()
    if create_postDB == -1:
        logging.debug("Could not create post DB. Exit")
        exit(-1)
    
    '''
    Check in postDB if the event has been published already 
    '''
    post = check_post_existence(evID)
    if not post:
        logging.info("No event: %s in postdatabase. Calling upload_event()" % (evID))
        if upload_post(eventDict)==0:
            logging.info("Event %s uploaded. Exit" %(evID))
        else:
            logging.info("Failed while upload event: %s" %(evID))
    
    elif check_facebook_post(post[0]['faceID']) == -1:
        logging.info("No event: %s found in Facebook. Upload anyway" % (evID))
        if upload_post(eventDict)==0:
            logging.info("Event %s uploaded. Exit" %(evID))
        else:
            logging.info("Failed while upload event: %s" %(evID))
    else:
        logging.info("Event: %s exist. Update" % (evID))
        updated_post = create_post_message(eventDict)
        if resend_post(updated_post[0], post[0]['faceID'])==0:
            logging.info("resend_post() OK. Exit")
        else:
            logging.info("Failed resend_post()")
        
