import sys,os
HOME=os.getenv("HOME")
sys.path.append("%s/plugins_python/facebook/" %HOME)

from datetime import datetime, timedelta
import seiscomp3.Logging as logging
import eqelib.plugin as plugin
import eqelib.settings as settings
from eqelib import configFaceTweet as cfg
from eqelib import distancia

import sqliteFaceDB
import facebook 
import json
import requests
from StringIO import StringIO


class Plugin(plugin.PluginBase):
    VERSION="0.2"
    
    def __init__(self, app,generator,env,db,cursor):
        
        logging.info("Calling init()")
        self.fb_token=cfg.fb_token_file
        self.fb_acc=cfg.face_fan_page
        self.hour_limit=cfg.LIMIT_HOURS
        self.log_file=cfg.fb_log_file

        
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
        Check token file for FB 
        """
        token=self.read_config_file(self.fb_token)
        if token==False:
            logging.info("Error while reading token file: %s" % (cfg.fb_token_file))
            return False
        else:            

            self.token_facebook=token[self.fb_acc]
            logging.info("Reading token ok: %s" %(self.token_facebook))
        
        """
        Create event dictionary from ctx
        """      
        d=self.ctx2dict(ctx,path)
        logging.info("##Created dict: %s" %d)

        """
        Check event antiquity 
        """
        if self.check_antiquity(d['date']) == False:
            logging.info("Event %s too old to publish" %d['evID'])
	    return True
        
        """
        Check in postDB if the event has been published already
        """
        post = self.check_post_existence(d['evID'])
        if not post:
            logging.info("No event: %s in postdatabase. Calling upload_event()" % (d['evID']))
            if self.upload_post(d)==True:
                logging.info("Event %s uploaded. Exit" %(d['evID']))
                return True
            else:
                logging.info("Failed while upload event: %s" %(d['evID']))
                return False
        
        elif self.check_facebook_post(post[0]['faceID']) == False:
            logging.info("No event: %s found in Facebook. Upload anyway" % (d['evID']))
            if self.upload_post(d)==True:
                logging.info("Event %s uploaded. Exit" %(d['evID']))
                return True
            else:
                logging.info("Failed while upload event: %s" %(d['evID']))
                return False

        else:
            logging.info("Event: %s exist. Update" % (d['evID']))
            updated_post = self.create_post_message(d)
            
            if self.resend_post(updated_post[0], post[0]['faceID'])==True:
                logging.info("resend_post() OK. Exit")
                return True
            else:
                logging.info("Failed while re-sending post: %s" %(d['evID']))
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
        logging.info("#SISMO ID: %s %s %s TL Magnitud:%s Prof %s km, %s Latitud:%s Longitud:%s Sintio este sismo? Reportelo! en %s\
        " % (evD['evID'], evD['modo'], evD['date'], evD['magV'], evD['dept'], evD['dist'], evD['lati'], evD['long'], evD['url']))
        post_text = "#SISMO ID: %s %s %s TL Magnitud:%s Prof %s km, %s Latitud:%s Longitud:%s Sintio este sismo? Reportelo! en %s\
        " % (evD['evID'], evD['modo'], evD['date'], evD['magV'], evD['dept'], evD['dist'], evD['lati'], evD['long'], evD['url'])
        
        return post_text, evD['path']

    
    def upload_post(self,evD):
        
        post = self.create_post_message(evD)
        try:
            
            api_facebook = facebook.GraphAPI(self.token_facebook['token'])
            post_id = api_facebook.put_photo(image=open(post[1]), message=post[0])
            if post_id:
                logging.info("Ok upload_post(). ID: %s" %str(post_id['post_id']))
                # insertar post info en BD
                post_DB = {'eventID':'%s' %evD['evID'], 'faceID':'%s' %str(post_id['post_id'])}
                if sqliteFaceDB.savePost(post_DB) == 0:
                    logging.info("Post inserted in DB")
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
        d['evID']=ctx['ID']
        d['modo']=str(o.evaluationMode)
        dtime=o.time.value
        dtime=datetime.strptime(dtime[:19],"%Y-%m-%dT%H:%M:%S") -timedelta(hours=5)
        d['date']=dtime
        d['magV']="%.2f" %o.magnitude.magnitude.value
        d['dept']="%.2f" %o.depth.value
        d['dist']=distancia.closest_distance(o.latitude.value,o.longitude.value)
        d['lati']="%.2f" %o.latitude.value
        d['long']="%.2f" %o.longitude.value
        d['url']="URL OF WEB PAGE"       
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

    def check_post_existence(self,evID):
        select = "*"
        where = "eventID='%s'" % evID
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
            
        post=self.check_post_existence(evID)
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
