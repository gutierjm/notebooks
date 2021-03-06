import requests
import os
import sys
import time
import json
import zipfile
from .lib.parse_urls import parse_urls

class package_api:
    def __init__(self,dh,dataset,variable_name,longitude_west,longitude_east,latitude_south,latitude_north,time_start,time_end,area_name="",folder='./'):
        self.dh = dh
        self.dataset = dataset
        self.variable_name = variable_name
        self.coordinates = (longitude_west,longitude_east,latitude_south,latitude_north)
        self.temporal_extent = (time_start,time_end)
        self.variable = variable_name
        self.area_name = area_name
        self.folder = folder
        self.package_key = self.define_package_key()
        self.local_file_name = self.get_local_file_name()

        
    def make_package(self):
        if self.get_package_exists(): return
        kwgs = {'dataset':self.dataset,
                'polygon':'[[{0},{2}],[{1},{2}],[{1},{3}],[{0},{3}],[{0},{2}]]'.format(self.coordinates[0],self.coordinates[1],self.coordinates[2],self.coordinates[3]),
                'grouping':'location',
                'time_start':self.temporal_extent[0],
                'time_end':self.temporal_extent[1],
                'package':self.package_key,
                'var':self.variable_name}
        putrequest = "http://{0}/{1}/{2}?apikey={3}".format(self.dh.server,self.dh.version,'packages',self.dh.apikey)
        for i,j in kwgs.items():
            putrequest += "&{0}={1}".format(i,j)
        mp = requests.put(putrequest)

        if mp.status_code == 200:
            return
        else:
            raise ValueError("Package submittion failed")
        
    def get_package_exists(self):
        rrr = parse_urls(self.dh.server,self.dh.version,'packages/'+self.package_key,self.dh.apikey)
        return_status = False
        if rrr.r.status_code == 200:
            rjson = rrr.r.json()
            if 'packageResult' in rjson:
                if rjson['packageResult']['success']:
                    print("Package exists")
                    return_status = True
            elif rjson['packageStatus'] == 'started':
                print("Package started")
                return_status = True
            else:
                raise ValueError("Unknown package status, exit")
        return return_status
        
    def get_status(self):
        rrr = parse_urls(self.dh.server,self.dh.version,'packages/'+self.package_key,self.dh.apikey)
        rjson = rrr.r.json()
        if 'packageResult' in rjson:
            if rjson['packageResult']['success'] == True:
                return_status = 'ready'
            else:
                return_status = 'failure'
        else:
            return_status = 'not_ready'
        return return_status
        
        
    def define_package_key(self):
        return self.dataset + '_' + iso_time_simplify(self.temporal_extent[0]) + 'to' + \
               iso_time_simplify(self.temporal_extent[1]) + '_' + self.area_name 
        
    def get_local_file_name(self):
        return self.folder + '/' + self.package_key + '.nc'

    def wait_for_package_completion(self,maxtime=600):
        check_time = 10
        count = 0
        while count * check_time <= maxtime:
            status = self.get_status()
            if status == 'ready': return True
            elif status == 'not_ready':
                time.sleep(check_time)
            else:
                raise ValueError('Package creation failed')
            count += 1
        return False

    def get_download_path(self):
        return "http://{0}/{1}/packages/{2}/data?apikey={3}".format(self.dh.server,self.dh.version,self.package_key,self.dh.apikey)
    
    def download_package(self):
        if os.path.exists(self.local_file_name):
            print("File already downloaded")
            return
        if self.wait_for_package_completion():
            r = requests.get(self.get_download_path(),stream = True)
            if r.status_code == 200:
                 with open(self.package_key + ".zip", "wb") as dat:
                    dat.write(r.content)
            else:
                raise ValueError('something happened while downloading data. Please try again.')
            self.unzip()
        else:
            print("Package was not downloaded and error was not detected. It is safe to run \"download_package\" function as many times as needed.")

    def unzip(self):
        zip_filename = self.package_key + '.zip'
        zip_ref = zipfile.ZipFile(zip_filename, 'r')
        zip_ref.extract('data',)
        zip_ref.close()
        os.remove(zip_filename)
        os.rename(self.folder + 'data', self.local_file_name)

def iso_time_simplify(indate):
    return indate.replace(':','').replace('-','')
        
