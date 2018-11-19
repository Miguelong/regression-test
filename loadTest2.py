#!/usr/bin/python
# -*- coding: UTF-8 -*-

import requests
import Queue
import json
import time
import threading
from threading import Timer
import MySQLdb
import sys, getopt
import os
import matplotlib
matplotlib.use('Agg')
import pylab as pl
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
from time import ctime,sleep



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

    bins = int((max-min)/0.01)
    if bins ==0:
        bins=1

    plt.hist(data, bins = bins, color = 'steelblue', edgecolor = 'k', label = 'title')
    plt.title(title)
    plt.xlabel('Response time (s)')
    plt.ylabel('Count')
    plt.show()
    plt.savefig(title+".png")

def outputFails(queue,file):
    if not queue.empty():
        print >>file,"------------------------------------------------------------------------------------"
        print >>file,"Fail: ",queue.qsize()

    dict={}
    while not queue.empty():
        item=queue.get()
        key=item[0]
        value=item[1]
        if dict.has_key(key):
            dict[key].append(value)
        else:
            dict[key]=[value]

    items=dict.items()
    for item in items:
        print >>file, item[0]
        print >>file, item[1]


def request_get(url):
    try:
        # r = requests.get(url, timeout=timeout)
        r = requests.get(url)
        json=r.json()
        code=json['meta']['code']
        total_seconds=r.elapsed.total_seconds()
        return (None,code,total_seconds)
    except Exception,e:
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
        return (e,None,None)

def request_get_proxy(url):
    try:
        if header==None:
            cmd="curl -w 'time_total: %{time_total}\n' '"+url+"' -H 'Content-Type:application/json' --proxy "+proxy
        else:
            cmd="curl -w 'time_total: %{time_total}\n' '"+url+"' -H 'Content-Type:application/json' -H '"+header+"' --proxy "+proxy

        res=os.popen(cmd).read()
        index=res.find('time_total')
        code=json.loads(res[0:index])['meta']['code']
        total_seconds=float(res[index+12:].replace("\n",""))
        return (None,code,total_seconds)
    except Exception,e:
        return (e,None,None)

def request_post_proxy(url,payload):
    try:
        if header==None:
            cmd="curl -w 'time_total: %{time_total}\n' '"+url+"' -X POST -H 'Content-Type:application/json' -d '"+payload+"' --proxy "+proxy
        else:
            cmd="curl -w 'time_total: %{time_total}\n' '"+url+"' -X POST -H 'Content-Type:application/json' -H '"+header+"' -d '"+payload+"' --proxy "+proxy

        res=os.popen(cmd).read()
        index=res.find('time_total')
        code=json.loads(res[0:index])['meta']['code']
        total_seconds=float(res[index+12:].replace("\n",""))
        return (None,code,total_seconds)
    except Exception,e:
        return (e,None,None)

def processResponse(res,timeout,successQueue,timeoutQueue,failQueue,parameters):
    e=res[0]
    code=res[1]
    total_seconds=res[2]
    if e==None:
        if code == 200:
            if total_seconds>timeout:
                timeoutQueue.put(total_seconds)
            else:
                successQueue.put(total_seconds)
        else:
            failQueue.put(("code "+str(code),parameters))
    else:
        failQueue.put((repr(e),parameters))


def testGet(url_template,timeout,successQueue,timeoutQueue,failQueue,parametersList):
    # get count of parameters of the url
    parameters_count=url_template.count('${')
    for parameters in parametersList:
        list=json.loads(parameters)
        url=url_template
        for i in range(parameters_count):
            old='${'+str(i)+'}'
            new=list[i]
            url=url.replace(old,new)
        if proxy==None:
            res=request_get(url)
        else:
            res=request_get_proxy(url)
        processResponse(res,timeout,successQueue,timeoutQueue,failQueue,parameters)

def testPost(url,payload_template,timeout,successQueue,timeoutQueue,failQueue,parametersList):
    # get count of parameters of the payload
    parameters_count=payload_template.count('${')
    for parameters in parametersList:
        list=json.loads(parameters)
        payload=payload_template
        for i in range(parameters_count):
            old='${'+str(i)+'}'
            new=list[i]
            payload=payload.replace(old,new)

        if proxy==None:
            res=request_post(url,json.loads(payload))
        else:
            res=request_post_proxy(url,payload)

        processResponse(res,timeout,successQueue,timeoutQueue,failQueue,parameters)

def getProgress(total_num,successQueue,timeoutQueue,failQueue):
    global progress
    while progress!=100.0:
        time.sleep(3)
        processed_num=successQueue.qsize()+timeoutQueue.qsize()+failQueue.qsize()
        progress=round(float(processed_num)/total_num*100)
        print total_num,processed_num
        print progress



proxy=None
header=None
progress=0.0

if __name__=="__main__":
    opts, args = getopt.getopt(sys.argv[1:], "c:u:m:h:t:p:x:")

    for op, value in opts:
        if op == "-c":
            concurrentNum = int(value)
        elif op == "-u":
            url = value
        elif op == "-m":
            method = value
        elif op == "-h":
            header = value
        elif op == "-p":
            payload = value
        elif op == "-t":
            timeout = int(value)
        elif op == "-x":
            proxy = value
        else :
            print "unmatched parameters"
            sys.exit()

    tmsp = time.strftime("%Y%m%d%H%M", time.localtime())
    result = open("result_"+str(concurrentNum)+"_"+tmsp+".txt",'w+')

    print >> result,"Concurrent threads:",str(concurrentNum)
    print >> result,"Url:",url
    print >> result,"Method:",method
    if not proxy==None:
        print >> result,"Proxy:",proxy
    if not header==None:
        print >> result,"Header:",header
    print >> result

    print >> result,"begin:",time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print >> result

    with open('parameters.json','r') as f:
        lines=f.readlines()

    ##split parameters for each thread
    parameters=[]
    total_num=len(lines)
    size=total_num/concurrentNum
    begin=0
    end=size
    for i in range(concurrentNum):
        if i==concurrentNum-1:
            end=total_num

        arr=lines[begin:end]
        parameters.append(arr)
        begin=begin+size
        end=end+size

    successQueue = Queue.Queue(total_num)
    timeoutQueue = Queue.Queue(total_num)
    failQueue = Queue.Queue(total_num)
    threads = []
    for i in range(concurrentNum):
        parametersPerThread=parameters[i]
        if method == 'get':
            t=threading.Thread(target=testGet,args=(url,timeout,successQueue,timeoutQueue,failQueue,parametersPerThread,))
        elif method == 'post':
            t=threading.Thread(target=testPost,args=(url,payload,timeout,successQueue,timeoutQueue,failQueue,parametersPerThread,))

        t.setDaemon(True)
        t.start()
        threads.append(t)

    t=threading.Thread(target=getProgress,args=(total_num,successQueue,timeoutQueue,failQueue,))
    t.setDaemon(True)
    t.start()
    threads.append(t)

    for t in threads:
        t.join()



    statistic('Success',successQueue,result)
    statistic('Timeout',timeoutQueue,result)


    outputFails(failQueue,result)

    print >>result

    print >> result,"end:",time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    result.close()
