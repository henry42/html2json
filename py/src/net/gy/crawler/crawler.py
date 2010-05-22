'''
Created on May 16, 2010

@author: Henry
'''
from lxml import etree as ET;
from string import join;
from net.gy import log;
from urlparse import urljoin;
import json;

import html5lib;
import urllib;
import urllib2;
import uuid;
import re;
import time;
import logging;


def _writetologfile(filename,content):
    if not log.isEnabledFor(logging.DEBUG):
        return;
    newline = '\n';
    f = open("log/%s.log" % filename ,"a");
    f.write(newline);
    f.write(">>> begin");
    f.write(newline);
    f.write(content);
    f.write(newline);
    f.write(">>> end");
    f.write(newline);
    f.flush();
    f.close();

class crawler(object):

    def __init__(self):
        self.uri = None;
        self.content = None;
        self.cfg = None;\
        self.uuid = uuid.uuid4();
        self.MAX_URL_OPEN = 3;
        self.result = None;
        pass;
    def setCfgElement(self,element,start="root"):
        self.cfg = element.xpath("//*[@id='%s']" % start)[0];
        
        uri = self.cfg.get("uri");
        if(uri and self.uri is None and self.content is None):
            self.setUri(uri);
        
    def setCfgFile(self,filename,start="root"):
        self.setCfgElement(ET.parse("conf/" + filename).getroot(),start);
            
        
    def setUri(self,uri,params=None,headers=None):
        log.info("loading %s %s" % (uri,params));
        self.uri = uri;
        if(params is not None and type(params) == dict):
            params = urllib.urlencode(params);
        for i in range(1,self.MAX_URL_OPEN):
            try:
                opener=urllib.URLopener();
                opener.addheader("User-Agent","Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0;  Embedded Web Browser from: http://bsalsa.com/; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729; Media Center PC 6.0; InfoPath.2; .NET CLR 1.1.4322; Tablet PC 2.0)");
                opener.addheader("Cache-Control","no-cache");
                for k,v in (headers or {}).iteritems():
                    opener.addheader(k,v);
                self.content = opener.open(uri,params).read();
                break;
            except BaseException,e:
                log.error("%s got error %s" % (i,e));
                if i < self.MAX_URL_OPEN:
                    time.sleep(5);
            
    def setContent(self,content):
        self.content = content;
        
    def getConfig(self):
        return self.cfg;
    
    def setTranslator(self , tran):
        self.tran = tran;
        self.tran.crawler = self;
    
    def parse(self):
        self.result = None;
        
        if(self.content is None):
            log.error("no content for parsing");
            return;
        if(self.cfg is None):
            log.error("no config file");
            return;

        log.info("parsing");
        data = self._parse(self.tran.getroot(),self.cfg);
        log.info("done!");
        _writetologfile(self.uuid , json.dumps(data,ensure_ascii=False,indent=4));
        return data;
    
    def getlastresult(self):
        return self.result;
    
    def _parse(self ,element, cfg):
        
        if(element is None or cfg is None):
            return None;
        
        if(cfg.tag == 'dict'):
            return self._dictparse(element,cfg);
        elif(cfg.tag == 'list'):
            return self._listparse(element,cfg);
        elif(cfg.tag == 'val'):
            return self._dataparse(element,cfg);
        else:
            return None;
        
    def _listparse(self,element,cfg):
        rlist = [];
        if self.result is None:
            self.result = rlist;
        
        list = self.tran.select(element,cfg);
        
        ncfg = cfg.xpath("dict | list | val");
        if not len(ncfg):
            ncfg = None;
        else:
            ncfg = ncfg[0];
        
        for x in list:
            rlist.append(self._parse(x,ncfg));
            
        for item in cfg.findall("incl"):
            for ele in list:
                ilist = self.tran.select(ele,item);
                rlt = self._inclparse(item , ilist);
                if type(rlt) == list : 
                    for v in rlt:
                        rlist.append(v);
                else:
                    log.error("%s 's result is not a list (%s)" % (cfg.getroottree().getpath(cfg),type(rlt)));
        
        for item in cfg.findall("spec"):
            self.tran.spec(rlist , item , list);
        
        return rlist;
    
    def _dictparse(self,element,cfg):
        root = {};
        if self.result is None:
            self.result = root;
            
        list = self.tran.select(element,cfg);
        if(not list):
            return None;
        val = list[0];
            
        
            
        for item in cfg.findall("item"):
            root[item.get("name")] = self._itemparse(val,item);

        for item in cfg.findall("incl"):
            ilist = self.tran.select(element,item);
            rlt = self._inclparse(item , ilist);
            if type(rlt) == dict : 
                for k,v in rlt.iteritems():
                    root[k] = v;
            else:
                log.warn("%s 's result is not a dict (%s)" % (cfg.getroottree().getpath(cfg),type(rlt)));
        
        for item in cfg.findall("spec"):
            self.tran.spec(root , item , list);
            
        return root;
    
    def _itemparse(self,element,cfg):
        sval = self.tran.select(element,cfg);
        if cfg.get("type") is not None:
            tfunc = getattr(self.tran,"_" + cfg.get("type"));
            return tfunc(sval,cfg);
        else:
            child = cfg.xpath("dict | list | val");
            if len(child) and len(sval):
                return self._parse(sval[0],child[0]);
            else:
                return None;
    def _dataparse(self,element,cfg):
        list = self.tran.select(element,cfg);
        return self.tran._data(list,cfg);
    
    def _inclparse(self, cfg , matches):
        if not len(matches):
            return None;
        return self.tran.incl(cfg,matches[0]);
    def _specparse(self,root , cfg , matches):
        list = self.tran.select(root,cfg);
        for item in list:
            self.tran.spec(item,cfg,matches);
    

