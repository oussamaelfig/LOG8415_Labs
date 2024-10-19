#for managing error in aws
from botocore.exceptions import ClientError


def create_load_balancer(elbv2, load_balancer_name, subnets, security_group_id):
    '''
    This function creates an internet-facing application load balancer (ALB) using AWS Elastic Load Balancing (ELBv2).
    The load balancer is created in the specified subnets with the given security group.

    Steps:
    1. The function accepts four parameters: the ELBv2 client object, the load balancer name, 
       a list of subnet IDs, and a security group ID.
    2. It calls the `create_load_balancer` method from ELBv2 to create a new load balancer.
    3. The load balancer is set up as an internet-facing, application-type load balancer with IPv4 addressing.
    4. The function returns the details of the newly created load balancer.

    Parameters:
        elbv2: A Boto3 ELBv2 client object to interact with AWS Elastic Load Balancing (ELBv2).
        load_balancer_name: The name to assign to the new load balancer.
        subnets: A list of subnet IDs where the load balancer will be placed.
        security_group_id: The security group ID to associate with the load balancer.

    Returns:
        The response object containing the details of the created load balancer.
    '''

    # Create the load balancer with the specified name, subnets, and security group
    load_balancer = elbv2.create_load_balancer(
        Name=load_balancer_name,
        Subnets=subnets,
        SecurityGroups=[security_group_id],
        Scheme='internet-facing',  # Make the load balancer accessible from the internet
        Type='application',        # This specifies that it's an application load balancer
        IpAddressType='ipv4'       # The IP address type is set to IPv4
    )

    # Return the details of the created load balancer
    return load_balancer



#Create listenr with default rule
def create_listener(elbv2, lb_arn, cluster_target_group_arn):
    '''
    This function creates an HTTP listener for an existing Application Load Balancer (ALB) in AWS Elastic Load Balancing (ELBv2).
    The listener listens on port 8000 and forwards traffic to the specified target group.

    Steps:
    1. The function accepts three parameters: the ELBv2 client object, the Load Balancer ARN, and the target group ARN.
    2. It calls the `create_listener` method to create an HTTP listener on port 8000.
    3. The listener forwards all traffic to the specified target group using the ARN of the target group.
    4. If successful, the function prints and returns the ARN of the created listener.
    5. If there is an error during the listener creation, an error message is printed.

    Parameters:
        elbv2: A Boto3 ELBv2 client object to interact with AWS Elastic Load Balancing (ELBv2).
        lb_arn: The Amazon Resource Name (ARN) of the load balancer where the listener will be created.
        cluster1_target_group_arn: The ARN of the target group to forward traffic to.

    Returns:
        The ARN of the created listener if successful, or None if there is an error.

    Raises:
        ClientError: If there is an issue with the ELBv2 API call, an exception will be raised and handled.
    '''

    try:
        # Create a listener for the load balancer on port 8000, forwarding traffic to the target group
        response = elbv2.create_listener(
            LoadBalancerArn=lb_arn,
            Protocol='HTTP',
            Port=8000,
            DefaultActions=[{
                'Type': 'forward',
                'TargetGroupArn': cluster_target_group_arn
            }]
        )

        # Extract the Listener ARN from the response
        listener_arn = response['Listeners'][0]['ListenerArn']
        print(f"Listener created for the Load Balancer with ARN: {listener_arn}")

        # Return the Listener ARN
        return listener_arn

    # Handle potential errors during listener creation
    except ClientError as e:
        print(f"Error creating the listener: {str(e)}")


#Create rules for target groups
def create_rule(elbv2, listener_arn, target_group_arn, path, priority):
    '''
    This function creates a forwarding rule for an existing listener in AWS Elastic Load Balancing (ELBv2).
    The rule forwards traffic that matches a specified path pattern to a target group and is assigned a priority.

    Steps:
    1. The function accepts five parameters: the ELBv2 client object, listener ARN, target group ARN, 
       the path pattern for the rule, and the rule's priority.
    2. It calls the `create_rule` method to create a rule that forwards requests with a matching path pattern.
    3. The rule forwards traffic to the specified target group based on the path condition.
    4. The rule is assigned a priority to determine the order in which it will be evaluated.
    5. Finally, the function returns the rule details.

    Parameters:
        elbv2: A Boto3 ELBv2 client object to interact with AWS Elastic Load Balancing (ELBv2).
        listener_arn: The Amazon Resource Name (ARN) of the listener to which the rule will be attached.
        target_group_arn: The ARN of the target group where the traffic will be forwarded.
        path: The path pattern that the rule will match.
        priority: The priority of the rule, which determines its evaluation order.

    Returns:
        The response object containing the details of the created rule.

    Raises:
        ClientError: If there is an issue with the ELBv2 API call, an exception will be raised.
    '''

    # Create a forwarding rule for the specified listener and target group
    rule = elbv2.create_rule(
        ListenerArn=listener_arn,
        Conditions=[{
            'Field': 'path-pattern',  # Specify the condition to match the request path
            'Values': [path]          # The path pattern that the rule will match
        }],
        Priority=priority,             # Set the priority for rule evaluation
        Actions=[{
            'Type': 'forward',         # Forward the traffic to the specified target group
            'TargetGroupArn': target_group_arn
        }]
    )

    # Return the created rule's details
    return rule
