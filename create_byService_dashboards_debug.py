import pydevd
pydevd.settrace('127.0.0.1', port=9000)

import boto3, os, glob, json
from os import chdir
import delete_dashboards_by_prefix
from delete_dashboards_by_prefix import delete_dashboards_by_prefix
import instance_prod_arg 
from instance_prod_arg import get_instance_status
import copy


dashboard_home='BIN_HOME'
chdir( dashboard_home )
dashboard_template= str( dashboard_home + "/instance_dashboard_src" )
dashboard_out = ''

prefix='DevOps-Healthy-Instances'
for board in glob.glob( str( prefix + ".dashboard" )):
    print( "Removing existing dashboards .." )
    os.remove( board )    

delete_dashboards_by_prefix( prefix )

session = boto3.Session()
region='AWS_REGION'
ec2 = session.resource('ec2', region_name=region)

healthy_instances =  ec2.instances.filter( Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
unhealthy_instances =  ec2.instances.filter( Filters=[{'Name': 'instance-state-name', 'Values': ['stopped', 'terminated']}])

# load template 
first_time=True
template = open( dashboard_template, 'r' )
template_data = template.read()
json_data = json.loads( template_data )
metric_name=''

instances_by_service = {}

# split the instances into service buckets
for instance in healthy_instances:
    for dtag in instance.tags:
        if ( dtag ['Key'] == 'server-group' ):
            server_group_name = dtag['Value']
            break
        else:
            server_group_name = 'None'
    if ( server_group_name not in instances_by_service.keys() ):
        instances_by_service[server_group_name] = [instance]
    else:
        instances_by_service[server_group_name].append(instance)

asg_name = 'None'
# for each bucket, append instance data to the widget

first_time = True

    # We get the metrics title from server_group_name ( service_key )
for service_group in instances_by_service.keys():
    json_data = json.loads( template_data )
    for widget in json_data['widgets']:
        copy_widget = copy.copy(widget)
        metrics_array = copy_widget['properties']['metrics']
        metric_name = metrics_array[0][1]
        for instance_obj in instances_by_service[service_group]:
            
            instance_id=instance_obj.id
            
            for dtag in instance_obj.tags:
                if ( dtag ['Key'] == 'aws:cloudformation:stack-name' ):
                    instance_stack_name = dtag['Value']
                    break
                else:
                    instance_stack_name = 'None'
                    
            for dtag in instance_obj.tags:
                if ( dtag ['Key'] == 'aws:autoscaling:groupName' ):
                    asg_name = dtag['Value']
                    break
                else:
                    asg_name = 'None'       
  
            if ( first_time ):
                metrics_item = metrics_array[0]
                metrics_item[3] = instance_id
                metrics_array[0] = metrics_item
                first_time=False
            else:
                append_metrics_item = copy.copy(metrics_array[0])
                append_metrics_item[3] = instance_id
                metrics_array.append( append_metrics_item )       
                               
        title_attribute = str(widget['properties']['title'])
        # split the title into three, 
        elements = title_attribute.split()
        title_attribute = title_attribute.replace(elements[0], str(service_group))
        title_attribute = title_attribute.replace(elements[1], str(asg_name))
        widget['properties']['title'] = title_attribute
        title_attribute = ''
        metrics_array = []
        metrics_item = []
        # reload json
        print ( "ec2 Instance metric added for " + metric_name + " " + service_group )
        first_time = True

        
    print( "All widgets updated for " + service_group )
    dashboard_out = str( prefix + "_" + service_group + ".dashboard" )
    out = open( dashboard_out, 'w' )
    out.write( json.dumps( json_data ))
    print( "Template " + dashboard_out + " created." ) 
    out.close()
    print( "Done" )
        
    print ( "Uploading dashboard .." )
    dashboards = glob.glob( prefix + "_" + service_group + ".dashboard")
    print( len(dashboards), " to add" )
        
    client1 = boto3.client('cloudwatch' )
    for board in dashboards:
            name=board.split('.')[0]
            f = open( board, 'r' )
            fc = f.read()
            db = json.loads( fc )
            print ( "Adding dashboard: " + name )
            client1.put_dashboard( DashboardName=name,  DashboardBody=json.dumps( db ))
print( "Done" )
