#import pydevd
#pydevd.settrace('127.0.0.1', port=9000)

import boto3, datetime, pprint, collections
from termcolor import colored
from collections import defaultdict
import sys, os

def get_running_instances():
    region='us-east-1'
    ec2 = boto3.resource('ec2', region_name=region)
    instances = ec2.instances.filter(
    Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    running_instances = {}
    for instance in instances:
        running_instances[instance.id] = instance
    return running_instances
    
def get_instance_statuses():
    
    # {'InstanceState': {'Code': 16, 'Name': 'running'}, 
    # 'InstanceStatus': {'Details': [{'Name': 'reachability', 'Status': 'passed'}], 'Status': 'ok'}, 
    #'SystemStatus': {'Details': [{'Name': 'reachability', 'Status': 'passed'}], 'Status': 'ok'}, 
    #'InstanceId': 'i-019c4789ecc6a5eb1', 
    #'AvailabilityZone': 'us-east-1c'}
    
    region='us-east-1'
    ec2 = boto3.resource('ec2', region_name=region)
    instance_status_dict = {}
    for status in ec2.meta.client.describe_instance_status()['InstanceStatuses']:
        instance_status_dict[status['InstanceId']] = status
        
    #     instance_status_dict['i-035b08b8a58bd5476']
    #     {'AvailabilityZone': 'us-east-1b', 'InstanceStatus': {'Details': [{'Name': 'reachability', 'Status': 'passed'}], 'Status': 'ok'}, 'SystemStatus': {'Details': [{'Name': 'reachability', 'Status': 'passed'}], 'Status': 'ok'}, 'InstanceId': 'i-035b08b8a58bd5476', 'InstanceState': {'Code': 16, 'Name': 'running'}}
    #     >>> instance_status_dict['i-035b08b8a58bd5476']['InstanceStatus']
    #     {'Details': [{'Name': 'reachability', 'Status': 'passed'}], 'Status': 'ok'}
    #     >>> instance_status_dict['i-035b08b8a58bd5476']['InstanceStatus']['Status']
    #     'ok'
    return instance_status_dict
def get_instance_status(state):    
    region='us-east-1'
    session = boto3.Session()
    ec2 = session.resource('ec2', region_name=region)
    if ( state == 'running' ):
        instances = ec2.instances.filter( Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    if ( state == 'not running' ):
        instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['stopped', 'terminated']}])

    instance_dict = {}
    instance_dict = defaultdict( lambda: '-', instance_dict ) 
    for instance in instances:
        instance_dict[instance.private_dns_name] = { 'id':instance.id,
                                   'type':instance.instance_type,
                                   'private_ip':instance.private_ip_address,
                                   'private_dns':instance.private_dns_name,
                                   'state':instance.state['Name'] if instance.state['Name'] is not None else '-',
                                   'state_reason':instance.state_reason if instance.state_reason is not None else '-',
                                   'state_transition_reason':instance.state_transition_reason if instance.state_transition_reason is not None else '-',
                                   'tags': instance.tags
        }
    return instance_dict

