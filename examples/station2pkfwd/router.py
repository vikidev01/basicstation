# --- Revised 3-Clause BSD License ---
# Copyright Semtech Corporation 2022. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright notice,
#       this list of conditions and the following disclaimer in the documentation
#       and/or other materials provided with the distribution.
#     * Neither the name of the Semtech corporation nor the names of its
#       contributors may be used to endorse or promote products derived from this
#       software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL SEMTECH CORPORATION. BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from typing import Any,Awaitable,Callable,Dict,List,Mapping,MutableMapping,Optional
import asyncio
import websockets
import logging
import json
import struct
import base64
import datetime
import copy
from websockets.server import WebSocketServerProtocol as WSSP
import time
import router_config
import pkfwdc
from id6 import Id6, Eui
from bgtask import BgTask

import db
import paho.mqtt.client as mqtt

logger = logging.getLogger('ts2pktfwd')
MQTT_TOPIC = 'router/other'

def xtime2bits32(xtime:int) -> int:
    return xtime & 0xFFFFFFFF


class Router:   
    ''' Map Station messages to pkfwd and vice versa. '''

    def __init__(self, routerid:Id6, config:router_config.RouterConfig, pkfwduri:Any, mqtt_client:mqtt.Client) -> None:
        self.routerid = routerid
        self.config = config
        self.pkfwdc = pkfwdc.PkFwdC(pkfwduri, routerid, config, self.on_pull_resp, self.get_pkfwd_stat)
        self.mqtt_client = mqtt_client
        self.websocket = None           # type:Optional[WSSP]
        empty_list_fn = list            # type: Callable[[],List[Mapping{str,Any]]]
        self.ws_write_bgtask = BgTask(self.ws_write_bgtask_func, empty_list_fn, 'ws_write_bgtask', 10.0)
        self.ws_write_bgtask.start()
        self.deveui = None
        self.chan = 0
        self.rfch = 0
        
        self.pkfwdstat = {
            'lati': 0.0,   # number | GPS latitude of the gateway in degree (float, N is +)
            'long': -0.0,  # number | GPS latitude of the gateway in degree (float, E is +)
            'alti': 0,     # number | GPS altitude of the gateway in meter RX (integer)
            'rxnb': 0,     # number | Number of radio packets received (unsigned integer)
            'rxok': 0,     # number | Number of radio packets received with a valid PHY CRC
            'rxfw': 0,     # number | Number of radio packets forwarded (unsigned integer)
            'dwnb': 0,     # number | Number of downlink datagrams received (unsigned integer)
            'txnb': 0,     # number | Number of packets emitted (unsigned integer)
            'lora': 0      # number | Number of packets lora recived (unsigned integer)
        }
        
        self.last_xtime = 0

    def __str__(self):
        return 'Router:%s' % (self.routerid)


    def get_routerid(self) -> Id6:
        return self.routerid


    def get_rid(self) -> int:
        return self.routerid.id


    async def start(self):
        await self.pkfwdc.start()

    def publish_mqtt(self, topic: str, payload: dict) -> None:
        try:
            self.mqtt_client.publish(topic, json.dumps(payload))
        except Exception as e:
            logger.error(f"{self}: MQTT publish failed: {e}")

    async def on_ws_connect(self, websocket:WSSP):
        ''' Station has been connected. Loop receiving messages on web socket. '''
        try:
            if self.websocket is not None:
                logger.error('%s: router already connected, switching to new connection.' % (self))
            try:
                await self.websocket.close()
            except:
                pass  

            self.websocket = websocket

            await self.pkfwdc.resume()
            await asyncio.sleep(0.3)

            while True:
           
                raw_msg = await websocket.recv()
                try:
                    s = json.loads(raw_msg)
                except json.JSONDecodeError as e:
                    print("ERROR de JSON:", e)
                    continue  # o break, según si querés cortar la conexión o no
                
                msgtype = s.get('msgtype')

                if msgtype == 'version':
                    logger.info('%s: on_ws: version: %s' % (self, s))
                    msg = self.config.get_station_config_message()
                    msg['MuxTime'] = datetime.datetime.utcnow().timestamp()
                    msg['msgtype'] = 'router_config'
                    await websocket.send(json.dumps(msg))
                # JOIN REQUEST
                elif msgtype == 'jreq':
                    self.pkfwdstat['rxnb'] += 1
                    self.pkfwdstat['rxok'] += 1
                    self.pkfwdstat['rxfw'] += 1

                    joineui = Eui(s['JoinEui'])
                    deveui = Eui(s['DevEui'])
                    devnonce = s['DevNonce']
                    mic = s['MIC']
                    mhdr = s['MHdr']
                    pdu_ba = struct.pack("<BqqHi", mhdr, joineui.as_int(), deveui.as_int(), devnonce & 0xFFFF, mic)
                    xtime = s['upinfo']['xtime']
                    self.last_xtime = xtime
                    rxtime = s['upinfo']['rxtime']
                    rssi = s['upinfo']['rssi']
                    snr = s['upinfo']['snr']
                    datr = self.config.dr2sfbw[s['DR']]
                    #self.pkfwdc.push_rxpk(rxtime, xtime2bits32(xtime), self.chan, self.rfch, s['Freq'], datr, rssi, snr, pdu_ba)
                # UPLINK DATAFRAME
                elif msgtype == 'updf':
                    self.pkfwdstat['rxnb'] += 1
                    self.pkfwdstat['rxok'] += 1
                    self.pkfwdstat['rxfw'] += 1

                    mic = s['MIC']
                    mhdr = s['MHdr']
                    devaddr = s['DevAddr']
                    fctrl = s['FCtrl']
                    fcnt = s['FCnt']
                    fopts = bytes.fromhex(s['FOpts'] if s['FOpts'] else '')
                    fport = bytes.fromhex('%02x' % s['FPort']  if s['FPort'] >= 0 else '')
                    frmpayload = bytes.fromhex(s['FRMPayload'] if s['FRMPayload'] else '')
                    pdu_ba = struct.pack("<BiBH{}s{}s{}si".format(len(fopts), len(fport), len(frmpayload)),
                                         mhdr, devaddr, fctrl & 0xFF, fcnt & 0xFFFF, fopts, fport, frmpayload, mic)
                    datr = self.config.dr2sfbw[s['DR']]
                    xtime = s['upinfo']['xtime']
                    self.last_xtime = xtime
                    rxtime = s['upinfo']['rxtime']
                    rssi = s['upinfo']['rssi']
                    snr = s['upinfo']['snr']
                    #self.pkfwdc.push_rxpk(rxtime, xtime2bits32(xtime), self.chan, self.rfch, s['Freq'], datr, rssi, snr, pdu_ba)
                    
                elif msgtype == 'dntxed':
                    self.pkfwdstat['txnb'] += 1
                    token = s['diid']
                    self.pkfwdc.push_txack(token)
                elif msgtype == 'lora':
                    self.pkfwdstat['rxnb'] += 1
                    self.pkfwdstat['rxok'] += 1
                    self.pkfwdstat['rxfw'] += 1
                    xtime = s['upinfo']['xtime']
                    self.last_xtime = xtime
                    rxtime = s['upinfo']['rxtime']
                    rssi = s['upinfo']['rssi']
                    snr = s['upinfo']['snr']
                    datr = self.config.dr2sfbw.get(s['DR'])  # Valor por defecto
                    print('-------------------------------------------------------------datr', datr)
                    payload = s["payload"]
                    deveui = s["DevEUI"]
                    freq = s["Freq"]
                    self.deveui = deveui
                    pdu_ba = bytes.fromhex(payload)
                    self.publish_mqtt(MQTT_TOPIC, s)  
                    self.pkfwdc.push_rxpk(rxtime, xtime2bits32(xtime), self.chan, self.rfch, s['Freq'], datr, rssi, snr, pdu_ba)
                    await self.transmitter(deveui, xtime, freq)

                    # Save the message to the database
                    db.insert_device_if_not_exists(deveui)

                    message_id = db.insert_message(
                        deveui=deveui,
                        datetime=rxtime,
                        frec=s['Freq'],
                        rssi=rssi,
                        snr=snr,
                        fcnt=s["FCnt"]
                    )

                    if 'GNSS_TS' in s and 'GNSS_Status' in s and 'GNSS' in s:
                        db.insert_gnss(
                            message_id=message_id,
                            timestamp_scan=s['GNSS_TS'],
                            status=s['GNSS_Status'],
                            payload=s['GNSS']
                        )

                    if 'WiFi_TS' in s and 'WiFi_MACs' in s:
                        db.insert_wifi(
                            message_id=message_id,
                            timestamp_scan=s['WiFi_TS'],
                            balizas=s['WiFi_MACs']
                        )

                    if any(k in s for k in ['Batt', 'Ener', 'Charge ', 'Flags', 'Resets', 'Temp']):
                        batt   = s.get('Batt')
                        ener   = s.get('Ener')
                        carga  = s.get('Charge ')
                        flags  = s.get('Flags')
                        resets = s.get('Resets')
                        temp   = s.get('Temp')
                        db.insert_status(
                            message_id=message_id,
                            battery=batt,
                            energy=ener,
                            millisec_in_charge=carga,
                            flag_status=flags,
                            cant_reset=resets,
                            temp=temp
                        )
                            
                    

        except Exception as exc:
            logger.error('%s: server socket failed: %s', self, exc, exc_info=True)
        finally:
            self.websocket = None
            await self.pkfwdc.pause() 

    async def transmitter(self, deveui, xtime, freq):
        payload = deveui
        token_tx = 1
        tmst =  xtime
        # Determinar el rfch según la frecuencia
        rfch = 0
        if 918400000 <= freq < 919200000:
            rfch = 0
        elif 919200000 <= freq <= 919800000:
            rfch = 1
        encoded_data = payload
        data_tx = {
            "txpk": {
                "imme": True,
                "tmms": 0,
                "tmst": tmst,
                "freq": 927.5,
                "rfch": rfch,
                "powe": 14,
                "modu": "LORA",
                "datr": "SF8BW500",
                "codr": "4/5",
                "ipol": False,
                "size": len(payload),
                "data": encoded_data,
                "ncrc": False
            } 
        }
        self.pkfwdc.on_pull_resp(token_tx, data_tx)
       
    def get_pkfwd_stat(self) -> MutableMapping[str,Any]:
        return self.pkfwdstat

    def on_pull_resp(self, token:int, obj:Any) -> None:
        ''' PULL_RESP from pktfwd socket with downlink for Station. '''
        if 'txpk' not in obj:
            logger.info('%s: on_pull_resp: unhandled message: %s' % (self, obj))
            return

        self.pkfwdstat['dwnb'] += 1

        txpk = obj['txpk']
        RxDelay  = self.config.RxDelay
        rx2dr = self.config.RX2DR
        rx2freq = self.config.RX2Freq
        rx1dr = self.config.sfbw2dr[txpk['datr']]
        
        rx1freq = int(float(txpk['freq'])*1e6)
        pdu_hex = txpk['data'].replace('-', '')

        xtime = txpk['tmst'] - int(RxDelay*1e6)
        xtime = (self.last_xtime & 0xFFFFFFFF00000000) | xtime
        dnmsg = {
            'msgtype': 'dnmsg',
            'xtime':    xtime,
            'RxDelay':  RxDelay,
            'RX1Freq':  rx1freq,
            'RX1DR':    rx1dr,
            'RX2DR':    rx2dr,
            'RX2Freq':  rx2freq,
            'dC':       0,
            'pdu':      pdu_hex, 
            'dnmode':   'updn',
            'diid':     token,
            'MuxTime':  datetime.datetime.utcnow().timestamp()
        }
        if self.deveui is not None:
            dnmsg['DevEui'] = self.deveui
        else:
            dnmsg['DevEui'] = '00-00-00-00-00-00-00-00'  # fallback

        if self.config.get_hwspec() == 'sim':
            dnmsg['regionid'] = self.config.get_regionid()

        logger.info('%s: on_pull_resp: dnmsg: %s' % (self, dnmsg))
        self.send_ws(dnmsg)


    def send_ws(self, msg:Mapping[str,Any]) -> None:
        self.ws_write_bgtask.queue.append(msg)
        self.ws_write_bgtask.notify()


    async def ws_write_bgtask_func(self, queue:List[Mapping[str,Any]]) -> None:
        ''' Write queued messages out for Station. '''
        try:
            for e in queue:
                logger.debug('%s: ws_write_bgtask_func: %s' % (self, e))
                if self.websocket is not None:
                    await self.websocket.send(json.dumps(e))
        except asyncio.CancelledError:
            logger.error('%s: ws_write_bgtask_func cancelled.' % (self))
            raise
        except Exception as exc:
            logger.error('%s: ws_write_bgtask_func failed: %s', self, exc, exc_info=True)
