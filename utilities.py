import seiscomp3.Logging as logging
import bitly_api
import requests
import configFaceTweet as cfg

def short_url(url):
    key = cfg.bitly_key
    user = cfg.bitly_user
    try:
	bitlyAPI = bitly_api.Connection(user,key)
	short_url=bitlyAPI.shorten(url)
	return short_url['url']
    except Exception as e:
	print("Error in short_url: %s" %str(e))
    	return "---"

def get_closest_city(latitude,longitude):
    try:
        query = '%s/get_nearest_city?lat=%s&lon=%s&token=%s'%(cfg.geolocation_service_url,latitude,longitude,cfg.geolocation_service_token)
        result = requests.get(query)
        distance,city,province = result.text.strip('()').encode('utf-8',errors='ignore').split(',')
        
        return 'a %s de %s, %s' %(distance,city.strip(" '"),province.strip(" '"))
    except Exception as e:
        msg_error = "##Error in get_closest_city:%s" %str(e)
        print(msg_error)
        logging.error(msg_error)
        return '---'

#test get_closest_city
#print(get_closest_city(-10.47,-75.26))


'''
#Code to call the function
url=short_url("http://eventos.igepn.edu.ec/eqevents/event/igepn2018jgsc/overview.html")
print(url)
'''

def get_survey_url(local_time,event_id):
    
    date_event = local_time.strftime("%Y-%m-%d")
    time_event = local_time.strftime("%H:%M:%S")
    if cfg.survey_type == "arcgis":
        return short_url(cfg.arcgis_survey_url %(event_id,date_event,time_event))
    else:
        return short_url(cfg.google_survey_url %(event_id, date_event, time_event))

'''
#Code to call the function
from datetime import datetime

dt='2018-05-08T01:49:53.767704Z' 
dt=datetime.strptime(dt[:19], "%Y-%m-%dT%H:%M:%S")
url=get_survey_url(dt,'igepn2018jgsf')
print(url)
'''




