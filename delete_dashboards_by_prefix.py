#import pydevd
#pydevd.settrace('127.0.0.1', port=9000)

import boto3, json, os, glob

def delete_dashboards_by_prefix(prefix):
    os.chdir("/home/centos/bin")
    client1 = boto3.client('cloudwatch' )
    delete_list=[]
    current_dashboards = client1.list_dashboards( DashboardNamePrefix=prefix )
    for dboard in current_dashboards['DashboardEntries']:
        name=dboard['DashboardName']
        print ( "Delete ", name ) 
        delete_list.append( name ) 
    
    if ( len(delete_list) > 0 ):
        print( "Dashboards to delete: ", delete_list )
        client1.delete_dashboards( DashboardNames=delete_list )
        print ( "Dashboards removed" )	
    
