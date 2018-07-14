#!/usr/bin/python
# -*- coding: UTF-8 -*-

import requests
import Queue
import json
import time
import threading
import MySQLdb
import sys, getopt
import os
import matplotlib
matplotlib.use('Agg')
import pylab as pl
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
from time import ctime,sleep

repeat=50
proxy=None

def statistic(title,queue,file):
    dict={}
    sum=0.0
    count=0
    max=0.0
    min=100.0
    data=[]
    if queue.empty():
        return

    print >>file,"------------------------------------------------------------------------------------"
    print >>file,title+":",queue.qsize()

    while not queue.empty():
        total_seconds=round(queue.get(),2)
        print total_seconds
        data.append(total_seconds)
        if dict.has_key(total_seconds):
            dict[total_seconds]=dict[total_seconds]+1
        else:
            dict[total_seconds]=1

        if total_seconds>max:
            max=total_seconds

        if total_seconds<min:
            min=total_seconds

        sum+=total_seconds
        count=count+1

    print >>file,str("max:%s" %max),str("min:%s" %min),
    if count >0 :
        print >>file, str("average:%s" %(sum/count)).ljust(13)[:13]

    items=dict.items()
    items.sort()
    # print >>file, items
    print >>file
    # x=[]
    # y=[]
    leftBound=min
    rightBound=min+0.5
    interval_count=0
    detail=""
    print >>file,"[",leftBound,",",rightBound,"):",
    for item in items:
        total_seconds=item[0]
        count=item[1]
        while total_seconds>=rightBound:
            leftBound=rightBound
            rightBound=rightBound+0.5
            if total_seconds<rightBound:
                if len(detail)>0:
                    detail=detail[0:len(detail)-1]
                print >>file,interval_count
                print >>file,detail
                print >>file
                print >>file,"[",leftBound,",",rightBound,"):",
                interval_count=0
                detail=""


        # print >>file,"(",total_seconds,",",count,"),",
        detail=detail+"("+str(total_seconds)+","+str(count)+"),"
        interval_count=interval_count+count

    if len(detail)>0:
        detail=detail[0:len(detail)-1]
        print >>file,interval_count
        print >>file,detail

    print >>file
    print >>file


    print title
    plt.hist(data, bins = (max-min)/0.01, color = 'steelblue', edgecolor = 'k', label = 'title')
    plt.title(title)
    plt.xlabel('Response time (s)')
    plt.ylabel('Count')
    plt.show()
    plt.savefig(title+".png")

def request_get(url):
    try:
        # r = requests.get(url, timeout=timeout)
        r = requests.get(url)
        json=r.json()
        code=json['meta']['code']
        total_seconds=r.elapsed.total_seconds()
        return (None,code,total_seconds)
    except Exception,e:
        print e
        return (e,None,None)

def request_post(url,payload):
    try:
        # r = requests.post(url, json=payload, timeout=timeout)
        r = requests.post(url, json=payload)
        json=r.json()
        code=json['meta']['code']
        total_seconds=r.elapsed.total_seconds()
        return (None,code,total_seconds)
    except Exception,e:
        print e
        return (e,None,None)

def request_get_proxy(url,timeout):
    try:
        cmd="curl -w 'time_total: %{time_total}\n' '"+url+"' -H 'Content-Type:application/json' -H 'Authorization:Gridx hEwCQGumUL+vulFJKaiuUNzwr2v0ajrt' --proxy "+proxy
        res=os.popen(cmd).read()
        index=res.find('time_total')
        code=json.loads(res[0:index])['meta']['code']
        total_seconds=float(res[index+12:].replace("\n",""))
        return (None,code,total_seconds)
    except Exception,e:
        print e
        return (e,None,None)

def request_post_proxy(url,contract_id,timeout):
    try:
        cmd="curl -w 'time_total: %{time_total}\n' '"+url+"' -X POST -H 'Content-Type:application/json' -H 'Authorization: Gridx hEwCQGumUL+vulFJKaiuUNzwr2v0ajrt' -d '{\"contractIDs\": [\""+contract_id+"\"]}' --proxy "+proxy
        res=os.popen(cmd).read()
        index=res.find('time_total')
        code=json.loads(res[0:index])['meta']['code']
        total_seconds=float(res[index+12:].replace("\n",""))
        return (None,code,total_seconds)
    except Exception,e:
        print e
        return (e,None,None)

