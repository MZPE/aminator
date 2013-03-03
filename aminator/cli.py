# -*- coding: utf-8 -*-

#
#
#  Copyright 2013 Netflix, Inc.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
#


import argparse
import logging
import sys
import urllib
from datetime import datetime

from aminator.clouds.ec2.instanceinfo import this_instance
from aminator.clouds.ec2.core import ec2connection
from aminator.core import AminateRequest
from aminator.utils import pid
from aminator.config import config

log = logging.getLogger(__name__)

argparser = argparse.ArgumentParser('AMInator: provision a launchable VM image')


def logging_init(logfile, log_boto=False):
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter('%(asctime)s - %(message)s', '%F %T'))
    console.setLevel(logging.INFO)

    details = logging.FileHandler("{0}/{1}".format(config.log_dir, logfile))
    details.setFormatter(logging.Formatter('%(asctime)s %(name)s: %(levelname)s: %(message)s', '%F %T'))
    details.setLevel(logging.DEBUG)

    # CLI module will spew to stdout
    log.addHandler(console)
    logging.getLogger('aminator.core').addHandler(console)

    # hook up the rest to logfile
    logging.getLogger('aminator').addHandler(details)
    # crank it up
    logging.getLogger('aminator').setLevel(logging.DEBUG)
    log.root.setLevel(logging.DEBUG)

    if config.boto_log_dir and log_boto:
        if not os.path.exists(config.boto_log_dir):
            return
        boto_details = logging.FileHandler("{}/boto-{}".format(config.boto_log_dir, logfile))
        boto_details.setFormatter(details.formatter)
        boto_details.setLevel(logging.DEBUG)
        logging.getLogger('boto').addHandler(boto_details)


def argparse_init():
    """
    Works against the module-level argparser binding
    """
    required = argparser.add_argument_group('Required', 'Required arguments')
    required.add_argument('-b', dest='base_ami_name', required=True,
                          help='The name of base AMI on which to build')
    required.add_argument('-p', dest='pkg', required=True,
                          help='Name of package to install')

    optional = argparser.add_argument_group('Optional', 'Optional arguments')
    optional.add_argument('-n', dest='name',
                          help='name of resultant AMI (default package_name-version-release-arch-yyyymmddHHMM-ebs)')
    optional.add_argument('-s', dest='suffix', help='suffix of ami name, (default yyyymmddHHMM)')
    optional.add_argument('-c', dest='creator', default='aminator',
                          help='the name of the user invoking aminate, resultant AMI will receive a creator tag w/ this user')
    optional.add_argument('-B', dest='logboto', default=False,
                          help='log boto debug logs. See aminator.config.__doc__')
    # TODO: implement!
    """
    optional.add_argument('-r', dest='regions', default=None,
                          help='comma delmitted list of regions to copy resultant AMI (unimplemented)')
    """


def run():
    argparse_init()

    args = argparser.parse_args()

    base_ami_name = args.base_ami_name
    pkg = args.pkg
    creator = args.creator
    ami_name = args.name
    ami_suffix = args.suffix
    if ami_suffix is None:
        ami_suffix = datetime.utcnow().strftime('%Y%m%d%H%M')

    detailed_logfile = "{}-{}.log".format(pkg, ami_suffix)

    logging_init(detailed_logfile, args.logboto)

    log.info('creator    = {}'.format(creator))
    log.info('pkg        = {}'.format(pkg))
    if ami_name:
        log.info('ami_name   = {}'.format(ami_name))
    log.info('ami_suffix = {}'.format(ami_suffix))

    if config.log_url_prefix:
        log_details_url = config.log_url_prefix.format(this_instance.public_dns_name, detailed_logfile)
        log.info('Detailed logs: {}'.format(log_details_url))

    ec2 = ec2connection()
    try:
        log.info('looking up base AMI named {}'.format(base_ami_name))
        baseami = ec2.get_all_images(filters={'name': base_ami_name})[0]
    except IndexError:
        log.error('could not locate the base AMI named {}'.format(base_ami_name))
        sys.exit(1)

    aminate_request = AminateRequest(pkg, baseami, ami_suffix, creator, ami_name=ami_name)
    if not aminate_request.aminate():
        sys.exit(1)
    return(sys.exit(0))
