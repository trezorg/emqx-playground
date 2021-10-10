# python -m pip install --user uvloop gmqtt

# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import argparse
import asyncio
from datetime import datetime
from functools import partial
import logging
import uuid
import signal

import uvloop
from gmqtt import Client as MQTTClient

from jwt_token import (
    DEFAULT_ROLE,
    generate_token,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('mqtt')


STATE_TOPIC = 'sensors/{username}/state'
NOISE_TOPIC = 'sensors/{username}/noise'
PRIVATE_KEY_FILE = 'keys/private.pem'
DEFAULT_ORGANIZATION = 'sensors'
DEFAULT_TTL = 3600*24*30


def prepare_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        help="MQTT host",
        default='127.0.0.1',
        type=str,
    )
    parser.add_argument(
        "-p",
        "--port",
        help="MQTT port",
        default=1883,
        type=int,
    )
    parser.add_argument(
        "-q",
        "--qos",
        help="MQTT QOS",
        default=2,
        choices=[0, 1, 2],
        type=int,
    )
    parser.add_argument(
        "-t",
        "--token",
        help="JWT token",
        type=str,
    )
    parser.add_argument(
        "-u",
        "--username",
        help="username",
        type=str,
    )
    parser.add_argument(
        "-st",
        "--subscribe-topic",
        help="MQTT subscribe topic",
        type=str,
        nargs='+',
    )
    parser.add_argument(
        "-pt",
        "--publish-topic",
        help="MQTT publish topic",
        type=str,
        nargs='+',
    )
    parser.add_argument(
        "-k",
        "--private-key",
        help="RS256 private key",
        default=PRIVATE_KEY_FILE,
        type=str,
    )
    parser.add_argument(
        "-o",
        "--organization",
        help="Organization ID",
        default=DEFAULT_ORGANIZATION,
        type=str,
    )
    parser.add_argument(
        "-r",
        "--role",
        help="user role",
        type=str,
        default=DEFAULT_ROLE,
    )
    parser.add_argument(
        "--ttl",
        help="token ttl in seconds",
        type=int,
        default=DEFAULT_TTL,
    )
    parser.add_argument(
        "--no-local",
        help="MQTT 5 NoLocal flag. Do not get published messages in same connection",
        action="store_true"
    )
    parser.add_argument(
        "--clean-start",
        help="MQTT 5 clean start flag",
        action="store_true"
    )
    parser.add_argument(
        "--timeout",
        help="publish period",
        type=float,
        default=1
    )
    parser.add_argument(
        "--session-expiry-interval",
        help=(
            "Session expiry interval in seconds. "
            "If the Session Expiry Interval is absent the value 0 is used. "
            "If it is set to 0, or is absent, the Session ends when the Network Connection is closed"
        ),
        type=int,
        default=0xFFFFFFFF,
    )
    args = parser.parse_args()
    return args


def check_args(args: argparse.Namespace):
    if not args.username:
        raise ValueError("username must be specified")
    if not args.token:
        args.token = generate_token(args)
    parameters = vars(args)
    topics = [STATE_TOPIC.format(**parameters), NOISE_TOPIC.format(**parameters)]
    if not args.subscribe_topic:
        args.subscribe_topic = topics
    if not args.publish_topic:
        args.publish_topic = topics[1:]


def on_connect(args, client: MQTTClient, flags, rc, properties):
    logger.info('Connected: Flags: %s, RC: %s, properties: %s', flags, rc, properties)
    for topic in args.subscribe_topic:
        client.subscribe(topic, qos=args.qos, no_local=args.no_local, content_type='json')


def on_message(args, client, topic, payload, qos, properties):
    logger.info('Get message: Topic: %s, payload: %s', topic, payload)


def on_disconnect(args, client, packet, exc=None):
    logger.info('Disconnected. packet: %s. Exception: %s', packet, exc)


def on_subscribe(args: argparse.Namespace, client, mid, qos, properties):
    logger.info('Subscribed. Mid: %s. QOS: %s. Properties: %s', mid, qos, properties)


def prepare_message(args: argparse.Namespace):
    return {
        'message_id': uuid.uuid4().hex,
        'username': args.username,
        'time': datetime.now().isoformat(),
    }


def ask_exit(event, *args):
    event.set()


async def publish(args: argparse.Namespace, client: MQTTClient, event: asyncio.Event):
    while not event.is_set():
        try:
            await asyncio.wait_for(event.wait(), timeout=args.timeout)
        except asyncio.TimeoutError:
            pass
        for topic in args.publish_topic:
            logger.info('Publish to topic: %s', topic)
            client.publish(topic, payload=prepare_message(args), qos=args.qos, content_type='json')


async def start(args):
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    client = MQTTClient(
        args.username,
        clean_session=args.clean_start,
        session_expiry_interval=args.session_expiry_interval
    )
    client.on_connect = partial(on_connect, args)
    client.on_message = partial(on_message, args)
    client.on_disconnect = partial(on_disconnect, args)
    client.on_subscribe = partial(on_subscribe, args)

    event = asyncio.Event()

    loop = asyncio.get_event_loop()
    func = partial(ask_exit, event)
    loop.add_signal_handler(signal.SIGINT, func)
    loop.add_signal_handler(signal.SIGTERM, func)

    client.set_auth_credentials(username=args.username, password=args.token)
    await client.connect(host=args.host, port=args.port)
    asyncio.create_task(publish(args=args, client=client, event=event))
    await event.wait()
    await client.disconnect()


if __name__ == "__main__":
    params = prepare_args()
    check_args(params)
    logger.info('Args: %s', vars(params))
    asyncio.run(start(params))
