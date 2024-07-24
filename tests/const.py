import json

GET_ALL_BARRIERS_RESPONSE = {
    "data": {
        "devicesListAll": {
            "devices": [
                {
                    "state": {
                        "connectionState": {
                            "connected": True,
                            "updatedTimestamp": "1234567890",
                        },
                        "deviceId": "test_id",
                        "desired": json.dumps({"test": "value"}),
                        "reported": json.dumps({"test": "value"}),
                        "timestamp": "1234567890",
                        "version": 1,
                    },
                    "id": "test_id",
                    "type": "test_type",
                    "controlLevel": "test_control_level",
                    "attr": [{"key": "test_key", "value": "test_value"}],
                },
            ],
        },
    },
}

GET_ALL_BARRIERS_RESPONSE_NO_CONNECTION_STATE = {
    "data": {
        "devicesListAll": {
            "devices": [
                {
                    "state": {
                        "connectionState": None,
                        "deviceId": "test_id",
                        "desired": json.dumps({"test": "value"}),
                        "reported": json.dumps({"test": "value"}),
                        "timestamp": "1234567890",
                        "version": 1,
                    },
                    "id": "test_id",
                    "type": "test_type",
                    "controlLevel": "test_control_level",
                    "attr": [{"key": "test_key", "value": "test_value"}],
                },
            ],
        },
    },
}
