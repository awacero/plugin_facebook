##Example of configFaceTweet.py
##$SC3/lib/python/eqelib

HOME        =   "/home/seiscomp/"
createpath  =   "/%s/plugins_python/" %HOME

fb_dbname       ="%s/facebook/post.db" %(createpath)
fb_dbtable      ="postFacebook"
tw_dbname      =   "%s/twitter/post.db" %(createpath)
tw_dbtable     =   "postsTwitter"

tw_token_file  =   "/%s/plugins_python/twitter/twitter_account.json" %HOME
fb_token_file  =   "/%s/plugins_python/facebook/facebook_account.json" %HOME
tw_log_file    =   "%s/twitter/twitter.log" %(createpath)
fb_log_file    =   "%s/facebook/facebook.log"%(createpath)
 
local_zone  = 'America/Guayaquil'
LIMIT_HOURS = 20
DATE_FORMAT_EQ = '%Y/%m/%d %H:%M:%S'
face_fan_page= 'DGTEST'
twitter_page = 'AWACERO'
