#!/usr/bin/env python

# python -m pip install --user -U pyjwt

# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import argparse
import datetime
import logging
import time
from dataclasses import asdict, dataclass

import jwt

DEFAULT_TTL = 60 * 10
DEFAULT_ROLE = 'sensor'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Payload:
    username: str
    org: str
    role: str
    exp: int
    iat: int


def prepare_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-k",
        "--private-key",
        help="RS256 private key",
        type=str,
    )
    parser.add_argument(
        "-u",
        "--username",
        help="username",
        type=str,
    )
    parser.add_argument(
        "-o",
        "--organization",
        help="Organization ID",
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
        "-t",
        "--ttl",
        help="token ttl in seconds",
        type=int,
        default=DEFAULT_TTL,
    )
    args = parser.parse_args()
    return args


def check_args(args):
    if not args.private_key:
        raise ValueError("RS256 private key must be specified")
    if not args.username:
        raise ValueError("username must be specified")
    if not args.organization:
        raise ValueError("Organization ID must be specified")


def read_key(filename) -> str:
    with open(filename, 'r') as fld:
        return fld.read()


def from_timestamp(timestamp: int):
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def prepare_payload(args: dict) -> Payload:
    iat = int(time.time())
    exp = iat + args['ttl']
    logger.info('Token IAT: %s', from_timestamp(iat))
    logger.info('Token EXP: %s', from_timestamp(exp))
    return Payload(
        username=args['username'],
        org=args['organization'],
        role=args['role'],
        iat=iat,
        exp=exp,
    )


def prepare_token(payload: dict, secret: str):
    logger.info('Payload: %s', payload)
    return jwt.encode(payload, secret, algorithm='RS256')


def generate_token(args: argparse.Namespace) -> str:
    payload = prepare_payload(vars(args))
    key = read_key(args.private_key)
    return prepare_token(asdict(payload), key)


def main():
    args = prepare_args()
    check_args(args)
    print(generate_token(args))


if __name__ == '__main__':
    main()
