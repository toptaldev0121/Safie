# -*- coding: utf-8 -*-
"""
Created on Tue May 14 03:51:53 2024

@author: admin
"""

import os
import json
import requests
from typing import Optional
from datetime import datetime, timezone, timedelta
import rfc3339
from time import sleep



SAFIE_API_BASE_URL = ""
SAFIE_API_KEY = ""
NAS_PATH = ""


def loadConfig():
    f = open("config.ini", "r")
    
    server_url = f.readline()   # server url
    server_url = server_url.replace("server_url=", "")
    server_url = server_url.replace("\n", "")
    
    api_key = f.readline()        #api key
    api_key = api_key.replace("api_key=", "")
    api_key = api_key.replace("\n", "")
    
    nas_path = f.readline()        #nas_path
    nas_path = nas_path.replace("nas_path=", "")
    nas_path = nas_path.replace("\n", "")
    
    f.close()
    return server_url, api_key, nas_path


# this function gets available connection devices by using authentication.
def getDeviceList(all: bool, api_key: str, offset: int, limit: int, item_id: Optional[int]):
    device_list = list()
    device_count = 0
    if all:
        offset, limit, item_id = 0, 100, None
        
    has_next, current_offset = True, offset
    while has_next:
        params = {"offset": current_offset, "limit": limit}
        if item_id is not None:
            params["item_id"] = item_id
            
        # send request
        res = requests.get(
            url = f"{SAFIE_API_BASE_URL}/v2/devices",
            headers = {"Safie-API-Key": api_key},
            params = params)
        
        sleep(10) # 200req/15min
        res.raise_for_status()  #wait

        json_res = res.json()   #convert to JSON
        has_next = json_res["has_next"]
        current_offset = json_res["count"]
        for i in json_res["list"]:
            device_list.append(i)
        device_count += current_offset
        
    print(device_list)
    return device_list, device_count


# this function download media file.
def mediafile_download(api_key: str, device_id: str, start_time: datetime, end_time: datetime):
    # create media file
    res = requests.post(
        url = f"{SAFIE_API_BASE_URL}/v2/devices/{device_id}/media_files/requests",
        headers = {"Safie-API-Key": api_key},
        json = {
            "start": rfc3339.rfc3339(start_time),
            "end": rfc3339.rfc3339(end_time)
            }
    )
    sleep(65) # 15req/15min
    
    #res.raise_for_status()  # wait
    if res.status_code != 200:
        print(res.json()["detail"])
        return
    
    request_id = res.json()["request_id"]
    
    # loop until creation media file.
    isAvailable = False
    while isAvailable is not True:
        res = requests.get(
            url = f"{SAFIE_API_BASE_URL}/v2/devices/{device_id}/media_files/requests/{request_id}",
            headers = {"Safie-API-Key": api_key})
        sleep(20)
        
        res.raise_for_status()
        
        state = res.json()["state"]
        if state == "FAILED":
            raise Exception("メディアファイルの作成に失敗しました。")
        elif state == "PROCESSING":
            raise Exception("規定の時間内にメディアファイル作成が終了しませんでした。")
        elif state == "AVAILABLE":
            url = res.json("url")
            
            # call download API
            res = requests.get(url, 
                               headers = {"Safie-API-Key": api_key},
                               stream = True)
            sleep(35) #30req/15min
            res.raise_for_status()
            
            file_name = os.path.dirname(__file__) + f"/{device_id} - {start_time}~{end_time}.mp4"
            with open(file_name, "wb") as fw:
                for chunk in res.iter_content(chunk_size = 100 * 1024):
                    fw.write(chunk)
            
            print(f"{file_name}")
            break


def start():
    # get device list
    device_list, device_count = getDeviceList(True, SAFIE_API_KEY, 0, 100, None)
    
    print("Device count : ", device_count)
    
    if device_count == 0:
        return
    
    elif device_count > 0:
        # get record time
        # loop device list
        time = datetime.now()
        delta = timedelta(minutes = 10)
        end = datetime(time.year, time.month, time.day - 1, 3, 0, 0)
        for device in device_list:
            #download every 10 minutes data
            for i in range(6*24):
                start = end - delta
                print("time range : ", end, start)
                mediafile_download(SAFIE_API_KEY, device["device_id"], start, end)
                end = start


if __name__ == "__main__":
    # load config information
    SAFIE_API_BASE_URL, SAFIE_API_KEY, NAS_PATH = loadConfig()

    #start()