class translator():
    def __init__(self):
        self.crawler = None;

    def getroot(self):
        return None;
    def select(self , val , cfg):
        return [];
    def incl(self , cfg , match):
        val = self._data([match], cfg);
        url = urljoin(self.crawler.uri, val);
        sel = cfg.get("ref");
        if not len(sel):
            self.showerrorpath("cfg error",cfg);
        hashind = sel.rfind("#");
        start = (hashind > -1 and [sel[hashind + 1:]] or [None])[0];
        if hashind == -1:
            conf = sel;
        else:
            conf = sel[0:hashind];
            
        newT = crawler();
        newT.setTranslator(self.__class__());
        newT.setUri(url);
        if len(conf):
            newT.setCfgFile(conf,start);
        else:
            newT.setCfgElement(self.crawler.cfg.getroottree(),start);
        return newT.parse();
    def spec(self , root , cfg , matches):
        pass;
    
    def _text(self , matches , cfg):
        r = [];
        for m in matches:
            r.append(str(m));
        return join(r);
    def _data(self , matches , cfg):
        return self.text(matches, cfg);
    
    def showerrorpath(self,text,cfg):
        log.error((text or "parse cfg error") + " " + cfg.getroottree().getpath(cfg));
    

class xmltranslator(translator):
    def __init__(self):
        self.crawler = None;
    def getroot(self):
        content = self.crawler.content;
        root = html5lib.parse(content, treebuilder = "lxml",namespaceHTMLElements=False);
        nouse = root.xpath("//comment() | //script | //noscript | //style");
        while(len(nouse) > 0):
            el = nouse.pop();
            el.getparent().remove(el);

        _writetologfile(self.crawler.uuid , ET.tostring(root,pretty_print=True, encoding='UTF-8'));
        return root;
    def select(self , val , cfg):
        if(cfg.get("select") is not None):
            return val.xpath(cfg.get("select"));
        else:
            return [val];
    def spec(self , root , cfg , matches):
        pass;
    
    def _text(self , matches , cfg):
        r = [];
        for m in matches:
            if(type(m) == str):
                r.append(m);
            elif(ET.iselement(m)):
                r.append(m.text or '');
            else:
                r.append(str(m) or '');
        return join(r);
    def _data(self , matches , cfg):
        return self._text(matches, cfg);