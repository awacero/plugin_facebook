# -*- coding: utf-8 -*-

import sys,os
HOME=os.getenv("HOME")
sys.path.append("%s/plugins_python/plugin_facebook/" %HOME)

from datetime import datetime, timedelta
import seiscomp3.Logging as logging
import eqelib.plugin as plugin
import eqelib.settings as settings
from eqelib import configFaceTweet as cfg
from eqelib import utilities 
from eqelib import distancia

import facebook_plugin_sqlite_connection as sqliteFaceDB
import facebook 
import json
import requests
from StringIO import StringIO

import subprocess
                    
class Plugin(plugin.PluginBase):
    VERSION="0.2"
    
    def __init__(self, app,generator,env,db,cursor):
        
        logging.info("Calling init()")
        self.plugins_path = cfg.plugins_path
        self.fb_token = cfg.fb_token_file
        self.fb_acc = cfg.face_fan_page
        self.hour_limit = cfg.LIMIT_HOURS
        self.log_file = cfg.fb_log_file
        self.geo_url = cfg.geolocation_service_url
        self.geo_token = cfg.geolocation_service_token
        
    def processEvent(self,ctx,path):
        """
        Process the event  
        """
        logging.info("Start post in Facebook")
        
        """
        Create DB for evid, postid 
        """
        create_postDB = sqliteFaceDB.initDatabase()
        if create_postDB == False:
            logging.info("Error while creating DB: %s" % (cfg.fb_token_file))
            return False           
        
        """
        Check token file for FB and Bitly
        """
        token=self.read_config_file(self.fb_token)
        if token==False:
            logging.info("Error while reading token file: %s" % (cfg.fb_token_file))
            return False
        else:            
            self.token_bitly=token['BITLY']
            self.token_facebook=token[self.fb_acc]
            #logging.info("Reading token ok: %s" %(self.token_facebook))
            logging.info("Reading token ok")
        """
        Create event dictionary from ctx
        """      
        event_dict=self.ctx2dict(ctx,path)
        logging.info("##Created dict: %s" %event_dict)

        """
        Check event antiquity 
        """
        if self.check_antiquity(event_dict['date']) == False:
            logging.info("Event %s too old to publish" %event_dict['evID'])
	    return True
        
        """
        Check in postDB if the event has been published already
        """
        logging.info("###CHECK TO DB") 
        post_row=self.check_post_existence(event_dict['evID'],event_dict['modo'])
        
        if len(post_row)==0:
            logging.info("Event not found. Continue to publish")

        elif len(post_row)==1:
            logging.info("Event already published. Exit")
            return True
        
    
        """     Post to Facebook        """
        try:
            post = self.create_post_message(event_dict)        
        except Exception as e:
            logging.info("Error while creating post for %s. Error was: %s" %(event_dict['evID'], str(e)))
            return False

        post_id = self.post_event(post,event_dict)
        if post_id==False:
            logging.info("Error posting to Facebook")
            return False
        else:
            ##INSERTAR EN BD
            
            post_DB = {'eventID':'%s' %event_dict['evID'], 'faceID':'%s' %str(post_id['post_id']),'modo':'%s' %event_dict['modo'] }
            logging.info("Insert post info into DB: %s" %post_DB ) 
            if sqliteFaceDB.savePost(post_DB) == 0:
                logging.info("Post inserted in DB")
            else:
                logging.info("Failed to insert post in DB. Something bad will happen!")
            
            return True
    
    def post_event(self,post,event_dict):
        """     Post to Facebook        """
        try:
        
            api_facebook = facebook.GraphAPI(self.token_facebook['token'])
            post_id = api_facebook.put_photo(image=open(post[1]), message=post[0])
            return post_id

        except Exception as e:
            logging.info("Error while uploading post for %s. Error was: %s" %(event_dict['evID'], str(e)))
            return False
    




    def resend_post(self,msg_post, post_id):
        face_url = 'https://graph.facebook.com/'
        headers = {'Authorization':'OAuth %s' % self.token_facebook['token']}
        payload = {'batch':'[{"method":"POST","body":"message=%s","name":"editPost","omit_response_on_success":false,"relative_url":"%s"}]' % (msg_post, post_id)}
        buffer_temporal = StringIO("")
        try:
            logging.debug("Trying resen_post():"+ str(requests.post(face_url, headers=headers, data=payload, files=buffer_temporal)))
            return True
        except Exception as e:
            logging.debug("Error in resend_post(): %s" % str(e))
            return False  

                            
    def check_facebook_post(self,fID):
        try:
            api_facebook = facebook.GraphAPI(self.token_facebook['token'])
            post_object = api_facebook.get_object('%s' % fID)
            if post_object:
                return True
            else:
                return False
        except Exception as e:
            logging.debug("Error in check_facebook_post: %s" % str(e))
            return False
           
            

    def create_post_message(self,evD):
        
        query = '%s/get_country?lat=%s&lon=%s&token=%s'%(self.geo_url,evD['lati'],evD['long'],self.geo_token)
	print(query)
        result = requests.get(query)
        country = result.text
        post_text =  """#SISMO ID: %s %s %s TL Magnitud:%s Prof %s km, %s Latitud:%s Longitud:%s Sintió este sismo? Cuéntenos en dónde (débil,\
fuerte,muy fuerte) Repórtelo! en %s""" % (evD['evID'], evD['modo'], evD['date'], evD['magV'], evD['dept'], evD['dist'], evD['lati'], evD['long'], evD['url'])

        if country == 'Colombia':
            post_text += "\nFuente oficial COLOMBIA: \nhttps://www.sgc.gov.co/sismos \nhttps://twitter.com/sgcol"
        elif country == 'Peru':
            post_text += "\nFuente oficial PERU: \nhttps://www.gob.pe/igp \nhttps://twitter.com/Sismos_Peru_IGP"
        
        return post_text, evD['path']

    
    def upload_post(self,evD):
        
        post = self.create_post_message(evD)
        try:
            logging.info("Event received: %s" %evD) 
            api_facebook = facebook.GraphAPI(self.token_facebook['token'])
            post_id = api_facebook.put_photo(image=open(post[1]), message=post[0])
            if post_id:
                logging.info("Ok upload_post(). ID: %s" %str(post_id['post_id']))
                # insertar post info en BD
                post_DB = {'eventID':'%s' %evD['evID'], 'faceID':'%s' %str(post_id['post_id'])}
                if sqliteFaceDB.savePost(post_DB) == 0:
                    logging.info("Post inserted in DB")
                    logging.info("Llamar a hide_facebook_messages")
                    script_sh="/%s/ml_text/run_hide_facebook_messages.sh" %self.plugins_path
                    event_id = evD['evID']
                    post_id = str(post_id['post_id'])
                    FNULL=open(os.devnull,'w')
                    p=subprocess.Popen(["%s" %script_sh,"%s"%event_id, "%s" %post_id],stdout=FNULL,stderr=subprocess.STDOUT)
                else:
                    logging.info("Failed to insert post in DB. Something bad will happen!")
                return True
        except Exception as e:
            logging.info("Error in upload_post(%s). Error: %s" %(evD['evID'], str(e)))
            return False      
        
        
        
    def ctx2dict(self,ctx,path):
        
        """
        receive a ctx object and return a dictionary of the event
        """
        d={}
        o=ctx['origin']
        d['evID'] = ctx['ID']
        d['modo'] = self.status(str(o.evaluationMode))
        dtime = o.time.value
        dtime = datetime.strptime(dtime[:19],"%Y-%m-%dT%H:%M:%S") -timedelta(hours=5)
        d['date'] = dtime
        d['magV'] = "%.2f" %o.magnitude.magnitude.value
        d['dept'] = "%.2f" %o.depth.value
        d['dist'] = utilities.get_closest_city(o.latitude.value,o.longitude.value)
        d['lati']="%.2f" %o.latitude.value
        d['long']="%.2f" %o.longitude.value
        d['url']= str(utilities.get_survey_url(d['date'],d['evID']))       
        d['path']="%s/%s-map.png" %(path,d['evID'])
        return d


    def read_config_file(self,jsonFile):
        """
        read JSON files
        """
        try:
            with open(jsonFile) as json_data_files:
                return json.load(json_data_files)
        except Exception as e:
            logging.info("Error in read_config_file(): %s" %str(e))
            return False
        
    def check_antiquity(self, dt):
        """
        Check the age of a event
        Parameters:
            dt - datetime object
        """
        date_check = datetime.now() - timedelta(hours=self.hour_limit)
        
        if date_check < dt:
            return True
        else:
            return False

    def status(self,stat):
        if stat == 'automatic':
            stat = 'Preliminar'
        elif stat == 'manual':
            stat = 'Revisado'
        else:
            stat = '.'
        return stat


    def check_post_existence(self,evID,modo):
        select = "*"
        where = "eventID='%s' AND modo='%s' " % (evID,modo)
        return sqliteFaceDB.getPost(select, where)

    
    def delete_facebook_post(self,evID):
        
        import logging
        logging.basicConfig(filename=self.log_file,format='%(asctime)s %(levelname)s %(message)s',level=logging.INFO)

        """
        Read token file and set token global variables
        """
        token = self.read_config_file(self.fb_token)
        if token == False:
            logging.info('Error while reading token file: %s' % (cfg.fb_token_file))
            return False 
        else:
            self.token_facebook = token[self.fb_acc]
            
        post=self.check_post_existence(evID,modo)
        if post:
            logging.info("Event %s found in FB post.db. Delete" %(evID))
            try:
                logging.info("##Connect to FB to delete event %s|%s" %(evID,str(post[0]['faceID'])))
                api_facebook=facebook.GraphAPI(self.token_facebook['token'])
                res=api_facebook.delete_object('%s' %(post[0]['faceID']))
                logging.info("Event %s deleted from FB fanpage. Response is: %s" %(evID,str(res)))
                
                res=sqliteFaceDB.deletePost(evID)
        
                if res== True:
                    logging.info("Deleted from post.db")
                    return True
                else:
                    logging.info("Error deleting: %s" %res)
                    return False
                
            except Exception as e:
                logging.info("Error while deleting event %s : %s " %(evID,str(e)))
                return False
        else:
            logging.info("Event %s not found in FB post.db. Nothing to do" %(evID))
            return False


