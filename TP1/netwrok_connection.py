#for managing error in aws
from botocore.exceptions import ClientError

#1. get VPC_id
def get_vpc(ec2):
    '''
    This function retrieves the ID of the default Virtual Private Cloud (VPC) 
    for a given EC2 object using AWS Boto3.

    Steps:
    1. The function accepts an EC2 client object (from the Boto3 library).
    2. It calls the describe_vpcs method with a filter to get VPCs 
       where 'isDefault' is true (which identifies the default VPC).
    3. From the response, it extracts the 'VpcId' of the first VPC 
       in the list of VPCs returned by the describe_vpcs method.
    4. The function returns the extracted VPC ID.

    Parameters:
        ec2: A Boto3 EC2 client object that allows interaction with AWS EC2 service.

    Returns:
        The ID of the default VPC as a string.
    '''

    # Describe VPCs with a filter for the default VPC
    response = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
    
    # Extract the VPC ID from the first VPC in the response list
    vpc_id = response['Vpcs'][0]['VpcId']
    
    # Return the VPC ID
    return vpc_id




#2.get Subnet_ids
def get_subnet_id(ec2, vpc_id):
    '''
    This function retrieves the IDs of the first two subnets associated with 
    a given Virtual Private Cloud (VPC) using AWS Boto3.

    Steps:
    1. The function takes two arguments: an EC2 client object and a VPC ID.
    2. It calls the describe_subnets method to retrieve the subnets 
       that belong to the specified VPC.
    3. If subnets are found, the function extracts the 'SubnetId' of each subnet.
    4. It collects the IDs of the first two subnets (if more are available).
    5. If no subnets are found, the function prints a message and returns None.

    Parameters:
        ec2: A Boto3 EC2 client object that allows interaction with AWS EC2 service.
        vpc_id: The ID of the VPC whose subnets need to be retrieved.

    Returns:
        A list of the first two subnet IDs if available, or None if no subnets are found.
    '''

    # Retrieve the subnets associated with the given VPC
    response = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])

    if response['Subnets']:
        # Initialize an empty list to collect subnet IDs
        subnet_ids = []
        
        # Iterate through the subnets and collect the Subnet IDs
        for i, subnet in enumerate(response['Subnets'], start=1):
            subnet_ids.append(subnet['SubnetId'])
        
        # Return the first two subnet IDs (or fewer if there are less than two)
        return subnet_ids[:2]
    else:
        # Print a message if no subnets are found and return None
        print(f"No subnets found for VPC ID: {vpc_id}")
        return None


#3. create security group and return security id
def create_security_group(ec2, vpc_id):
    '''
    This function creates or retrieves a security group in a given VPC using AWS Boto3.

    Steps:
    1. The function accepts two arguments: an EC2 client object and a VPC ID.
    2. It checks if a security group with the given group name ('my-security-group-2') already exists.
    3. If the group exists, it checks whether the group is currently in use by other resources. 
       If it is in use, the function returns the existing security group ID.
    4. If the group does not exist, it creates a new security group in the specified VPC.
    5. After creation, it configures ingress rules to allow traffic on ports 80, 8000, 443, and 22.
    6. Finally, the function returns the security group ID.

    Parameters:
        ec2: A Boto3 EC2 client object to interact with AWS EC2 service.
        vpc_id: The ID of the VPC where the security group will be created.

    Returns:
        The ID of the security group, either existing or newly created.
    '''

    group_name = 'my-security-group-2'

    # Check if the security group already exists
    try:
        response = ec2.describe_security_groups(GroupNames=[group_name])
        security_group_id = response['SecurityGroups'][0]['GroupId']
        print(f"Security group '{group_name}' already exists with ID: {security_group_id}")

        # Check if the security group is in use
        try:
            # If the group is in use by other resources, do not attempt to delete it
            print(f"Security group '{group_name}' is in use. It will not be deleted.")
            return security_group_id
        except ClientError as e:
            if 'DependencyViolation' in str(e):
                print(f"Cannot delete security group '{group_name}' because it is associated with other resources.")
            else:
                raise e

    # If the security group does not exist, create a new one
    except ClientError as e:
        if 'InvalidGroup.NotFound' in str(e):
            print(f"Security group '{group_name}' does not exist, creating a new one.")

            # Create a new security group
            security_group = ec2.create_security_group(
                GroupName=group_name,
                Description="Security group for EC2 instances",  # Description must be in ASCII
                VpcId=vpc_id
            )

            # Get the security group ID
            security_group_id = security_group['GroupId']
            print(f"Security group created: {security_group_id}")

            # Configure the security group ingress rules
            ec2.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                    {'IpProtocol': 'tcp', 'FromPort': 8000, 'ToPort': 8000, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                    {'IpProtocol': 'tcp', 'FromPort': 443, 'ToPort': 443, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
                    {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
                ]
            )
            print(f"Security group configured for ports 80, 8000, 443, and 22.")
            return security_group_id

        else:
            raise e
