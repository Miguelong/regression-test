#!/usr/bin/python
# -*- coding: UTF-8 -*-

import requests
import Queue
import json
import time
import threading
import MySQLdb
import sys, getopt
import pylab as pl
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
from time import ctime,sleep

repeat=10

def statistic(title,queue,file):
    dict={}
    sum=0.0
    count=0
    max=0.0
    min=10.0
    data=[]
    while not queue.empty():
        total_seconds=queue.get()
        key=round(total_seconds,2)
        data.append(key)
        if dict.has_key(key):
            dict[key]=dict[key]+1
        else:
            dict[key]=1

        if total_seconds>max:
            max=total_seconds

        if total_seconds<min:
            min=total_seconds

        sum+=total_seconds
        count=count+1

    print >>file, str("max:%s" %max).ljust(9)[:9],
    if count >0 :
        print >>file, str("average:%s" %(sum/count)).ljust(13)[:13]

    items=dict.items()
    items.sort()
    print >>file, items
    print >>file
    x=[]
    y=[]
    for item in items:
        x.append(item[0])
        y.append(item[1])


    plt.hist(data, bins = (max-min)/0.01, align='mid', color = 'steelblue', edgecolor = 'k', label = title)
    plt.show()

    # pl.plot(x, y, 'o')# use pylab to plot x and y
    # pl.plot(x, y, 'r')# use pylab to plot x and y
    # pl.title(title)
    # pl.xlabel('Response time (s)')
    # pl.ylabel('Count')
    # pl.show()# show the plot on the screen



def testGet(url,timeout,successQueue,failQueue,queueForId):
    failNum=0
    for loop in range(repeat):
        contract_id=queueForId.get()
        # url='http://akka-aps-prod-spray.internal.gridx.com:8082/v1/getComparedAPI/'+contract_id
        # url='http://10.100.34.73:8082/v1/getComparedAPI/'+contract_id

        try:
            r = requests.get(url+contract_id, timeout=timeout)
            json=r.json()
            code=json['meta']['code']
            total_seconds=r.elapsed.total_seconds()
            print "get response:",total_seconds
            if code == 200:
                successQueue.put(total_seconds)
            else:
                print "get Code",code,":",contract_id
                failQueue.put(total_seconds)
        except Exception,e:
            print e
            failNum=failNum+1
            print "get exception",contract_id
            failQueue.put(10)
    print "get fails:",failNum


def testPost(url,timeout,successQueue,failQueue,queueForId):
    failNum=0
    for loop in range(repeat):
        contract_id=queueForId.get()
        # url='http://akka-aps-prod-spray.internal.gridx.com:8082/v1/getMailerSummary'
        # url='http://10.100.34.73:8082/v1/getMailerSummary'
        payload = {'SAlist': contract_id}
        try:
            r = requests.post(url, json=payload, timeout=timeout)
            json=r.json()
            code=json['meta']['code']
            total_seconds=r.elapsed.total_seconds()
            print "post response:",total_seconds
            if code == 200:
                successQueue.put(total_seconds)
            else:
                print "post Code",code,":",contract_id
                failQueue.put(total_seconds)
        except Exception,e:
            print e
            failNum=failNum+1
            print "post exception",contract_id
            failQueue.put(10)
    print "post fails:",failNum


if __name__=="__main__":
    opts, args = getopt.getopt(sys.argv[1:], "c:g:p:t:")

    for op, value in opts:
        if op == "-c":
            concurrentNum = int(value)
        elif op == "-g":
            url_get = value
        elif op == "-p":
            url_post = value
        elif op == "-t":
            timeout = int(value)
        else :
            print "unmatched parameters"
            sys.exit()

    tmsp = time.strftime("%Y%m%d%H%M", time.localtime())
    result = open("result_"+str(concurrentNum)+"_"+tmsp+".txt",'w+')

    contract_id_num=concurrentNum*repeat*2

    print >> result,"Concurrent threads:",str(concurrentNum)
    print >> result,"Url of get:",url_get
    print >> result,"Url of post:",url_post
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
    failQueueForGet = Queue.Queue(concurrentNum*100)
    queueForPost = Queue.Queue(concurrentNum*100)
    failQueueForPost = Queue.Queue(concurrentNum*100)
    threads = []
    for i in range(concurrentNum):
        t1=threading.Thread(target=testGet,args=(url_get,timeout,queueForGet,failQueueForGet,queueForId,))
        t2=threading.Thread(target=testPost,args=(url_post,timeout,queueForPost,failQueueForPost,queueForId,))
        t1.setDaemon(True)
        t2.setDaemon(True)
        t1.start()
        t2.start()
        threads.append(t1)
        threads.append(t2)

    for t in threads:
        t.join()

    print >>result,"Get result:"
    statistic('Get Success',queueForGet,result)
    print >>result,"Get fail:"
    statistic('Get fail',failQueueForGet,result)
    print >>result,"Post result:"
    statistic('Post success',queueForPost,result)
    print >>result,"Post fail:"
    statistic('Post fail',failQueueForPost,result)

    print >> result,"end:",time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    result.close()
