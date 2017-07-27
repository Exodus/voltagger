#!/usr/bin/env python3
'''AWS EBS Volume Tagging.

This module will use your AWS Credentials and look for any untagged EC2
Volumes, search for the first attached EC2 Instance, and, if it has a
'Name' tag, it will replicate it to the Volume.
'''
import sys
import argparse
import boto3
import botocore.exceptions

PARSER = argparse.ArgumentParser(
    description='Tag untagged EBS volumes with the attached'
    ' instance Name tag.')
PARSER.add_argument('profile', help='The AWS Profile to use')
ARGS = PARSER.parse_args()

try:
    boto3.setup_default_session(profile_name=ARGS.profile)
except botocore.exceptions.ProfileNotFound:
    print('AWS Profile not found')
    sys.exit(1)

EC2 = boto3.resource('ec2')

# Fetch the untagged volumes
print('Fetching untagged Volumes')
VOLS = [vol for vol in EC2.volumes.all() if vol.tags is None]
print('{0} untagged volumes found'.format(len(VOLS)))
VOLUMES_UNATTACHED = []
INSTANCES_UNTAGGED = []
# If the volumes are attached, assign the Name tag of the first instance
#  they are attached to.
for idx, vol in enumerate(VOLS):
    if vol.attachments:
        vol_instance = EC2.Instance(vol.attachments[0]['InstanceId'])
        if vol_instance.tags:
            for tag in vol_instance.tags:
                if tag['Key'] == 'Name':
                    print('Tagging: {0}'.format(vol_instance.instance_id))
                    vol.create_tags(Tags=[tag])
        else:
            INSTANCES_UNTAGGED.append(vol_instance.instance_id)
    else:
        VOLUMES_UNATTACHED.append(vol.volume_id)
if INSTANCES_UNTAGGED:
    print('The following list of instance id\'s are untagged:')
    print(INSTANCES_UNTAGGED)
if VOLUMES_UNATTACHED:
    print('The following list of volume id\'s are unattached:')
    print(VOLUMES_UNATTACHED)
