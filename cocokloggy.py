from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
import json
import urllib.request, urllib.parse

import smtplib

import configparser
import os
import time
import ast

from apscheduler.schedulers.blocking import BlockingScheduler
import logging

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)

sched = BlockingScheduler()
client = Elasticsearch()

token_bot="XXXXXXX"

cP = configparser.ConfigParser()
configFilePath = os.path.join(os.path.dirname(__file__), 'rules.conf')
cP.read(configFilePath)

def email_notification(to,subject,body_email):
        TO = to
        SUBJECT = subject
        TEXT = body_email

        gmail_sender = 'email_to@gmail.com'
        gmail_passwd = 'passwd'

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_sender, gmail_passwd)

        BODY = '\r\n'.join(['To: %s' % TO,
                    'From: %s' % gmail_sender,
                    'Subject: %s' % SUBJECT,
                    '', TEXT])

        try:
            server.sendmail(gmail_sender, [TO], BODY)
            print ('email sent to '+TO)
        except:
            print ('error sending mail'+TO)
        server.quit()

def telegram_notification(command,token_bot,param):
        url="https://api.telegram.org/bot"+token_bot+"/"
        url +=command+"?"
        data = bytes( urllib.parse.urlencode( param ).encode() )
        handler = urllib.request.urlopen(url , data );

def search_es(rules_name,query):
        try:
                text_header = "Alert : " + rules_name + "\n"
                text_body = "";
                s = Search.from_dict(ast.literal_eval(query))
                s = s.using(client).index('*')
                response = s.execute()
                res_dict = response.to_dict()
                #res_d = str(res_dict['hits']['hits'])
                #res_e = res_d.replace('}','')
                #res_f = res_e.replace('{','')
                #res_g = res_f.replace('\\n','\n')
                #res_h = res_g.replace(',','\n')
                #res_i = limiter(res_h,1500)
                for aggdata in res_dict['aggregations']:
                        for haggdata in res_dict['aggregations'][aggdata]:
                                if(haggdata=="buckets"):
                                        for data_res in res_dict['aggregations'][aggdata][haggdata]:
                                                text_body += str(data_res['key'])+ " : " + str(data_res['doc_count']) + "\n"              
                if text_body!="":
                        return text_header+text_body
        except:
                logging.error('Error search Elasticsearch')
                return ""

def initiate_job(each_section,schedule,query):
        try:
                scheduler = ast.literal_eval(schedule)
                @sched.scheduled_job('interval',**scheduler)
                def timed_job():
                        time_run= time.asctime( time.localtime(time.time()) )
                        print('%s Running this job : %s is run every %s' % (time_run,each_section,schedule))
                        text_notification = search_es(each_section,query)
                        print("==========================================================")
                        print(text_notification)
                        print("==========================================================")
                        if text_notification!="":
                                data_param = {'chat_id' : 'XXXXXXX', 'text' : text_notification}
                                telegram_notification("sendMessage",token_bot,data_param)
                                email_notification("email_to@gmail.com","Alert : "+each_section,text_notification)
        except:
                logging.error('Error adding job')

for each_section in cP.sections():
        initiate_job(each_section,cP.get(each_section, 'schedule'),cP.get(each_section, 'query'))

try:
        sched.start()
except:
        logging.error('Cannot start scheduler')

