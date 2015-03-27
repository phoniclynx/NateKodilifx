import sys
# import xbmc
# import xbmcgui
# import xbmcaddon
import os
import subprocess
from time import sleep
from subprocess import call

import requests
import json
import urllib
import ConfigParser


def checkIfMovie():
    isTVorMovieQuery = {'jsonrpc': '2.0', 'method': 'Player.GetItem', 'params': {'properties': ['showtitle', 'season', 'episode'], 'playerid': 1}, 'id': 'VideoGetItem'}
    response = json.loads(xbmc.executeJSONRPC(json.dumps(isTVorMovieQuery)))
    if response['result']['item']['season'] == -1:
        return True
    else:
        return False


def getLightState(name, type='label'):
    """ This function checks what lights are in the group and what color they are currently set to """
    if name == 'all':
        getAvaliableLights = requests.get(lifxCloud + '/' + name, headers=header)
    else:
        getAvaliableLights = requests.get(lifxCloud + '/' + urllib.quote(type + ':' + name), headers=header)

    if getAvaliableLights.status_code == requests.codes.ok:
        avaliableLights = json.loads(getAvaliableLights.text)
        info = []
        for light in avaliableLights:
            info.append({'id': light['id'], 'label': light['label'], 'power': light['power'], 'hue': light['color']['hue'], 'saturation': light['color']['saturation'],
                'brightness': light['brightness']})
        return info
    return False


def restoreLights(LightStates, duration=1):
    """ This function's purpose is to set the lights to a given HSK from what they once were"""
    for light in LightStates:
        if light['power'] == 'on':
            power = 'true'
            option = {'color': 'hsb:' + str(light['hue']) + ',' + str(light['saturation']) + ',' + str(light['brightness']), 'duration': duration, 'power': power}
            chooseBulb = lifxCloud + '/' + urllib.quote('id:') + light['id'] + '/color.json'
            requests.put(chooseBulb, json=option, headers=header)
        else:
            power = 'false'
            turnOff(name=light['id'], type='id', duration=duration)
            continue


def turnOff(name, type='label', duration=1):
    """ This function turns off a given group or light """
    powerCommand = lifxCloud + '/' + urllib.quote(type + ':' + name) + '/power.json'
    option = {'state': 'off', 'duration': duration}
    requests.put(powerCommand, json=option, headers=header)
    return


def loadConfig ():
    global header
    global bulbs
    global setColor
    global config

    confpath = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'lifx.cfg')
    config = ConfigParser.RawConfigParser()
    config.readfp(open(confpath))

    apiKey = config.get('Authentication', 'apiKey')
    apiKey = 'Bearer ' + apiKey
    header = {'content-type': 'application/json', 'authorization': apiKey}

    bulbs = {'type': config.get('Bulbs', 'type'), 'set': config.get('Bulbs', 'set')}
    bulbURL = urllib.quote(bulbs['type'] + ':' + bulbs['set'])
    setColor = lifxCloud + bulbURL + '/color.json'

lifxCloud = 'https://api.lifx.co/v1beta1/lights/'

loadConfig()

preVideolightState = []

class XBMCPlayer(xbmc.Player):

    def __init__(self, *args):
        pass

    def onPlayBackStarted(self):
        global preVideolightState
        loadConfig()
        preVideolightState = getLightState(type=bulbs['type'], name=bulbs['set'])
        if checkIfMovie():
            turnOff(name=bulbs['set'], type=bulbs['type'], duration=config.get('Delay', 'MovieStart'))
        else:
            option = {'color': 'blue brightness:5%', 'duration': config.get('Delay', 'TVStart'), 'power_on': 'true'}
            r = requests.put(setColor, json=option, headers=header)

    def onPlayBackResumed(self):
        global preVideolightState
        loadConfig()
        preVideolightState = getLightState(type=bulbs['type'], name=bulbs['set'])
        if checkIfMovie():
            turnOff(name=bulbs['set'], type=bulbs['type'], duration=config.get('Delay', 'Pause'))
        else:
            option = {'color': 'blue brightness:5%', 'duration': config.get('Delay', 'UnPause'), 'power_on': 'true'}
            r = requests.put(setColor, json=option, headers=header)

    def onPlayBackEnded(self):
        restoreLights(preVideolightState, duration=config.get('Delay', 'EndPlay'))

    def onPlayBackPaused(self):
        restoreLights(preVideolightState, duration=config.get('Delay', 'Pause'))

    def onPlayBackStopped(self):
        restoreLights(preVideolightState, duration=config.get('Delay', 'EndPlay'))

player = XBMCPlayer()

while(not xbmc.abortRequested):
    xbmc.sleep(100)