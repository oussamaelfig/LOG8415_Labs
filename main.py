#aws library
import boto3
#import vpc,subnet_id,create_security_group
from netwrok_connection import get_vpc,get_subnet_id,create_security_group #Neda
#keypair and creat isntaces
from create_instances import create_key_pair,create_instances,get_public_ids #Neda

#deployement FAST API
from deploy_fastAPI import setup_fastapi_app



# Creating an EC2 client
ec2 = boto3.client('ec2',region_name='us-east-1')
elbv2 = boto3.client('elbv2',region_name='us-east-1')



#1. get VPC Neda
vpc_id=get_vpc(ec2=ec2)


#2. get subnet_id Neda
subnet_ids=get_subnet_id(ec2=ec2,vpc_id=vpc_id)
# print(subnet_ids)
subnet_id_1=subnet_ids[0]

#3. create security_group Neda
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

