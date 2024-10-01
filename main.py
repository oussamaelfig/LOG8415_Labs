#aws library
import boto3
#import vpc,subnet_id,create_security_group
from netwrok_connection import get_vpc,get_subnet_id,create_security_group
#keypair and creat isntaces
from create_instances import create_key_pair,create_instances,get_public_ids

#deployement FAST API
from deploy_fastAPI import setup_fastapi_app

#target group
from target_groups import create_target_group,register_instances,wait_for_target_group_health


#load balancer 
from loadbalancer import create_load_balancer,create_listener,create_rule

#benckmark
from benckmarking import execute_benchmark_script_on_instance

#cloud watch
from cloudwatch import plot_comparison_metrics,get_ec2_metrics,get_target_group_arn,get_instance_ids_from_target_group
from cloudwatch_loadbalancer import get_load_balancer_arn,plot_metrics,get_load_balancer_request_count
import time

#terminate ressources
from terminate_resources import delete_all_load_balancers,delete_all_target_groups,terminate_all_instances


# Creating an EC2 client
ec2 = boto3.client('ec2',region_name='us-east-1')
elbv2 = boto3.client('elbv2',region_name='us-east-1')



#1. get VPC
vpc_id=get_vpc(ec2=ec2)


#2. get subnet_id
subnet_ids=get_subnet_id(ec2=ec2,vpc_id=vpc_id)
# print(subnet_ids)
subnet_id_1=subnet_ids[0]

#3. create security_group
securiy_group_id=create_security_group(ec2=ec2,vpc_id=vpc_id)

#4. create keypair
#name of keypair
key_name = 'my-key-pair'
#path of keypair
key_file = f"./{key_name}.pem"
create_key_pair(ec2=ec2,key_name=key_name,key_file=key_file)

#5. create instance:
#5.creatting instance for micro and large
#ubuntu ami
ami_id = 'ami-0e86e20dae9224db8'
#CPU type
instance_type_micro='t2.micro'
#number of instances
nb_instances_micro=5
#creation instances
instance_ids_micro=create_instances(ec2=ec2,ami_id=ami_id,key_name=key_name,
                                    subnet_id=subnet_id_1,security_group_id=securiy_group_id,
                                    instance_type=instance_type_micro, num_instances=
                                    nb_instances_micro)
#get ip of instances
instance_ips_micro=get_public_ids(ec2=ec2,instance_ids=instance_ids_micro)

#CPU type
instance_type_large='t2.large'
#number of instances
nb_instances_large=4
#creation instances
instance_ids_large=create_instances(ec2=ec2,ami_id=ami_id,key_name=key_name,
                                    subnet_id=subnet_id_1,security_group_id=securiy_group_id,
                                    instance_type=instance_type_large, 
                                    num_instances=nb_instances_large)
#get ip of instances
instance_ips_large=get_public_ids(ec2=ec2,instance_ids=instance_ids_large)


#6. Deploy FAST API
# Deploy to t2.micro instances (Cluster 1)
for instance_id, public_ip in zip(instance_ids_micro, instance_ips_micro):
    setup_fastapi_app(public_ip, 'ubuntu', key_file, instance_id, "cluster1")

# Deploy to t2.large instances (Cluster 2)
for instance_id, public_ip in zip(instance_ids_large, instance_ips_large):
    setup_fastapi_app(public_ip, 'ubuntu', key_file, instance_id, "cluster2")


#6. Create target group
target_group_arn_cluster1=create_target_group(elbv2=elbv2,group_name='cluster1-target-group',vpc_id= vpc_id,path='cluster1')
target_group_arn_cluster2=create_target_group(elbv2=elbv2,group_name='cluster2-target-group', vpc_id=vpc_id,path='cluster2')

#7. Create Load balancer
#name of load balancer
load_balancer_name = 'my-load-balancer'
load_balancer=create_load_balancer(elbv2=elbv2,load_balancer_name=load_balancer_name,
                                   subnets=subnet_ids,security_group_id=securiy_group_id)
#get load balancer arn
load_balancer_arn = load_balancer['LoadBalancers'][0]['LoadBalancerArn']
#get dns name of load balancer
dns_name = load_balancer['LoadBalancers'][0]['DNSName']
#get url of load balancer
ec2_url = f"http://{dns_name}"
print("load balancer url is: ",ec2_url)


#8. Create listener
listener_arn=create_listener(elbv2=elbv2,lb_arn=load_balancer_arn,
                             cluster_target_group_arn=target_group_arn_cluster1)

