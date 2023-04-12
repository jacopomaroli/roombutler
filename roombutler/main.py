import asyncio
import websockets
import json
import uvicorn
from typing import Union
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx
import pandas as pd
import os
import threading
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score, ConfusionMatrixDisplay
from sklearn.model_selection import RandomizedSearchCV, train_test_split
import pickle
from operator import itemgetter
from scipy.stats import randint

app = FastAPI()

config = {
    'room_assistant': {
        'rest_url': os.getenv('ROOM_ASSISTANT_REST_URL'),
        'ws_url': os.getenv('ROOM_ASSISTANT_WS_URL')
    }
}

devices = {}
nodes_list = []
train_data = None
cols = []
model = None
is_training = False


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


async def request(client):
    response = await client.get(f"{config['room_assistant']['rest_url']}/entities")
    return response.json()


async def get_entities_ups():
    async with httpx.AsyncClient() as client:
        tasks = request(client)
        result = await asyncio.gather(tasks)
        return result[0]


@app.get("/api/entities")
async def get_entities():
    global devices
    global nodes_list
    global cols
    entities = await get_entities_ups()
    devices_list = list(filter(lambda x: x.get('measuredValues'), entities))
    devices = {x['id']: {'raw': x, 'is_gathering': False, 'room': None}
               for x in devices_list}
    nodes_list = sorted(list(filter(lambda x: x.get(
        'id') == 'status-cluster-size', entities))[0]['attributes']['nodes'])
    cols = ["deviceId", "room"] + nodes_list
    return entities


class Room(BaseModel):
    name: str
    deviceId: str


@app.post("/api/room")
def set_room(room: Room):
    global devices
    if (device := devices.get(room.deviceId)):
        device['room'] = room.name


class GatheringAction(BaseModel):
    action: str
    deviceId: str


@app.post("/api/gathering")
def set_gathering(gatheringAction: GatheringAction):
    global devices
    global train_data
    if (device := devices.get(gatheringAction.deviceId)):
        if gatheringAction.action == "append":
            df = pd.read_csv("data/room-location.csv")
            if (set(df.columns.tolist()) != set(cols)):
                raise HTTPException(
                    status_code=422, detail="Cols are different")
            device['is_gathering'] = True
            train_data = df
        if gatheringAction.action == "new":
            device['is_gathering'] = True
            os.remove("data/room-location.csv")
            d = {x: [] for x in cols}
            train_data = pd.DataFrame(data=d)
        if gatheringAction.action == "stop":
            device['is_gathering'] = False
            train_data.to_csv("data/room-location.csv", index=False)


@app.delete("/api/gathering")
def delete_gathering():
    os.remove("room-location.csv")


class PostTraining(BaseModel):
    deviceId: str
    optimize: bool


@app.post("/api/training")
def post_training(postTraining: PostTraining):
    global training_thread_instance
    training_thread_instance = threading.Thread(
        target=training_thread, args=(postTraining.deviceId, postTraining.optimize))
    training_thread_instance.start()


@app.delete("/api/training")
def delete_training():
    if training_thread_instance:
        training_thread_instance.stop()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await consumer(websocket, data)
            # await websocket.send_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Warning! Needs to be after every other handler!
app.mount("/", StaticFiles(directory="public", html=True), name="public")


async def consumer(websocket, msg_str):
    msg = json.loads(msg_str)
    if msg['type'] == 'ping':
        res = {
            'type': 'pong'
        }
        res_str = json.dumps(res)
        await websocket.send_text(res_str)


def get_prediction(model, nodes_list, msg):
    node2instanceMap = {instance2node(x): x for x in list(
        msg['entity']['measuredValues'].keys())}
    d = {x: [msg['entity']['measuredValues'][node2instanceMap[x]]['rssi']]
         for x in nodes_list}
    X = pd.DataFrame.from_dict(d)
    y_predicted = model.predict(X)
    enc2dec = {0: 'living room', 1: 'bedroom'}
    res_list = list(map(lambda x: enc2dec[x], y_predicted.tolist()))
    return res_list[0]


