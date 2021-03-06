#!/user/bin/python
# -*- coding: utf-8 -*-
import requests
import re
import sys
import psycopg2
import psycopg2.extras
import dateutil.parser
import pguser
import numpy as np
import json
from bs4 import BeautifulSoup

checkusers = ['bgpat','goryudyuma','Makinami','murashin','not_seele','toga2048','ugwis','wanimaru47','tsunetoki','sn_93','scn_13k','fono09']

histogram_filename = "hist-atcoder.png"

url_atcoder_jp = "http://atcoder.jp"
contest_atcoder = "contest.atcoder.jp"
url_media = "https://upload.twitter.com/1.1/media/upload.json"
url_text = "https://api.twitter.com/1.1/statuses/update.json"

def regex(r,text):
    rec = re.compile(r)
    match = rec.search(text)
    if match is None:
        print("--regex doesn't matched folowing text--")
        print(text)
        return None
    return match.group(1)

def insert_user(userid,username):
    connector = psycopg2.connect(pguser.arg)
    uid = None
    cur = connector.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("""SELECT insert_user((%s),(%s))as uid;""",(userid,username))
        connector.commit()
        for row in cur:
            uid = row['uid']
    except Exception as e:
        print(e.message)
    cur.close()
    connector.close()
    return uid

def insert_language(name):
    connector = psycopg2.connect(pguser.arg)
    cur = connector.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("""SELECT insert_language((%s)) as lid""",(name,))
        connector.commit()
        for row in cur:
            lid = row['lid']
    except Exception as e:
        print(e.message)
    cur.close()
    connector.close()
    return lid

def fetch_pid(cid,problemid):
    connector = psycopg2.connect(pguser.arg)
    cur = connector.cursor(cursor_factory=psycopg2.extras.DictCursor)
    pid = None
    try:
        cur.execute("""SELECT * FROM problems WHERE cid=(%s) AND problemid=(%s)""",(cid,problemid))
        for row in cur:
            pid = row['pid']
    except Exception as e:
        print(e.message)
    cur.close()
    connector.close()
    return pid

def fetch_cid(contestid):
    connector = psycopg2.connect(pguser.arg)
    cur = connector.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cid = None
    try:
        cur.execute("""SELECT * FROM contests WHERE contestid=%s""",(contestid,))
        for row in cur:
            cid = row['cid']
    except Exception as e:
        print(e.message)
    cur.close()
    connector.close()
    return cid

def insert_solved(rid,userid,username,contestid,problemid,language,cputime,memory,codesize,datetime):
    uid = insert_user(userid,username)
    lid = insert_language(language)
    cid = fetch_cid(contestid)
    pid = fetch_pid(cid,problemid)
    connector = psycopg2.connect(pguser.arg)
    cur = connector.cursor(cursor_factory=psycopg2.extras.DictCursor)
    try:
        cur.execute("""INSERT INTO solved(rid,uid,cid,pid,lid,cputime,memory,codesize,datetime) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)""",(rid,uid,cid,pid,lid,cputime,memory,codesize,datetime))
        connector.commit()
    except Exception as e:
        #print(e.message)
        cur.close()
        connector.close()
        return None
    cur.close()
    connector.close()
    print("inserted:" + str(rid))
    return 1

def crawl_contest_solved_page(cid,page,type):
    url = "http://" + cid + "." + contest_atcoder + "/submissions/all/" + str(page) + "?status=AC"
    print(url)
    ret = []
    r = requests.get(url)
    soup = BeautifulSoup(r.text.encode(r.encoding),"html.parser")
    succ = soup.find_all("tr")
    if succ == []:
        return "Finish"
    for suc in succ:
        row = suc.find_all("td")
        if row == []:
            continue
        if insert_solved(
                regex("/submissions/(\d*)",row[9].a.get("href")),
                regex("/users/(\w*)",row[2].a.get("href")),
                row[2].a.string,
                cid,
                regex("/tasks/(\w*)",row[1].a.get("href")),
                row[3].string,
                regex("(\d*) ms",row[7].string),
                regex("(\d*) KB",row[8].string),
                regex("(\d*) Byte",row[5].string),
                dateutil.parser.parse(row[0].time.string)
            ) == None:
            if type != 'all':
                return "Failed"
    return 1

def crawl_contest_solved_pages(cid,type):
    i = 0
    while True:
        i+=1
        try:
            status = crawl_contest_solved_page(cid,i,type)
            print(status)
            if status == 'Finish':
                return
            if status == 'Failed' and type != 'all':
                return
        except Exception as e:
            print("exception pages")
            print(e.message)
            return

def fetch_ended_contest_list():
    connector = psycopg2.connect(pguser.arg)
    cur = connector.cursor(cursor_factory=psycopg2.extras.DictCursor)
    contest = []
    try:
        cur.execute("SELECT contestid,crawled FROM contests WHERE endtime <= now() GROUP BY cid ORDER BY endtime DESC;")
        connector.commit()
        for row in cur:
            contest.append({
                "contestid":row['contestid'],
                "crawled":row['crawled']
            })
    except Exception as e:
        print(e.message)
    return contest

if __name__ == "__main__":
    #crawl_contest_solved_page("abc001",378)
    #crawl_contest_solved_pages("abc001","all")
    contests = fetch_ended_contest_list()
    for contest in contests:
        if contest['crawled']:
            crawl_contest_solved_pages(contest['contestid'],"normal")
        else:
            crawl_contest_solved_pages(contest['contestid'],"all")

    exit(0)
