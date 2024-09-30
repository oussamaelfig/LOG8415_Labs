#for managing error in aws
from botocore.exceptions import ClientError
#for getting permission on key pairs(chmod 400)
import os
import stat

import time


#Create key pairs
def create_key_pair(ec2, key_name, key_file):
    '''
    This function checks if an EC2 key pair exists, and if not, it creates a new key pair. 
    The key pair is saved to a file with appropriate permissions.

    Steps:
    1. The function accepts three arguments: an EC2 client object, the key pair name, and the path to the key file.
    2. It checks if the key pair with the specified name already exists using describe_key_pairs.
    3. If the key pair exists, it prints a message and sets the correct file permissions for the key file.
    4. If the key pair does not exist, it creates a new key pair and saves the private key material to a .pem file.
    5. The function sets the correct permissions (read-only for the owner) on the key file to ensure security.

    Parameters:
        ec2: A Boto3 EC2 client object to interact with AWS EC2 service.
        key_name: The name of the key pair to create or check for.
        key_file: The path to the .pem file to store the key.

    Returns:
        None.
    '''

    # Check if the key pair already exists
    try:
        ec2.describe_key_pairs(KeyNames=[key_name])
        print(f"Key Pair '{key_name}' already exists.")
        
        # Set proper permissions for the pem file (read-only for the owner)
        os.chmod(key_file, stat.S_IRUSR)

    # If the key pair doesn't exist, create a new one
    except ClientError as e:
        if 'InvalidKeyPair.NotFound' in str(e):
            # Create the key pair
            key_pair = ec2.create_key_pair(KeyName=key_name)
            
            # Save the private key material to a .pem file
            with open(f'{key_name}.pem', 'w') as file:
                file.write(key_pair['KeyMaterial'])
            print(f"Key Pair created and saved as {key_name}.pem")
            
            # Set proper permissions for the pem file (read-only for the owner)
            os.chmod(key_file, stat.S_IRUSR)
        else:
            raise e

#create instance
def create_instances(ec2, ami_id, key_name, subnet_id, security_group_id, instance_type, num_instances):
    '''
    This function launches a specified number of EC2 instances with the provided parameters.
    It uses AWS Boto3 to run instances and waits until the instances are in the 'running' state.

    Steps:
    1. The function accepts parameters like EC2 client object, AMI ID, key pair name, subnet ID, 
       security group ID, instance type, and the number of instances to launch.
    2. It uses the `run_instances` method to launch the EC2 instances with the provided configuration.
    3. The instances are tagged with a name that includes the instance type.
    4. It enables monitoring for the instances.
    5. The function then waits for the instances to reach the 'running' state using a waiter.
    6. Finally, the function returns the list of instance IDs for the created instances.

    Parameters:
        ec2: A Boto3 EC2 client object to interact with AWS EC2 service.
        ami_id: The Amazon Machine Image (AMI) ID to use for launching instances.
        key_name: The key pair name to associate with the instances.
        subnet_id: The subnet ID where the instances will be launched.
        security_group_id: The security group ID to assign to the instances.
        instance_type: The type of instance to launch (e.g., t2.micro).
        num_instances: The number of instances to launch.

    Returns:
        A list of instance IDs for the instances that were launched.
    '''

    # Launch EC2 instances with the specified parameters
    response = ec2.run_instances(
        ImageId=ami_id,
        MinCount=num_instances,
        MaxCount=num_instances,
        InstanceType=instance_type,
        KeyName=key_name,
        SubnetId=subnet_id,
        SecurityGroupIds=[security_group_id],
        # Tag the instances with a name that includes the instance type
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{'Key': 'Name', 'Value': f'cluster-{instance_type}'}]
        }],
        # Enable detailed monitoring for the instances
        Monitoring={
            'Enabled': True
        }
    )
    
    # Collect the instance IDs from the response
    instance_ids = [instance['InstanceId'] for instance in response['Instances']]
    print(f"Created instances: {instance_ids}")
    
    # Wait for the instances to reach the 'running' state
    print("Waiting for instances to reach the 'running' state...")
    ec2.get_waiter('instance_running').wait(InstanceIds=instance_ids)
    print(f"Instances are now running: {instance_ids}")

    # Return the list of instance IDs
    return instance_ids


def get_public_ids(ec2, instance_ids):
    '''
    This function retrieves the public IP addresses of EC2 instances by their instance IDs.
    It waits for each instance to have a public IP and appends the public IPs to a list.

    Steps:
    1. The function accepts two parameters: an EC2 client object and a list of instance IDs.
    2. It iterates over each instance ID, waiting for the instance to obtain a public IP.
    3. The `wait_for_public_ip` function is called to wait for the public IP assignment.
    4. Once the public IP is available, it is printed and added to the list of public IPs.
    5. Finally, the function returns a list of public IP addresses for the given instances.

    Parameters:
        ec2: A Boto3 EC2 client object to interact with AWS EC2 service.
        instance_ids: A list of EC2 instance IDs for which to fetch public IP addresses.

    Returns:
        A list of public IP addresses for the specified EC2 instances.
    '''

    # Initialize an empty list to store public IPs
    public_ips = []
    
    # Iterate over the list of instance IDs
    for instance_id in instance_ids:
        # Wait for the instance to obtain a public IP
        public_ip = wait_for_public_ip(ec2, instance_id)
        
        # Print the public IP of the instance
        print("IP address is", public_ip)
        
        # Append the public IP to the list
        public_ips.append(public_ip)
    
    # Return the list of public IPs
    return public_ips



# Function to wait for public IP
def wait_for_public_ip(ec2, instance_id, retries=10, delay=10):
    '''
    This function waits for an EC2 instance to obtain a public IP address by periodically checking
    the instance's public IP over a specified number of retries. If the public IP is not available
    after the given number of retries, the function raises an exception.

    Steps:
    1. The function accepts three parameters: an EC2 client object, the instance ID, 
       and optional parameters for retries and delay between retries.
    2. It loops over a specified number of retries to check if the instance has a public IP.
    3. The `describe_instances` method is used to retrieve the instance details, 
       and it checks for the 'PublicIpAddress' field.
    4. If the public IP is found, it is returned immediately.
    5. If the public IP is not found, the function waits for the specified delay before retrying.
    6. If the retries are exhausted without retrieving a public IP, the function raises an exception.

    Parameters:
        ec2: A Boto3 EC2 client object to interact with AWS EC2 service.
        instance_id: The ID of the EC2 instance to check for a public IP.
        retries: The number of attempts to check for the public IP (default is 10).
        delay: The amount of time (in seconds) to wait between retries (default is 10 seconds).

    Returns:
        The public IP address of the instance if available.

    Raises:
        Exception: If the public IP is not retrieved after the specified number of retries.
    '''

    # Loop over the specified number of retries
    for attempt in range(retries):
        # Describe the instance to fetch its details
        response = ec2.describe_instances(InstanceIds=[instance_id])
        
        # Try to get the public IP address from the response
        public_ip = response['Reservations'][0]['Instances'][0].get('PublicIpAddress')
        
        # If a public IP is found, return it
        if public_ip:
            return public_ip
        
        # Wait for the specified delay before the next retry
        time.sleep(delay)
    
    # Raise an exception if the public IP is not retrieved after all retries
    raise Exception(f"Public IP for instance {instance_id} could not be retrieved.")