#9. Configure rules
#Create rules for target groups
cluster1_rule=create_rule(elbv2=elbv2,listener_arn=listener_arn,target_group_arn=target_group_arn_cluster1, path='/cluster1', priority=1)
cluster2_rule=create_rule(elbv2=elbv2,listener_arn=listener_arn,target_group_arn=target_group_arn_cluster2, path='/cluster2', priority=2)

#10. Activate all instances
# start the instances created in cluster 1 => micro
ec2.start_instances(InstanceIds = instance_ids_micro)   

# start the instances created in cluster 2 => large
ec2.start_instances(InstanceIds = instance_ids_large)

# wait for all instances to be running before proceeding
instanceIds = [*instance_ids_micro, *instance_ids_large]
waiter = ec2.get_waiter('instance_running')
waiter.wait(InstanceIds = instanceIds)

#11. Register instances in target groups
register_instances(elbv2=elbv2,target_group_arn=target_group_arn_cluster1, instance_ids=instance_ids_micro)
register_instances(elbv2=elbv2,target_group_arn=target_group_arn_cluster2, instance_ids=instance_ids_large)

#12.Benchmarking

#a. wait until all target groups become healthy
health_status_cluster1=wait_for_target_group_health(elbv2=elbv2,target_group_arn=target_group_arn_cluster1, max_retries=10, delay=60)
health_status_cluster2=wait_for_target_group_health(elbv2=elbv2,target_group_arn=target_group_arn_cluster2, max_retries=10, delay=60)


#b. send benchmark file for each cluster
if health_status_cluster1 and health_status_cluster2:
    #pick an instance_ip randomly
    ec2_radom_ip=instance_ips_large[0]
    #send script to this machine and run script 
    execute_benchmark_script_on_instance(instance_ip=ec2_radom_ip, load_balancer_url=ec2_url, pem_key_path=key_file, user='ubuntu')

#13.Cloud watch
# Define the target group names

target_group_names = ['cluster1-target-group', 'cluster2-target-group']  # Replace with your actual target group names

# Loop through each target group and fetch the metrics
aggregated_data = {}
for target_group_name in target_group_names:
    # Dynamically get the Target Group ARN
    target_group_arn = get_target_group_arn(target_group_name)

    if target_group_arn:
        # Fetch EC2 instance IDs from the target group
        instance_ids = get_instance_ids_from_target_group(target_group_arn)

        # Initialize containers for aggregated timestamps and values for each metric
        aggregated_timestamps = []
        aggregated_values = {}

        # Loop over all EC2 instances in the target group and fetch their metrics
        for metric_name in ['CPUUtilization', 'NetworkIn', 'NetworkOut']:
            aggregated_values[metric_name] = []

            for instance_id in instance_ids:
                timestamps, values = get_ec2_metrics(instance_id, metric_name)

                if timestamps and values:
                    if not aggregated_timestamps:
                        aggregated_timestamps = timestamps  # Initialize timestamps with the first instance
                    if aggregated_timestamps == timestamps:
                        # Add the values to the aggregated values list
                        if not aggregated_values[metric_name]:
                            aggregated_values[metric_name] = values
                        else:
                            aggregated_values[metric_name] = [sum(x) for x in zip(aggregated_values[metric_name], values)]
                    else:
                        print(f"Timestamps for {instance_id} are not aligned with other instances.")

            # After iterating over instances, average the aggregated values
            if aggregated_values[metric_name]:
                aggregated_values[metric_name] = [x / len(instance_ids) for x in aggregated_values[metric_name]]

            # Add aggregated data for each target group to the dictionary
            if metric_name not in aggregated_data:
                aggregated_data[metric_name] = {}
            aggregated_data[metric_name][target_group_name] = (aggregated_timestamps, aggregated_values[metric_name])

# Plot the comparison for each metric
for metric_name in ['CPUUtilization', 'NetworkIn', 'NetworkOut']:
    plot_comparison_metrics(aggregated_data[metric_name], metric_name)


# Sleep for 5 minutes (300 seconds)
print("Sleep for 5 minuts")
time.sleep(300)

#14. Cloud watch for load balancer
# Dynamically get the Load Balancer ARN
lb_arn = get_load_balancer_arn()

if lb_arn:
    # Fetch data and plot the RequestCount
    timestamps, values = get_load_balancer_request_count(lb_arn)
    plot_metrics(timestamps, values)


#15. Terminate ressources

delete_all_load_balancers()
delete_all_target_groups()
terminate_all_instances()


print("All load balancers, target groups, EC2 instances have been deleted.")