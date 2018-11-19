import MySQLdb
import json

if __name__=="__main__":
    file = open("parameters2.json",'w+')
    db = MySQLdb.connect("10.100.2.143","long","y91lkeKY","aps_prod")
    cursor = db.cursor()
    cursor.execute("select distinct contract_id from unifiedbillimpactapi limit 6000")
    results = cursor.fetchall()

    for row in results:
        contract_id = row[0]
        arr=[contract_id]
        print >> file, json.dumps(arr)

    file.close()
