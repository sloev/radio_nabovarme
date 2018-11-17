import asyncio
from aiohttp import web
import aiohttp_jinja2
from aiohttp.web import Response
from aiohttp_sse import sse_response
import paho.mqtt.client as mqtt
import multiprocessing
import csv
import json
import logging
import random
import os
import signal
import psutil
import jinja2

MAX_MESSAGES = 50
URL = os.environ['URL']
MQTT=os.environ['MQTT']

lookup = {}
scale = {
    0:0,
    1:2,
    2:4,
    3:7,
    4:9,
    5:12,
    6:14,
    7:16,
    8:19,
    9:21,
    10:24,
    11:16,
    12:28
}

with open('serials.csv', 'r') as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',')
    for row in spamreader:
        serial = row[0]
        instrument = str(ord(serial[-1]) % 13 )

        lookup[serial] = instrument


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("/sample/v2/#")
    client.subscribe("/config/v2/#")

client = mqtt.Client()
client.on_connect = on_connect

try:
    client.connect(MQTT, 1883, 60)
except:
    logging.exception("could not connect to mqtt server")
    exit(1)

def worker(queue, client, die_queue):

    # The callback for when a PUBLISH message is received from the server.
    def on_message(client, userdata, msg):
        serial_number = msg.topic.split('/')[3]
        try:
            instrument = lookup[serial_number]
            tone = scale.get((int(serial_number)) % 12 , 0) + (random.randint(-4,1)*12)
            decay = (((int(serial_number)+ random.randint(0,15) ) %15) / 10) + 0.001
            volume = min((((int(serial_number) / 20 + random.randint(0,20) ) %20) / 40) + 0.1, 0.4)

            queue.put(json.dumps(dict(
                tone=int(tone),
                instrument=str(instrument),
                decay=decay,
                volume=volume
            )), timeout=0.001)
            if random.randint(0,10) > 8:
                queue.put(json.dumps(dict(
                    tone=int(tone) + 8,
                    instrument=str(instrument),
                    decay=decay
                )), timeout=0.001)
        except:
            pass

    client.on_message = on_message

    try:
        client.loop_forever()
    except:
        logging.warning('disconnecting from mqtt')
        client.disconnect()
        logging.warning('disconnected from mqtt')
        die_queue.put('die')


queue = multiprocessing.Queue(maxsize=10)
die_queue = multiprocessing.Queue(maxsize=10)
p = multiprocessing.Process(target=worker, args=(queue, client, die_queue))
p.start()


async def events(request):
    loop = request.app.loop
    async with sse_response(request) as resp:
        while True:
            try:
                data = queue.get(block=False)
                logging.warning(f"transmitting item from queue: {data}")
                await resp.send(data)
            except:
                pass
            await asyncio.sleep(0.001, loop=loop)
    return resp


@aiohttp_jinja2.template('index.jinja2')
async def index(request):
    return {'url':URL}


async def message(request):
    app = request.app
    data = await request.post()
    payload = json.dumps(dict(data))
    logging.warning(f"message: {payload}")

    app['last_messages'].append(payload)
    if len(app['last_messages']) > MAX_MESSAGES:
        app['last_messages'] = app['last_messages'][-MAX_MESSAGES:]

    for queue in app['channels']:
        await queue.put(payload)
    return Response()

async def chat(request):
    async with sse_response(request) as response:
        app = request.app
        print('Someone joined.')

        this_queue = asyncio.Queue()
        app['channels'].add(this_queue)
        for queue in app['channels']:
            await queue.put(json.dumps(dict(online=len(app['channels']))))

        try:
            for message in app['last_messages']:
                logging.warning(f"last_message: message: {message}")
                await response.send(message)

            while not response.task.done():
                payload = await this_queue.get()
                await response.send(payload)
                this_queue.task_done()
        finally:
            print(f"someone left, online{len(app['channels'])}")

            for queue in app['channels']:
                await queue.put(json.dumps(dict(online=len(app['channels'])-1)))
            app['channels'].remove(this_queue)


    return response

app = web.Application()
aiohttp_jinja2.setup(app,
    loader=jinja2.FileSystemLoader('./templates'))
app['channels'] = set()
app['last_messages'] = [json.dumps(dict(message='Radio Nabovarme goddag!'))]
app['online'] = 0
app.router.add_route('GET', '/events', events)
app.router.add_route('GET', '/', index)
app.router.add_static('/static/', path='/static/', name='static')
app.router.add_route('POST', '/everyone', message)
app.router.add_route('GET', '/chat', chat)

def worker_app(app):
    web.run_app(app, host='0.0.0.0', port=80)

p_2 = multiprocessing.Process(target=worker_app, args=(app, ))
p_2.start()


def killtree(pid, including_parent=True):
    parent = psutil.Process(pid)
    for child in parent.children(recursive=True):
        child.kill()

    if including_parent:
        parent.kill()

## get the pid of this program
pid=os.getpid()

logging.warning("waiting for mqtt process")
while True:
    try:
        die_queue.get(timeout=1)
        break
    except:
        pass
logging.warning("killing process tree")
## when you want to kill everything, including this program
killtree(pid)

logging.warning("exiting")
