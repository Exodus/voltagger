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
CLIENT = boto3.client('ec2')
REGIONS = [region['RegionName'] for region in CLIENT.describe_regions()['Regions']]
for region in REGIONS:
    print('Region: {0}'.format(region))
    EC2 = boto3.resource('ec2',region)

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
                        print('Tagging: {0} ({1}) \t Attached to: {2}'.format(
                            tag['Value'], vol.volume_id, vol_instance.instance_id))
                        vol.create_tags(Tags=[tag])
                        # Tagging Snapshots as well
                        snapshots = [snap for snap in vol.snapshots.all()]
                        for snap in snapshots:
                            print('Tagging Snapshot: {0}'.format(snap.snapshot_id))
                            snap.create_tags(Tag=[tag])
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

    # To not make huge nested list comprehensions I'm dividing them into several
    # Now tagging the snapshots. Get all the instances with a 'Name' tag.
    snapvols = []
    VOLUMES_NOTEXIST = []
    owner_id = boto3.client('sts').get_caller_identity().get('Account')
    sfilter = [{'Name': 'owner-id', 'Values': [owner_id]}]
    snapshots = [snap for snap in EC2.snapshots.filter(Filters=sfilter).all()]
    for idx, snap in enumerate(snapshots):
        try:
            print('Index: {0}/{1}\r'.format(idx, len(snapshots)), end='')
            vol_instance = EC2.Instance(snap.volume.attachments[0]['InstanceId']) if any(snap.volume.attachments) else None
            if vol_instance:
                if vol_instance.tags:
                    for tag in vol_instance.tags:
                        if tag['Key'] == 'Name':
                            if snap.tags:
                                keys = []
                                for tag in snap.tags:
                                    keys.append(tag['Key'])
                                if 'Name' not in keys:
                                    print('Tagging Snapshot: {0} ({1}) \t Attached to: {2}'.format(
                                        tag['Value'], snap.snapshot_id, vol_instance.instance_id))
                                    snap.create_tags(Tags=[tag])
                            else:
                                print('Tagging Snapshot: {0} ({1}) \t Attached to: {2}'.format(
                                    tag['Value'], snap.snapshot_id, vol_instance.instance_id))
                                snap.create_tags(Tags=[tag])

        except botocore.exceptions.ClientError as e:
            if 'InvalidVolume.NotFound' in e.response['Error']['Code']:
                VOLUMES_NOTEXIST.append(snap.volume_id)