def processResponse(res,timeout,successQueue,timeoutQueue,failQueue,contract_id):
    e=res[0]
    code=res[1]
    total_seconds=res[2]
    if e==None:
        print "response:",total_seconds
        if code == 200:
            if total_seconds>timeout:
                timeoutQueue.put(total_seconds)
            else:
                successQueue.put(total_seconds)
        else:
            print "Code",code,":",contract_id
            failQueue.put("code "+str(code)+":"+contract_id)
    else:
        print e
        print "exception",contract_id
        failQueue.put("exception:"+contract_id)


def testGet(url,timeout,successQueue,timeoutQueue,failQueue,queueForId):
    for loop in range(repeat):
        contract_id=queueForId.get()
        if proxy==None:
            res=request_get(url+contract_id)
        else:
            res=request_get_proxy(url+contract_id,timeout)
        processResponse(res,timeout,successQueue,timeoutQueue,failQueue,contract_id)

def testPost(url,timeout,successQueue,timeoutQueue,failQueue,queueForId):
    for loop in range(repeat):
        contract_id=queueForId.get()
        payload = {'SAlist': contract_id}
        if proxy==None:
            res=request_post(url,payload)
        else:
            res=request_post_proxy(url,contract_id,timeout)

        processResponse(res,timeout,successQueue,timeoutQueue,failQueue,contract_id)



if __name__=="__main__":
    opts, args = getopt.getopt(sys.argv[1:], "c:g:p:t:x:")

    for op, value in opts:
        if op == "-c":
            concurrentNum = int(value)
        elif op == "-g":
            url_get = value
        elif op == "-p":
            url_post = value
        elif op == "-t":
            timeout = int(value)
        elif op == "-x":
            proxy = value
        else :
            print "unmatched parameters"
            sys.exit()

    tmsp = time.strftime("%Y%m%d%H%M", time.localtime())
    result = open("result_"+str(concurrentNum)+"_"+tmsp+".txt",'w+')

    contract_id_num=concurrentNum*repeat*2

    print >> result,"Concurrent threads:",str(concurrentNum)
    print >> result,"Url of get:",url_get
    print >> result,"Url of post:",url_post
    if not proxy==None:
        print >> result,"Proxy:",proxy
        print proxy
    print >> result

    print >> result,"begin:",time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print >> result

    db = MySQLdb.connect("10.100.2.143","long","y91lkeKY","aps_cus")
    cursor = db.cursor()
    cursor.execute("select distinct contract_id from unifiedbillimpactapi limit "+str(contract_id_num))
    results = cursor.fetchall()

    queueForId = Queue.Queue(contract_id_num)
    for row in results:
        contract_id = row[0]
        queueForId.put(contract_id)

    queueForGet = Queue.Queue(concurrentNum*100)
    timeoutQueueForGet = Queue.Queue(concurrentNum*100)
    failQueueForGet = Queue.Queue(concurrentNum*100)
    queueForPost = Queue.Queue(concurrentNum*100)
    timeoutQueueForPost = Queue.Queue(concurrentNum*100)
    failQueueForPost = Queue.Queue(concurrentNum*100)
    threads = []
    for i in range(concurrentNum):
        t1=threading.Thread(target=testGet,args=(url_get,timeout,queueForGet,timeoutQueueForGet,failQueueForGet,queueForId,))
        t2=threading.Thread(target=testPost,args=(url_post,timeout,queueForPost,timeoutQueueForPost,failQueueForPost,queueForId,))
        t1.setDaemon(True)
        t2.setDaemon(True)
        t1.start()
        t2.start()
        threads.append(t1)
        threads.append(t2)

    for t in threads:
        t.join()

    statistic('Get Success',queueForGet,result)
    statistic('Get timeout',timeoutQueueForGet,result)
    statistic('Post success',queueForPost,result)
    statistic('Post timeout',timeoutQueueForPost,result)

    if not failQueueForGet.empty():
        print >>result,"------------------------------------------------------------------------------------"
        print >>result,"Get fail: ",failQueueForGet.qsize()

    count=0
    while not failQueueForGet.empty():
        print >>result,failQueueForGet.get(),
        count=count+1
        if count%20 == 0:
            print>>result

    print >>result

    if not failQueueForPost.empty():
        print >>result,"------------------------------------------------------------------------------------"
        print >>result,"Post fail: ",failQueueForPost.qsize()

    count=0
    while not failQueueForPost.empty():
        print >>result,failQueueForPost.get(),
        count=count+1
        if count%20 == 0:
            print>>result

    print >>result
    print >>result

    print >> result,"end:",time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    result.close()
