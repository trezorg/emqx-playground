EQMX test platform
==================================================

Install and test
--------------------------------------------------

##### Generate public/private keys

    bash keygen.sh

##### Start eqmx cluster

    docker-compose up -d --force-recreate --remove-orphans -V

##### Install python requirements

**Required python3.6+**

    python -m pip install -U --user -r requirements.txt

##### Generate token and publish/subscribe with mosquitto client

    username=sensorsadmin
    recipient_username=1
    topic="sensors/${recipient_username}/state"
    token=$(python jwt_token.py -k keys/private.pem -u "${username}" -o 1 -r admin -t "$((3600*24*30))" 2>/dev/null)
    uri="mqtt://${username}:${token}@127.0.0.1/${topic}"
    mosquitto_pub -V mqttv5 -L "${uri}" -i "${username}_pub" -q 2 -d -c -m "test$(date)"
    mosquitto_sub -V mqttv5 -L "${uri}" -i "${username}_sub" -q 2 -d -c -C 1

##### Start python publisher, subscriber

    python mqtt.py -h
    usage: mqtt.py [-h] [--host HOST] [-p PORT] [-q {0,1,2}] [-t TOKEN] [-u USERNAME] [-st SUBSCRIBE_TOPIC [SUBSCRIBE_TOPIC ...]] [-pt PUBLISH_TOPIC [PUBLISH_TOPIC ...]] [-k PRIVATE_KEY] [-o ORGANIZATION] [-r ROLE] [--ttl TTL] [--no-local] [--clean-start]
                [--timeout TIMEOUT] [--session-expiry-interval SESSION_EXPIRY_INTERVAL]

    optional arguments:
    -h, --help            show this help message and exit
    --host HOST           MQTT host
    -p PORT, --port PORT  MQTT port
    -q {0,1,2}, --qos {0,1,2}
                            MQTT QOS
    -t TOKEN, --token TOKEN
                            JWT token
    -u USERNAME, --username USERNAME
                            username
    -st SUBSCRIBE_TOPIC [SUBSCRIBE_TOPIC ...], --subscribe-topic SUBSCRIBE_TOPIC [SUBSCRIBE_TOPIC ...]
                            MQTT subscribe topic
    -pt PUBLISH_TOPIC [PUBLISH_TOPIC ...], --publish-topic PUBLISH_TOPIC [PUBLISH_TOPIC ...]
                            MQTT publish topic
    -k PRIVATE_KEY, --private-key PRIVATE_KEY
                            RS256 private key
    -o ORGANIZATION, --organization ORGANIZATION
                            Organization ID
    -r ROLE, --role ROLE  user role
    --ttl TTL             token ttl in seconds
    --no-local            MQTT 5 NoLocal flag. Do not get published messages in same connection
    --clean-start         MQTT 5 clean start flag
    --timeout TIMEOUT     publish period
    --session-expiry-interval SESSION_EXPIRY_INTERVAL
                            Session expiry interval in seconds. If the Session Expiry Interval is absent the value 0 is used. If it is set to 0, or is absent, the Session ends when the Network Connection is closed

###### Using example

    username=1
    python mqtt.py --host 127.0.0.1 -u "${username}" --timeout 10 -q 2
