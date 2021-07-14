HOME	    =	"/home/seiscomp/"
plugins_path  =   "/%s/plugins_python/" %HOME

fb_dbname	= "%s/plugin_facebook/post.db" %(plugins_path)
fb_dbtable	= "postFacebook"
tw_dbname      =   "%s/twitter/post.db" %(plugins_path)
tw_dbtable     =   "postsTwitter"

tw_token_file  =   "/%s/twitter/twitter_account.json" %plugins_path
fb_token_file  =   "/%s/plugin_facebook/facebook_account.json" %plugins_path
tw_log_file    =   "%s/twitter/twitter.log" %(plugins_path)
fb_log_file    =   "%s/plugin_facebook/facebook.log"%(plugins_path)
 
local_zone  = 'America/Guayaquil'
LIMIT_HOURS = 20
DATE_FORMAT_EQ = '%Y/%m/%d %H:%M:%S'
face_fan_page='WACEROTEST'
twitter_page = 'AWACERO'
