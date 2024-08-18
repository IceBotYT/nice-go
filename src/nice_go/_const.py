"""Constants for Nice G.O. API."""

import json

ENDPOINTS_URL = "https://prod.api.nortek-smartcontrol.com/endpoints"
BARRIER_STATUS = ["STATIONARY", "OPENING", "CLOSING"]
REQUEST_TEMPLATES = {
    "get_all_barriers": {
        "operationName": "devicesListAll",
        "variables": {"nextToken": None},
        "query": "query devicesListAll($nextToken: String) {\n  devicesListAll(nextToken: $nextToken) {\n    devices {\n      ...deviceFields\n      __typename\n    }\n    nextToken\n    __typename\n  }\n}\n\nfragment deviceFields on Device {\n  id\n  type\n  controlLevel\n  attr {\n    key\n    value\n    __typename\n  }\n  state {\n    ...deviceStateFields\n    __typename\n  }\n  groupIds\n  __typename\n}\n\nfragment deviceStateFields on DeviceState {\n  deviceId\n  desired\n  reported\n  timestamp\n  version\n  connectionState {\n    connected\n    updatedTimestamp\n    __typename\n  }\n  version\n  __typename\n}\n",  # noqa: E501
    },
    "open_barrier": {
        "operationName": "devicesControl",
        "variables": {
            "deviceId": "$barrier_id",
            "payload": {"target": "B", "action": 1},
        },
        "query": "mutation devicesControl($deviceId: ID!, $payload: ControlPayload!) {\n  devicesControl(deviceId: $deviceId, payload: $payload)\n}\n",  # noqa: E501
    },
    "close_barrier": {
        "operationName": "devicesControl",
        "variables": {
            "deviceId": "$barrier_id",
            "payload": {"target": "B", "action": 0},
        },
        "query": "mutation devicesControl($deviceId: ID!, $payload: ControlPayload!) {\n  devicesControl(deviceId: $deviceId, payload: $payload)\n}\n",  # noqa: E501
    },
    "light_on": {
        "operationName": "devicesControl",
        "variables": {
            "deviceId": "$barrier_id",
            "payload": {"target": "L", "action": 1},
        },
        "query": "mutation devicesControl($deviceId: ID!, $payload: ControlPayload!) {\n  devicesControl(deviceId: $deviceId, payload: $payload)\n}\n",  # noqa: E501
    },
    "light_off": {
        "operationName": "devicesControl",
        "variables": {
            "deviceId": "$barrier_id",
            "payload": {"target": "L", "action": 0},
        },
        "query": "mutation devicesControl($deviceId: ID!, $payload: ControlPayload!) {\n  devicesControl(deviceId: $deviceId, payload: $payload)\n}\n",  # noqa: E501
    },
    "subscribe": {
        "id": "$uuid",
        "payload": {
            "data": json.dumps(
                {
                    "query": "subscription devicesStatesUpdateFeed($receiver: ID!) {\n  devicesStatesUpdateFeed(receiver: $receiver) {\n    receiver\n    item {\n      ...deviceStateFields\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment deviceStateFields on DeviceState {\n  deviceId\n  desired\n  reported\n  timestamp\n  version\n  connectionState {\n    connected\n    updatedTimestamp\n    __typename\n  }\n  version\n  __typename\n}\n",  # noqa: E501
                    "variables": {"receiver": "$receiver_id"},
                },
            ),
            "extensions": {
                "authorization": {
                    "Authorization": "$id_token",
                    "host": "$host",
                    "x-amz-user-agent": "aws-amplify/2.0.8 js",
                },
            },
        },
        "type": "start",
    },
    "unsubscribe": {"id": "$id", "type": "stop"},
    "vacation_mode_on": {
        "operationName": "devicesStatesUpdate",
        "variables": {
            "deviceId": "$barrier_id",
            "state": '{"vcnMode": true}',
        },
        "query": "mutation devicesStatesUpdate($deviceId: ID!, $state: AWSJSON!) {\n  devicesStatesUpdate(deviceId: $deviceId, state: $state)\n}\n",  # noqa: E501
    },
    "vacation_mode_off": {
        "operationName": "devicesStatesUpdate",
        "variables": {
            "deviceId": "$barrier_id",
            "state": '{"vcnMode": false}',
        },
        "query": "mutation devicesStatesUpdate($deviceId: ID!, $state: AWSJSON!) {\n  devicesStatesUpdate(deviceId: $deviceId, state: $state)\n}\n",  # noqa: E501
    },
    "event_subscribe": {
        "id": "$uuid",
        "payload": {
            "data": json.dumps(
                {
                    "query": "subscription eventsFeed($receiver: ID!) {\n  eventsFeed(receiver: $receiver) {\n    receiver\n    item {\n      ...eventFields\n      __typename\n    }\n    __typename\n  }\n}\n\nfragment eventFields on Event {\n  deviceId\n  timestamp\n  eventId\n  organizationId\n  updatedTimestamp\n  type\n  eventState\n  severity\n  sensorName\n  sensorValue\n  metadata\n  __typename\n}\n",  # noqa: E501
                    "variables": {
                        "receiver": "$receiver_id",
                    },
                },
            ),
            "extensions": {
                "authorization": {
                    "Authorization": "$id_token",
                    "host": "$host",
                    "x-amz-user-agent": "aws-amplify/2.0.8 react-native",
                },
            },
        },
        "type": "start",
    },
}
