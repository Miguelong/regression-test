#!/usr/bin/python
# -*- coding: UTF-8 -*-

import requests
import Queue
import json
import time
import threading
import MySQLdb
import os
# import pylab as pl
from time import ctime,sleep

def statistic(queue,file):
    dict={}
    sum=0.0
    count=0
    max=0.0
    while not queue.empty():
        total_seconds=queue.get()
        key=round(total_seconds,2)
        if dict.has_key(key):
            dict[key]=dict[key]+1
        else:
            dict[key]=1

        if total_seconds>max:
            max=total_seconds
        sum+=total_seconds
        count=count+1
        # print >>file, str(total_seconds).ljust(4)[:4],
        # if count%25 == 0:
        #     print >>file
    print >>file
    print >>file, str("max:%s" %max).ljust(9)[:9],
    if count >0 :
        print >>file, str("average:%s" %(sum/count)).ljust(13)[:13]

    items=dict.items()
    items.sort()
    print >>file, items
    # x=[]
    # y=[]
    # for item in items:
    #     x.append(item[0])
    #     y.append(item[1])
    #
    # pl.plot(x, y, 'o')# use pylab to plot x and y
    # pl.show()# show the plot on the screen



def testGet(successQueue,failQueue,queueForId):
    failNum=0
    for loop in range(100):
        contract_id=queueForId.get()
        cmd="curl --connect-timeout 5 -m 5 -w 'time_total: %{time_total}\n' 'https://aps-api.gridx.ws/mailer/v1/compareResult/"+contract_id+"' -H 'Content-Type:application/json' -H 'Authorization:Gridx hEwCQGumUL+vulFJKaiuUNzwr2v0ajrt' --proxy http://'gridx-proxy':'s6!K]t]i'@proxy.internal.gridx.com:3128"


        try:
            res=os.popen(cmd).read()
            # print res
            index=res.find('time_total')
            code=json.loads(res[0:index])['meta']['code']
            total_seconds=float(res[index+12:].replace("\n",""))
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


def testPost(successQueue,failQueue,queueForId):
    failNum=0
    for loop in range(100):
        contract_id=queueForId.get()
        cmd="curl --connect-timeout 5 -m 5 -w 'time_total: %{time_total}\n' 'https://aps-api.gridx.ws/mailer/v1/getSummary' -X POST -H 'Content-Type:application/json' -H 'Authorization: Gridx hEwCQGumUL+vulFJKaiuUNzwr2v0ajrt' -d '{\"contractIDs\": [\""+contract_id+"\"]}' --proxy http://'gridx-proxy':'s6!K]t]i'@proxy.internal.gridx.com:3128"

        try:
            res=os.popen(cmd).read()
            # print res
            index=res.find('time_total')
            code=json.loads(res[0:index])['meta']['code']
            total_seconds=float(res[index+12:].replace("\n",""))
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
    concurrentNum=50
    getResult=open("getResult_"+str(concurrentNum)+".txt",'w+')
    getFail=open("getFail_"+str(concurrentNum)+".txt",'w+')
    postResult=open("postResult_"+str(concurrentNum)+".txt",'w+')
    postFail=open("postFail_"+str(concurrentNum)+".txt",'w+')
    contract_id_num=concurrentNum*100*2

    print >> getResult,"begin %s" %ctime()
    print
    print >> postResult,"begin %s" %ctime()
    print

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
        t1=threading.Thread(target=testGet,args=(queueForGet,failQueueForGet,queueForId,))
        t2=threading.Thread(target=testPost,args=(queueForPost,failQueueForPost,queueForId,))
        t1.setDaemon(True)
        t2.setDaemon(True)
        t1.start()
        t2.start()
        threads.append(t1)
        threads.append(t2)

    for t in threads:
        t.join()

    statistic(queueForGet,getResult)
    statistic(failQueueForGet,getFail)
    statistic(queueForPost,postResult)
    statistic(failQueueForPost,postFail)

    print >> getResult,"end %s" %ctime()
    print
    print >> postResult,"end %s" %ctime()
    print

    getResult.close()
    getFail.close()
    postResult.close()
    postFail.close()
