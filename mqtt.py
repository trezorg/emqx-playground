# python -m pip install --user uvloop gmqtt

# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import argparse
import asyncio
import logging
import random
import signal
import uuid
from datetime import datetime
from functools import partial

import uvloop
from gmqtt import Client as MQTTClient, Subscription

from jwt_token import DEFAULT_ROLE, generate_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('mqtt')


NOISE_SHARED_SUBSCRIPTION = '$share/{group}/sensors/+/noise'
NOISE_TOPIC = 'sensors/{recipient_username}/noise'
PRIVATE_KEY_FILE = 'keys/private.pem'
DEFAULT_ORGANIZATION = 'sensors'
DEFAULT_TTL = 3600*24*30
MESSAGE_VERSION = '0.0.1'
DEFAULT_QOS = 2
DEFAULT_PORT = 1883
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PUBLISH_PAUSE = 3


def prepare_args():
    parser = argparse.ArgumentParser()

    subscribe_group = parser.add_argument_group('subscribe', 'sibscription parameters')
    publish_group = parser.add_argument_group('publish', 'publishing parameters')

    parser.add_argument(
        "--host",
        help="MQTT host",
        default=DEFAULT_HOST,
        type=str,
    )
    parser.add_argument(
        "-p",
        "--port",
        help="MQTT port",
        default=DEFAULT_PORT,
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
        "-ur",
        "--recipient-username",
        help="recipient username",
        type=str,
    )
    parser.add_argument(
        "-i",
        "--client-id",
        help="client id",
        type=str,
    )
    parser.add_argument(
        "-tp",
        "--topic",
        help="MQTT topic",
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
        "--clean-start",
        help="MQTT 5 clean start flag",
        action="store_true"
    )
    parser.add_argument(
        "--version",
        help="message version",
        type=str,
        default=MESSAGE_VERSION
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
    parser.add_argument(
        "-q",
        "--qos",
        help="MQTT QOS",
        default=DEFAULT_QOS,
        choices=[0, 1, 2],
        type=int,
    )
    publish_group.add_argument(
        "--publish-pause",
        help="Wait QOS 2 publish message PUBREC",
        default=DEFAULT_PUBLISH_PAUSE,
        type=int,
    )
    publish_group.add_argument(
        "--timeout",
        help="publish period",
        type=float,
        default=1
    )
    publish_group.add_argument(
        "--publish",
        help="Publish message",
        action="store_true"
    )
    publish_group.add_argument(
        "--retain",
        help="Retained message",
        action="store_true"
    )
    publish_group.add_argument(
        "--payload",
        help="MQTT message payload",
        type=str
    )
    subscribe_group.add_argument(
        "--no-local",
        help="MQTT 5 NoLocal flag. Do not get published messages in same connection",
        action="store_true"
    )
    subscribe_group.add_argument(
        "-s",
        "--shared",
        help="MQTT 5 shared subscription",
        action="store_true"
    )
    subscribe_group.add_argument(
        "-g",
        "--group",
        help="MQTT 5 shared subscription group",
        type=str
    )
    subscribe_group.add_argument(
        "--subscribe",
        help="Subscribe on topics",
        action="store_true"
    )
    args = parser.parse_args()
    return args


def check_args(args: argparse.Namespace):
    if not args.username:
        raise ValueError("username must be specified")
    if not args.client_id:
        args.client_id = args.username
    if not args.recipient_username:
        args.recipient_username = args.username
    if not args.token:
        args.token = generate_token(args)
    if not args.group:
        args.group = args.username
    parameters = vars(args)
    if args.shared:
        sub_topics = [NOISE_SHARED_SUBSCRIPTION.format(**parameters)]
    else:
        sub_topics = [NOISE_TOPIC.format(**parameters)]
    if not args.subscribe and not args.publish:
        raise ValueError("either --subscribe of --publish should be set")
    if not args.topic:
        if args.subscribe:
            args.topic = sub_topics
        if args.publish:
            args.topic = [NOISE_TOPIC.format(**parameters)]


def subscribe_topics(args: argparse.Namespace, client: MQTTClient):
    subscriptions = [Subscription(topic, qos=args.qos) for topic in args.topic]
    logger.info('Subscribing topics"%s"...', args.topic)
    client.subscribe(subscription_or_topic=subscriptions, no_local=args.no_local, content_type='json')
    logger.info('Subscribed topic "%s"', args.topic)


def on_connect(args, client: MQTTClient, flags, rc, properties):
    logger.info('Connected: Flags: %s, RC: %s, properties: %s', flags, rc, properties)
    if args.subscribe:
        subscribe_topics(args, client)


async def on_message(args, client: MQTTClient, topic, payload, qos, properties):
    logger.info(
        'Get message: Client ID: %s, Topic: %s, payload: %s, qos: %d, properties: %s',
        client._client_id,
        topic,
        payload,
        qos,
        properties,
    )
    return 0


def on_disconnect(args, client: MQTTClient, packet, exc=None):
    logger.info('Disconnected. packet: %s. Exception: %s', packet, exc)


def on_subscribe(args: argparse.Namespace, client: MQTTClient, mid, qos, properties):
    logger.info('Subscribed. Client ID: %s. Mid: %s. QOS: %s. Properties: %s', client._client_id, mid, qos, properties)


def prepare_message(args: argparse.Namespace):
    return {
        'message_id': uuid.uuid4().hex,
        'username': args.username,
        'org': args.organization,
        'time': round(1000 * datetime.utcnow().timestamp()),
        'version': args.version,
        'level': round(random.uniform(0, 1), 2),
    }


def ask_exit(event, *args):
    event.set()


async def auto_publish(args: argparse.Namespace, client: MQTTClient, event: asyncio.Event):
    while not event.is_set():
        try:
            await asyncio.wait_for(event.wait(), timeout=args.timeout)
        except asyncio.TimeoutError:
            pass
        message = args.payload or prepare_message(args)
        for topic in args.topic:
            logger.info('Publishing to topic: "%s"...', topic)
            client.publish(topic, payload=message, qos=args.qos, retain=args.retain, content_type='json')
            logger.info('Published to topic: "%s"', topic)


async def prepare_client(args) -> MQTTClient:
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    client = MQTTClient(
        args.client_id,
        clean_session=args.clean_start,
        session_expiry_interval=args.session_expiry_interval,
    )
    client.on_connect = partial(on_connect, args)
    client.on_disconnect = partial(on_disconnect, args)
    client.on_message = partial(on_message, args)
    if args.subscribe:
        client.on_subscribe = partial(on_subscribe, args)
    client.set_auth_credentials(username=args.username, password=args.token)
    logger.info('Connecting to %s:%s', args.host, args.port)
    await client.connect(host=args.host, port=args.port)
    return client


async def subscribe(args: argparse.Namespace):
    client = await prepare_client(args)
    event = asyncio.Event()

    loop = asyncio.get_event_loop()
    func = partial(ask_exit, event)
    loop.add_signal_handler(signal.SIGINT, func)
    loop.add_signal_handler(signal.SIGTERM, func)

    # asyncio.create_task(auto_publish(args=args, client=client, event=event))
    await event.wait()
    await client.disconnect()


async def publish(args: argparse.Namespace):
    client = await prepare_client(args)
    event = asyncio.Event()

    loop = asyncio.get_event_loop()
    func = partial(ask_exit, event)
    loop.add_signal_handler(signal.SIGINT, func)
    loop.add_signal_handler(signal.SIGTERM, func)

    for topic in args.topic:
        logger.info('Publish to topic: %s', topic)
        message = args.payload or prepare_message(args)
        client.publish(message_or_topic=topic, payload=message, qos=args.qos, retain=args.retain, content_type='json')
        logger.info('Published to topic: %s', topic)

    if args.qos == DEFAULT_QOS:
        logger.info('Waithing for %d seconds...', args.publish_pause)
        await asyncio.sleep(args.publish_pause)
        event.set()

    await event.wait()
    await client.disconnect()


if __name__ == "__main__":
    params = prepare_args()
    check_args(params)
    logger.info('Args: %s', vars(params))
    coro = subscribe if not params.publish else publish
    asyncio.run(coro(params))