def get_instances(state):
    region='us-east-1'
    session = boto3.Session()
    ec2 = session.resource('ec2', region_name=region)
    if ( state == 'running' ):
        instances = ec2.instances.filter( Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    if ( state == 'not running' ):
        instances = ec2.instances.filter(Filters=[{'Name': 'instance-state-name', 'Values': ['stopped', 'terminated']}])

    instance_dict = {}
    instance_dict = defaultdict( lambda: '-', instance_dict ) 
    for instance in instances:
        instance_dict[instance.private_dns_name] = { 'id':instance.id,
                                   'type':instance.instance_type,
                                   'private_ip':instance.private_ip_address,
                                   'private_dns':instance.private_dns_name,
                                   'state':instance.state['Name'] if instance.state['Name'] is not None else '-',
                                   'state_reason':instance.state_reason if instance.state_reason is not None else '-',
                                   'state_transition_reason':instance.state_transition_reason if instance.state_transition_reason is not None else '-',
                                   'tag': ''.join( str(tag) for tag in str(instance.tags) )
        }
    return instance_dict

def get_metrics_elb(asset):
    client1 = boto3.client('elb')
    response1 = client1.describe_instance_health(
        LoadBalancerName=asset,

    )

    for instancestates in response1['InstanceStates']:
        if instancestates['State'] == 'InService':
            ins_state = colored(instancestates['State'],'green')
        else:
            ins_state = colored(instancestates['State'],'red')

        print('Instance Id: ', instancestates['InstanceId'], '| Instance State: ', ins_state)



def get_metrics_ec2(asset):
    client = boto3.client('cloudwatch')
    response = client.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        StartTime=datetime.datetime.utcnow()-datetime.timedelta(seconds=7200),
        EndTime=datetime.datetime.utcnow(),
        Period=300,
        Dimensions=[
            {
                'Name': 'InstanceId',
                'Value': asset
            },
        ],
        Statistics=['Average'],
        Unit='Percent'
    )
    newlist=response['Datapoints']
    newlist = sorted(newlist, key=lambda k: k['Timestamp'])
    if len(newlist) > 0:
        return newlist[-1]['Average']


def asg():
    client = boto3.client('autoscaling')
    #response = client.describe_auto_scaling_groups()
    #ASGs = response['AutoScalingGroups']

    paginator = client.get_paginator('describe_auto_scaling_groups')
    groups = paginator.paginate().build_full_result()
    ASGs = groups['AutoScalingGroups']

    healthy = 0
    unhealthy = 0
    for ASG in ASGs:
        print('#'*150)
        #print(colored(ASG['AutoScalingGroupName'],'red'))
        print(ASG['AutoScalingGroupName'])
        print('ASG Min Size: ', ASG['MinSize'])
        print('ASG Max Size: ', ASG['MaxSize'])
        print('ASG Desired Size: ', ASG['DesiredCapacity'])
        print('ASG instance count: ', len(ASG['Instances']))
        print('#'*150)

        for instance in ASG['Instances']:
            if instance['HealthStatus'] == 'Healthy':
                ins_health = colored('Healthy', 'green')
                ins_cpu = get_metrics_ec2(instance['InstanceId'])
                if ins_cpu and ins_cpu > 5:
                    ins_cpu = colored(ins_cpu, 'red')
                else:
                    ins_cpu = colored(ins_cpu, 'green')
                healthy += 1
            else:
                ins_health = colored(instance['HealthStatus'], 'red')
                unhealthy += 1
            if instance['LifecycleState'] == 'InService':
                ins_life = colored(instance['LifecycleState'], 'green')
            else:
                ins_life = colored(instance['LifecycleState'], 'red')

            print('Instance Id: ', colored(instance['InstanceId'],'yellow'), '| Instance Zone:', colored(instance['AvailabilityZone'],'yellow'), ' | Instance LifecycleState: ', ins_life, '| Instance Status: ', ins_health, '| Instance Cpu: ', ins_cpu)

        print('#'*150)
        print('ASG Healthy Instance Count: ', colored(healthy, "green"))
        print('ASG Unhealthy Instance Count: ', colored(unhealthy, "red"))

        for ELB in (ASG['LoadBalancerNames']):
            print('#'*150)
            print('ELB Name: ', ELB)
            print('#'*150)
            get_metrics_elb(ELB)
            print('#'*150)


if __name__ == "__main__":
    try:
        print( "Arg: " + sys.argv[1] )
        os.system('exit') 
        status = sys.argv[1]
        #instance_dict = get_instance_statuses()
        #instance_dict = get_instances()
        instance_dict = get_instances(status)
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(instance_dict)
        #input ("Get ASG info")
        #asg()
    except Exception as err:
        print(err)
