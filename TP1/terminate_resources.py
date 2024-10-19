import boto3

# Initialize clients
ec2_client = boto3.client('ec2')
elb_v2_client = boto3.client('elbv2')
elb_client = boto3.client('elb')

def delete_listeners_for_load_balancer(load_balancer_arn):
    """
    This function deletes all listeners associated with a given Application Load Balancer (ALB) by its ARN.
    
    Steps:
    1. The function accepts the ARN of the load balancer as a parameter.
    2. It calls the `describe_listeners` method of the ELBv2 client to retrieve all listeners for the load balancer.
    3. It iterates through the list of listeners, extracting the ARN for each listener.
    4. For each listener, it prints a message indicating the listener ARN and proceeds to delete the listener using the `delete_listener` method.
    5. No return value is provided. The function simply performs the deletion of the listeners.

    Parameters:
        load_balancer_arn: The ARN of the load balancer for which listeners will be deleted.

    Returns:
        None. The function deletes listeners and prints messages indicating the progress.

    Raises:
        Exception: If there are errors during the deletion process, they may be raised by the AWS SDK (Boto3).
    """

    # Describe listeners for the specified load balancer
    listeners = elb_v2_client.describe_listeners(LoadBalancerArn=load_balancer_arn)['Listeners']

    # Iterate over each listener to delete it
    for listener in listeners:
        listener_arn = listener['ListenerArn']
        print(f"Deleting listener with ARN: {listener_arn} for load balancer: {load_balancer_arn}")

        # Delete the listener by its ARN
        elb_v2_client.delete_listener(ListenerArn=listener_arn)


def delete_all_load_balancers():
    """
    This function deletes all Application Load Balancers (ALBs), Network Load Balancers (NLBs),
    and Classic Load Balancers (CLBs) in an AWS account. It first deletes the listeners 
    for each ALB or NLB before deleting the load balancers themselves.
    
    Steps:
    1. The function retrieves all ALBs and NLBs using the `describe_load_balancers` method of the ELBv2 client.
    2. For each load balancer, it deletes the associated listeners using the `delete_listeners_for_load_balancer` function.
    3. After deleting the listeners, it deletes the load balancer itself by calling `delete_load_balancer`.
    4. The function then retrieves all Classic Load Balancers (CLBs) using the `describe_load_balancers` method of the ELB client.
    5. It iterates through the CLBs and deletes each one using `delete_load_balancer`.
    6. The function prints messages indicating the progress of deletion for both ALBs/NLBs and CLBs.

    Parameters:
        None.

    Returns:
        None. The function deletes all load balancers and their associated listeners.

    Raises:
        Any errors raised by the AWS SDK (Boto3) during the load balancer or listener deletion process.
    """

    # Delete Application Load Balancers (ALBs) and Network Load Balancers (NLBs)
    load_balancers = elb_v2_client.describe_load_balancers()['LoadBalancers']

    # Iterate over each load balancer to delete its listeners and the load balancer itself
    for lb in load_balancers:
        lb_arn = lb['LoadBalancerArn']
        lb_name = lb['LoadBalancerName']
        
        # Delete listeners associated with the load balancer
        print(f"Deleting listeners for load balancer: {lb_name}")
        delete_listeners_for_load_balancer(lb_arn)
        
        # Delete the load balancer
        print(f"Deleting load balancer: {lb_name} with ARN: {lb_arn}")
        elb_v2_client.delete_load_balancer(LoadBalancerArn=lb_arn)
    
    # Delete Classic Load Balancers (CLBs)
    classic_load_balancers = elb_client.describe_load_balancers()['LoadBalancerDescriptions']

    # Iterate over each Classic Load Balancer and delete it
    for clb in classic_load_balancers:
        clb_name = clb['LoadBalancerName']
        print(f"Deleting Classic Load Balancer: {clb_name}")
        elb_client.delete_load_balancer(LoadBalancerName=clb_name)


def delete_all_target_groups():
    """
    This function deletes all target groups associated with Application Load Balancers (ALBs) or Network Load Balancers (NLBs) 
    in an AWS account. If a target group is currently in use, it cannot be deleted, and an appropriate message will be printed.

    Steps:
    1. The function retrieves all target groups using the `describe_target_groups` method of the ELBv2 client.
    2. It iterates through the target groups, extracting their ARNs and names.
    3. For each target group, it attempts to delete it by calling `delete_target_group`.
    4. If a target group is currently in use (e.g., attached to a load balancer), it catches the `ResourceInUseException`
       and prints a message indicating that the target group cannot be deleted.
    5. If the target group is successfully deleted, a message indicating success is printed.

    Parameters:
        None.

    Returns:
        None. The function deletes target groups and prints messages indicating the progress of deletion or errors.

    Raises:
        Any errors raised by the AWS SDK (Boto3) during the target group deletion process, except for `ResourceInUseException` 
        which is caught and handled.
    """

    # Retrieve all target groups
    target_groups = elb_v2_client.describe_target_groups()['TargetGroups']

    # Iterate over each target group to delete it
    for tg in target_groups:
        tg_arn = tg['TargetGroupArn']
        tg_name = tg['TargetGroupName']
        
        try:
            # Attempt to delete the target group
            print(f"Deleting target group: {tg_name} with ARN: {tg_arn}")
            elb_v2_client.delete_target_group(TargetGroupArn=tg_arn)
        
        # Handle case where the target group is currently in use
        except elb_v2_client.exceptions.ResourceInUseException:
            print(f"Target group {tg_name} is in use and cannot be deleted.")


def terminate_all_instances():
    """
    This function terminates all EC2 instances in an AWS account.
    
    Steps:
    1. The function retrieves all running EC2 instances by calling the `describe_instances` method of the EC2 client.
    2. It extracts the instance IDs from the returned reservations and instances.
    3. If there are any instances to terminate, the function calls `terminate_instances` to terminate them.
    4. It prints a message indicating which instances are being terminated.
    5. If no instances are found, a message is printed indicating that there are no instances to terminate.

    Parameters:
        None.

    Returns:
        None. The function terminates EC2 instances and prints messages indicating the progress.

    Raises:
        Any errors raised by the AWS SDK (Boto3) during the instance termination process.
    """

    # Retrieve all EC2 instances
    instances = ec2_client.describe_instances()['Reservations']

    # Extract instance IDs from the instances
    instance_ids = [instance['InstanceId'] for reservation in instances for instance in reservation['Instances']]
    
    # If there are instances, terminate them
    if instance_ids:
        print(f"Terminating instances: {', '.join(instance_ids)}")
        ec2_client.terminate_instances(InstanceIds=instance_ids)
    else:
        # If no instances found, print a message
        print("No instances to terminate.")



