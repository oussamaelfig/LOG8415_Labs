import boto3
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os

# Initialize boto3 clients
cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
elb = boto3.client('elbv2', region_name='us-east-1')

# Function to extract the resource part of the ARN (app/my-load-balancer/...)
def extract_lb_resource_from_arn(full_arn):
    """
    This function extracts the resource portion (e.g., 'app/my-load-balancer/...') from a full Amazon Resource Name (ARN)
    for a load balancer. The function assumes that the ARN is split by '/' and returns the second, third, and fourth 
    parts of the ARN, joined by slashes.

    Steps:
    1. The function accepts the full ARN as a parameter.
    2. It splits the ARN by '/' to break it into its components.
    3. If the ARN contains at least four components (to ensure it has the expected structure), 
       it extracts and returns the resource part as 'arn_part2/arn_part3/arn_part4'.
    4. If the ARN does not meet the expected structure, a ValueError is raised with a message indicating
       that the ARN format is invalid.

    Parameters:
        full_arn: The full ARN string to extract the resource part from.

    Returns:
        A string containing the resource part of the ARN (e.g., 'app/my-load-balancer/...').

    Raises:
        ValueError: If the ARN does not have the expected format with at least 3 components.
    """

    # Split the full ARN by '/' to get its components
    arn_parts = full_arn.split('/')

    # Ensure that the ARN has at least 4 parts (minimum required structure)
    if len(arn_parts) >= 3:
        # Return the resource part of the ARN (second, third, and fourth parts)
        return f"{arn_parts[1]}/{arn_parts[2]}/{arn_parts[3]}"
    else:
        # Raise an error if the ARN format is invalid
        raise ValueError("Invalid ARN format")
