EQMX test platform
==================================================

Install and test
--------------------------------------------------

Generate public/private keys
--------------------------------------------------

    bash keygen.sh

Start eqmx cluster
--------------------------------------------------

    docker-compose up -d --force-recreate --remove-orphans -V

Install python requirements
--------------------------------------------------


**Required python3.6+**

    python -m pip install -U --user -r requirements.txt

Generate token and publish/subscribe with mosquitto client
--------------------------------------------------

    username=sensorsadmin
    recipient_username=1
    topic="sensors/${recipient_username}/state"
    token=$(python jwt_token.py -k keys/private.pem -u "${username}" -o 1 -r admin -t "$((3600*24*30))" 2>/dev/null)
    uri="mqtt://${username}:${token}@127.0.0.1/${topic}"
    mosquitto_pub -V mqttv5 -L "${uri}" -i "${username}_pub" -q 2 -d -c -m "test$(date)"
    mosquitto_sub -V mqttv5 -L "${uri}" -i "${username}_sub" -q 2 -d -c -C 1

Start python publisher, subscriber
--------------------------------------------------

    python mqtt.py -h

Using example
--------------------------------------------------

    username=1
    python mqtt.py -u "${username}" --timeout 10 -q 2

Shared subscription
--------------------------------------------------

Subscribe
--------------------------------------------------

    username=sensorsadmin
    client_id1=1
    client_id2=2
    python mqtt.py -u "${username}" -i "${client_id1}" -s --no-publish -q 2 && \
    python mqtt.py -u "${username}" -i "${client_id2}" -s --no-publish -q 2

Publish
--------------------------------------------------

    username=sensorsadmin
    recipient_username=1
    topic="sensors/${recipient_username}/state"
    token=$(python jwt_token.py -k keys/private.pem -u "${username}" -o 1 -r admin -t "$((3600*24*30))" 2>/dev/null)
    uri="mqtt://${username}:${token}@127.0.0.1/${topic}"
    count=0
    while true; do
        count=$((count+1))
        mosquitto_pub -V mqttv5 -L "${uri}" -i "${username}_pub" -q 2 -d -c -m "test${count}"
        sleep 1
    done