async def ws_client():
    global train_data
    async with websockets.connect(config['room_assistant']['ws_url']) as websocket:
        subscribe = {
            "event": "subscribeEvents",
            "data": {
                "type": "entityUpdates"
            }
        }
        subscribeStr = json.dumps(subscribe)

        await websocket.send(subscribeStr)
        async for message in websocket:
            msg = json.loads(message)
            if is_training == False and (entity := msg.get("entity")) and (device := devices.get(entity["id"])):
                y_predicted = get_prediction(model, nodes_list, msg)
                res_msg = {
                    'type': 'room',
                    'payload': {
                        'room': y_predicted,
                        'node': entity["state"],
                        'deviceId': entity["id"]
                    }
                }
                await manager.broadcast(json.dumps(res_msg))
                if device['room'] and device['is_gathering'] == True:
                    append_train_data(train_data, nodes_list,
                                      device['room'], msg)


def train_model(df, deviceId, optimize):
    df = df.loc[df['deviceId'] == deviceId]
    df['room'] = df['room'].map({'living room': 0, 'bedroom': 1})
    df = df.drop('deviceId', axis=1)

    X = df.drop('room', axis=1)
    y = df['room']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    if optimize:
        param_dist = {'n_estimators': randint(50, 500),
                      'max_depth': randint(1, 20)}

        # Create a random forest classifier
        rf_blank = RandomForestClassifier()

        # Use random search to find the best hyperparameters
        rand_search = RandomizedSearchCV(
            rf_blank, param_distributions=param_dist, n_iter=5, cv=5)

        # Fit the random search object to the data
        rand_search.fit(X_train, y_train)

        rf = rand_search.best_estimator_

        # Print the best hyperparameters
        print('Best hyperparameters:',  rand_search.best_params_)
    else:
        rf = RandomForestClassifier(n_estimators=10, max_depth=7)
        rf.fit(X_train, y_train)

    y_pred = rf.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)

    print("Accuracy:", accuracy)
    print("Precision:", precision)
    print("Recall:", recall)

    return {
        'rf': rf,
        'stats': {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall
        }
    }


async def training_thread_main(deviceId, optimize):
    global is_training
    msg = {
        'type': 'training',
        'payload': {
            'state': 'started',
            'deviceId': deviceId
        }
    }
    await manager.broadcast(json.dumps(msg))

    is_training = True
    df = pd.read_csv("data/room-location.csv")
    train_model_ret = train_model(df, deviceId, optimize)
    rf, stats = itemgetter('rf', 'stats')(train_model_ret)
    pickle.dump(rf, open('data/random_forest.pickle', "wb"))
    is_training = False

    msg = {
        'type': 'training',
        'payload': {
            'state': 'finished',
            'deviceId': deviceId,
            'stats': stats
        }
    }
    await manager.broadcast(json.dumps(msg))


def training_thread(deviceId, optimize):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(training_thread_main(deviceId, optimize))
    loop.close()


def instance2node(x):
    return x.lower().replace(' ', '-')


def find(in_list, key, val):
    return list(filter(lambda x: x.get(key) == val, in_list))


def append_train_data(train_data, nodes_list, room, in_data):
    node2instanceMap = {instance2node(x): x for x in list(
        in_data['entity']['measuredValues'].keys())}

    res = list(map(lambda x: in_data['entity']['measuredValues']
               [node2instanceMap[x]]['rssi'], nodes_list))
    data = [in_data['entity']['id'], room] + res
    train_data.loc[len(train_data)] = data


def get_model():
    return pickle.load(open('data/random_forest.pickle', "rb"))


def load_model():
    global model
    model = get_model()


@app.on_event('startup')
def initial_task():
    asyncio.create_task(ws_client())


if __name__ == "__main__":
    load_model()
    uvicorn.run(app, host="0.0.0.0", port=8000)
    # test_device_id = os.getenv('TEST_DEVICE_ID')
    # training_thread(test_device_id)
