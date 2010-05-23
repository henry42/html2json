'''
Created on May 22, 2010

@author: Henry
'''
from net.gy.crawler.crawler import crawler;
from net.gy.crawler.crawler import xmltranslator;
from net.gy import log;
import ConfigParser;
import codecs;
from datetime import datetime;
from mysql import connector as pydb;

CONFIG = None;
SQL_CONN = None;


def loadconf():
    global CONFIG;
    global SQL_CONN;
    
    config = ConfigParser.ConfigParser()  
    config.readfp(codecs.open("conf/ef.ini", "r"));
    log.info("conf loaded");
    SQL_CONN = {
                "host" : config.get("database", "host"),
                "db" : config.get("database", "db"),
                "port" : config.getint("database", "port"),
                "user" : config.get("database", "user"),
                "passwd" : config.get("database", "passwd")
                }
    
loadconf();

def update_fund_info():
    
    log.info('update_fund_info start');
    
    global SQL_CONN;
    
    crawl = crawler();
    crawl.setTranslator(xmltranslator());
    crawl.setCfgFile("crawler_fund_of_163.xml");
    result = crawl.parse();
    sql4info = '''INSERT INTO fund_info (
        CODE , 
        NAME , 
        manager , 
        size , 
        company , 
        birthday , 
        `type` , 
        status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE 
        NAME=%s,
        manager=%s,
        size=%s,
        company=%s,
        birthday=%s,
        `type`=%s,
        status=%s''';
        
    sql4data = '''insert into fund_data (
                code , 
                date , 
                nav , 
                tnav) values (%s,%s,%s,%s) on duplicate key update 
                nav=%s,
                tnav=%s ''';
    conn = pydb.connect(**SQL_CONN);
    cur = conn.cursor();

    array = result.get('data',[]);
    for data in array:
        log.info("update %s %s" % (data['code'],data['name']));
        d1 = (data['code'],)+(data['name'],
                data['manager'],
                data['size'],
                data['company'],
                data['birthday'],
                data['type'],
                data['status'])*2;
        log.debug("data %s" % list(d1));
        cur.execute(sql4info,d1);
        d2=(data['code'],data['date'])+(data['nav'],data['tnav'])*2
        log.debug("data %s" % list(d2));
        cur.execute(sql4data,d2);
        warnings = cur.fetchwarnings()
        if warnings:
            log.warn("db:" + warnings);
        conn.commit();
        
    cur.close();
    conn.close();
    
    log.info('update_fund_info done');
    
def update_all_nav(fundcode=[],start=None,end=datetime.now()):
    
    log.info('update_all_nav start');
    
    global SQL_CONN;
    
    req = 'http://biz.finance.sina.com.cn/fundinfo/open/lsjz.php?fund_code=';
    fundstart = {};
    endtime = end.strftime('%Y-%m-%d');
    
    conn = pydb.connect(**SQL_CONN);
    cur = conn.cursor();
    cur.execute("select code,birthday from fund_info");
    for row in cur.fetchall():
        fundstart[row[0]] = {'startdate1' : row[1].strftime('%Y-%m-%d'),'enddate1':endtime};
    if fundcode is None:
        fundcode = fundstart.keys();

    sql4data = '''insert into fund_data (
                code , 
                date , 
                nav , 
                tnav) values (%s,%s,%s,%s) on duplicate key update 
                nav=%s,
                tnav=%s ''';
    ind = 1;
    count = len(fundcode);
    cur = conn.cursor();
    for fc in fundcode:
        log.info("start %s %s/%s" % (fc,ind,count));
        crawl = crawler();
        crawl.setTranslator(xmltranslator());
        postdata = fundstart[fc];
        if start is not None:
            postdata['startdate1'] = start.strftime('%Y-%m-%d');
        header = {'Refer':req + fc};
        crawl.setUri(req + fc,postdata,header);
        crawl.setCfgFile("crawler_allfund_of_sina.xml");
        result = crawl.parse();
        log.debug("data %s %s" % (fc,result));
        
        for data in result or []:
            if(result):
                cur.execute(sql4data,(fc,data['date'])+(data['nav'],data['tnav'])*2);
            else:
                log.error("no information about %s" % fc);
        warnings = cur.fetchwarnings()
        if warnings:
            log.warn("db:" + warnings);
        conn.commit();
        log.info("done %s %s/%s" % (fc,ind,count));
	ind = ind + 1;
    
    conn.close();
    log.info('update_all_nav done');
        
    
    