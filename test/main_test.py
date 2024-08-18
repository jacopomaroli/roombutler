import json
import os
import pandas as pd

from roombutler.main import get_model, get_prediction, append_train_data, instance2node

df = pd.read_csv("data/room-location.csv")
nodes_list = ["bedroom", "living-room", "living-room-2"]
cols = ["deviceId", "room"] + nodes_list
living_room_payload_str = '{"entity":{"attributes":{"distance":2.6,"lastUpdatedAt":"2023-04-03T20:54:11.711Z"},"id":"ble-123456789abc","name":"Device Room Presence","distributed":true,"stateLocked":true,"distances":{"Living Room":{"lastUpdatedAt":"2023-04-03T20:54:11.711Z","distance":2.6,"outOfRange":false},"Bedroom":{"lastUpdatedAt":"2023-04-02T00:12:30.276Z","distance":6.2,"outOfRange":false},"Living Room 2":{"lastUpdatedAt":"2023-04-02T18:10:48.368Z","distance":3.5,"outOfRange":false},"Bedroom":{"lastUpdatedAt":"2023-04-03T14:51:17.594Z","distance":9.7,"outOfRange":false}},"timeout":10,"measuredValues":{"Living Room":{"rssi":-67.17780860008281,"measuredPower":-59},"Bedroom":{"rssi":-75.62082129474952,"measuredPower":-59},"Living Room 2":{"rssi":-70.08624261953008,"measuredPower":-59},"Bedroom":{"rssi":-80.23188706292018,"measuredPower":-59}},"state":"Living Room"},"diff":[{"path":"/measuredValues/Living Room","oldValue":{"rssi":-67.09447516174505,"measuredPower":-59},"newValue":{"rssi":-67.17780860008281,"measuredPower":-59}},{"path":"/distances/Living Room","oldValue":{"lastUpdatedAt":"2023-04-03T20:54:09.782Z","distance":2.5,"outOfRange":false},"newValue":{"lastUpdatedAt":"2023-04-03T20:54:11.711Z","distance":2.6,"outOfRange":false}},{"path":"/attributes/distance","oldValue":2.5,"newValue":2.6},{"path":"/attributes/lastUpdatedAt","oldValue":"2023-04-03T20:54:09.782Z","newValue":"2023-04-03T20:54:11.711Z"}],"hasAuthority":true}'
bedroom_payload_str = '{"entity":{"attributes":{"distance":3.2,"lastUpdatedAt":"2023-04-03T21:17:46.464Z"},"id":"ble-123456789abc","name":"Device Room Presence","distributed":true,"stateLocked":true,"distances":{"Living Room":{"lastUpdatedAt":"2023-04-03T21:16:22.332Z","distance":2.4,"outOfRange":false},"Bedroom":{"lastUpdatedAt":"2023-04-02T00:12:30.276Z","distance":6.2,"outOfRange":false},"Living Room 2":{"lastUpdatedAt":"2023-04-03T21:16:47.549Z","distance":2.9,"outOfRange":false},"Bedroom":{"lastUpdatedAt":"2023-04-03T21:17:46.464Z","distance":3.2,"outOfRange":false}},"timeout":10,"measuredValues":{"Living Room":{"rssi":-66.54694261135968,"measuredPower":-59},"Bedroom":{"rssi":-75.62082129474952,"measuredPower":-59},"Living Room 2":{"rssi":-68.41970965040754,"measuredPower":-59},"Bedroom":{"rssi":-69.2339729581378,"measuredPower":-59}},"state":"Bedroom"},"diff":[{"path":"/measuredValues/Bedroom","oldValue":{"rssi":-69.38189095352912,"measuredPower":-59},"newValue":{"rssi":-69.2339729581378,"measuredPower":-59}},{"path":"/distances/Bedroom","oldValue":{"lastUpdatedAt":"2023-04-03T21:17:45.524Z","distance":3.3,"outOfRange":false},"newValue":{"lastUpdatedAt":"2023-04-03T21:17:46.464Z","distance":3.2,"outOfRange":false}},{"path":"/attributes/distance","oldValue":3.3,"newValue":3.2},{"path":"/attributes/lastUpdatedAt","oldValue":"2023-04-03T21:17:45.524Z","newValue":"2023-04-03T21:17:46.464Z"}],"hasAuthority":false}'
living_room_payload = json.loads(living_room_payload_str)
living_room_payload['entity']['id'] = os.getenv('TEST_DEVICE_ID')
bedroom_payload = json.loads(bedroom_payload_str)
bedroom_payload['entity']['id'] = os.getenv('TEST_DEVICE_ID')


def test_get_prediction_bedroom():
    model = get_model()
    res = get_prediction(model, nodes_list, bedroom_payload)
    assert res == 'bedroom'


def test_get_prediction_living_room():
    model = get_model()
    res = get_prediction(model, nodes_list, bedroom_payload)
    assert res == 'living room'


def test_get_prediction_raw_bedroom():
    model = get_model()
    df_room = df.loc[df['room'] == 'bedroom']
    X = df_room.sample(n=1).drop(['deviceId', 'room'], axis=1)
    y_predicted = model.predict(X)
    enc2dec = {0: 'living room', 1: 'bedroom'}
    res_list = list(map(lambda x: enc2dec[x], y_predicted.tolist()))
    res = res_list[0]
    assert res == 'bedroom'


def test_get_prediction_raw_living_room():
    model = get_model()
    df_room = df.loc[df['room'] == 'living room']
    X = df_room.sample(n=1).drop(['deviceId', 'room'], axis=1)
    y_predicted = model.predict(X)
    enc2dec = {0: 'living room', 1: 'bedroom'}
    res_list = list(map(lambda x: enc2dec[x], y_predicted.tolist()))
    res = res_list[0]
    assert res == 'living room'


def test_append_train_data():
    d = {x: [] for x in cols}
    train_data = pd.DataFrame(data=d)
    node2instanceMap = {instance2node(x): x for x in list(
        living_room_payload['entity']['measuredValues'].keys())}
    expected_d = {
        'deviceId': [living_room_payload['entity']['id']],
        'room': ['living room']
    }
    expected_d.update({x: [living_room_payload['entity']['measuredValues'][node2instanceMap[x]]['rssi']]
                       for x in nodes_list})
    expected_df = pd.DataFrame.from_dict(expected_d)
    append_train_data(train_data, nodes_list,
                      "living room", living_room_payload)
    assert train_data.equals(expected_df)
