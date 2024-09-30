#for managing error in aws
from botocore.exceptions import ClientError
import time

#Create target  groups
def create_target_group(elbv2, group_name, vpc_id, path):
    '''
    This function checks if a target group already exists in AWS Elastic Load Balancing (ELBv2).
    If the target group exists, it deletes the existing one and creates a new target group. 
    If it does not exist, the function creates a new target group in the specified VPC.

    Steps:
    1. The function accepts four parameters: ELBv2 client object, the target group name, VPC ID, and the health check path.
    2. It first tries to check if a target group with the specified name exists.
    3. If the target group exists, it deletes the target group.
    4. After deleting, or if the target group does not exist, it creates a new target group.
    5. The new target group is created with an HTTP health check using the specified path and port.
    6. Finally, the function returns the ARN of the created target group.

    Parameters:
        elbv2: A Boto3 ELBv2 client object to interact with AWS Elastic Load Balancing (ELBv2).
        group_name: The name of the target group to create or replace.
        vpc_id: The ID of the VPC where the target group will be created.
        path: The health check path for the target group's health monitoring.

    Returns:
        The ARN of the created target group.

    Raises:
        ClientError: If there is an issue with the ELBv2 API call, an exception will be raised.
    '''

    # Check if the target group already exists, and if so, delete it
    try:
        response = elbv2.describe_target_groups(Names=[group_name])
        target_group_arn = response['TargetGroups'][0]['TargetGroupArn']
        print(f"Target group '{group_name}' already exists with ARN: {target_group_arn}")

        # Delete the existing target group
        elbv2.delete_target_group(TargetGroupArn=target_group_arn)
        print(f"Target group '{group_name}' deleted.")
    
    # If the target group doesn't exist, create a new one
    except ClientError as e:
        if 'TargetGroupNotFound' in str(e):
            print(f"Target group '{group_name}' does not exist yet, creating a new one.")

            # Create a new target group after deletion (or if it doesn't exist)
            response = elbv2.create_target_group(
                Name=group_name,
                Protocol='HTTP',
                Port=8000,
                VpcId=vpc_id,
                HealthCheckProtocol='HTTP',
                HealthCheckPath=f'/{path}',  # Use the provided health check path
                HealthCheckPort='8000',
                TargetType='instance'
            )

            # Get the target group ARN from the response
            target_group_arn = response['TargetGroups'][0]['TargetGroupArn']
            print(f"Target group created: {target_group_arn}")
            return target_group_arn
        else:
            raise e

#Register instances 
# Function to register a list of instances to a target group
def register_instances(elbv2,target_group_arn, instance_ids):
    """
    Registers a list of EC2 instances to a specific target group.

    Args:
    target_group_arn (str): The ARN of the target group where the instances will be registered.
    instance_ids (list): A list of EC2 instance IDs to be registered.

    Returns:
    None: Registers the instances and prints success or error messages.
    """

    try:
        # Register the instances to the target group
        elbv2.register_targets(
            TargetGroupArn=target_group_arn,
            Targets=[{'Id': instance_id, 'Port': 8000} for instance_id in instance_ids]
        )
        print(f"Instances {instance_ids} successfully registered to target group {target_group_arn}.")
    except ClientError as e:
        print(f"Failed to register instances {instance_ids} to target group {target_group_arn}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while registering instances {instance_ids}: {e}")
