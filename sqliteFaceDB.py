'''
Created on May 26, 2016

@author: wacero
'''


import sqlite3
import os
from eqelib import configFaceTweet
import logging

#logging.basicConfig(filename=os.path.join(execDir, "faceplugin.log"), level=logging.DEBUG)


def connectDatabase():
    dbDir = os.path.dirname(configFaceTweet.fb_dbname)
    if not os.path.exists(dbDir):
        logging.debug("Creating DB directory")
        os.makedirs(dbDir)
    logging.debug("connecting to BD")
    con = sqlite3.connect(configFaceTweet.fb_dbname)
    con.text_factory = bytes
    logging.debug("connection to DB established")
    return con

def closeDatabase(con):
    con.commit()
    con.close()
    logging.debug("connection to DB closed")

def initDatabase():
    logging.info("creating and starting BD")
    try:
        if os.path.isfile(configFaceTweet.fb_dbname):
            return True
        con = connectDatabase()
        cur = con.cursor()
        sql = """CREATE TABLE %s (
        eventID TEXT PRIMARY KEY, faceID INTEGER NULL)""" % configFaceTweet.fb_dbtable
        logging.debug("Creating table %s" % configFaceTweet.fb_dbtable)
        cur.execute(sql)
        closeDatabase(con)
        logging.info("Table created")
        return True
    except sqlite3.Error, e:
        logging.info("Failed to create DB/table: %s" % str(e))
        return False

def savePost(postDict):
    postDict["table"] = configFaceTweet.fb_dbtable
    con = connectDatabase()
    cur = con.cursor()
    sql = """INSERT INTO %s (eventID, faceID ) 
        VALUES (:eventID,  :faceID)""" % configFaceTweet.fb_dbtable

    try:
        cur.execute(sql, postDict)
        logging.debug("Event '%s' added" % postDict['eventID'])
        closeDatabase(con)
        return 0

    except sqlite3.Error, e:
        logging.debug("Failed to add event %s : %s" % (postDict['eventID'], str(e)))
        return -1



def updatePost(postDict, column, value):
    postDict["table"] = configFaceTweet.fb_dbtable
    con = connectDatabase()
    cur = con.cursor()
    sql = """UPDATE %s SET %s = %s WHERE eventID= '%s'
    """ % (configFaceTweet.fb_dbtable, column, value, postDict['eventID'])
    try:
        logging.info("SQL: %s" % sql)
        cur.execute(sql, postDict)
        logging.info("Event %s inserting")
        closeDatabase(con)
        return 0
    except sqlite3.Error, e:
        logging.error("Failed to insert value: %s. Error:  %s" % (value, str(e)))
        return -1

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def getPost(select="*", where=None):
    con = connectDatabase()
    con.row_factory = dict_factory
    con.text_factory = str
    cur = con.cursor()
    sql = "SELECT %s FROM %s " % (select, configFaceTweet.fb_dbtable)
    if where:
        sql += "WHERE %s " % where
    cur.execute(sql)
    events = cur.fetchall()
    closeDatabase(con)
    return events


def deletePost(evID):
    con= connectDatabase()
    cur=con.cursor()
    sql="DELETE FROM %s WHERE eventID='%s'" %(configFaceTweet.fb_dbtable,evID)
    try:
        cur.execute(sql)
        con.commit()
        return True
    except sqlite3.Error, e:
        return str(e)
    


