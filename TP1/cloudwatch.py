import boto3
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os

# Initialize boto3 clients
cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
elb = boto3.client('elbv2', region_name='us-east-1')

# Function to retrieve Target Group ARNs dynamically
def get_target_group_arn(target_group_name):
    '''
    This function retrieves the Amazon Resource Name (ARN) of a target group by its name using AWS Elastic Load Balancing (ELB).
    
    Steps:
    1. The function accepts the name of the target group as a parameter.
    2. It calls the `describe_target_groups` method of the ELB client to fetch details of the specified target group.
    3. If the target group is found, the ARN of the first target group in the response is retrieved and printed.
    4. If no target group is found, it prints a message indicating that no target group was found.
    5. If an error occurs during the API call, it catches the exception and prints an error message.
    6. The function returns the ARN of the target group if found, otherwise, it returns `None`.

    Parameters:
        target_group_name: The name of the target group to retrieve the ARN for.

    Returns:
        The ARN of the target group if found, or `None` if not found or an error occurred.

    Raises:
        Exception: If any error occurs while retrieving the target group ARN, it is caught and handled.
    '''
    
    try:
        # Describe the target group by name using the ELB client
        response = elb.describe_target_groups(Names=[target_group_name])

        # Check if the target group is present in the response
        if 'TargetGroups' in response and len(response['TargetGroups']) > 0:
            # Extract the Target Group ARN from the response
            target_group_arn = response['TargetGroups'][0]['TargetGroupArn']
            print(f"Retrieved Target Group ARN: {target_group_arn}")

            # Return the Target Group ARN
            return target_group_arn
        else:
            # Print message if no target group was found
            print(f"No target groups found with name: {target_group_name}")
            return None

    # Handle any exceptions during the API call
    except Exception as e:
        print(f"Error retrieving target group ARN: {e}")
        return None


# Function to fetch EC2 instance IDs from a target group
def get_instance_ids_from_target_group(target_group_arn):
    '''
    This function retrieves the EC2 instance IDs associated with a given target group in AWS Elastic Load Balancing (ELB).
    
    Steps:
    1. The function accepts the ARN of the target group as a parameter.
    2. It calls the `describe_target_health` method of the ELB client to fetch the health descriptions of the targets in the target group.
    3. The EC2 instance IDs are extracted from the target health descriptions.
    4. If the target group contains instances, their IDs are printed and returned as a list.
    5. If an error occurs during the API call, the exception is caught and an error message is printed.
    6. If an error occurs, the function returns an empty list.

    Parameters:
        target_group_arn: The ARN of the target group from which to retrieve the instance IDs.

    Returns:
        A list of EC2 instance IDs associated with the target group. If an error occurs, an empty list is returned.

    Raises:
        Exception: Any errors during the API call are caught and handled.
    '''

    try:
        # Describe the target health of the target group using its ARN
        response = elb.describe_target_health(TargetGroupArn=target_group_arn)

        # Extract the EC2 instance IDs from the target health descriptions
        instance_ids = [target['Target']['Id'] for target in response['TargetHealthDescriptions']]
        print(f"EC2 Instance IDs from Target Group: {instance_ids}")

        # Return the list of instance IDs
        return instance_ids

    # Handle any exceptions during the API call
    except Exception as e:
        print(f"Error retrieving instance IDs from target group: {e}")
        return []


# Function to fetch CPU utilization or network metric for EC2 instances
def get_ec2_metrics(instance_id, metric_name):
    '''
    This function retrieves CloudWatch metrics for a specified EC2 instance over the past hour.
    It fetches the average of the specified metric in 5-minute intervals and returns the timestamps 
    and values for the metric.

    Steps:
    1. The function accepts the EC2 instance ID and the metric name as parameters.
    2. It calls the `get_metric_statistics` method from AWS CloudWatch to fetch the metric data 
       for the specified instance and time period.
    3. The metric is averaged over 5-minute intervals for the past 1 hour.
    4. The function extracts the timestamps and corresponding metric values from the response.
    5. The data is sorted by timestamp to ensure chronological order.
    6. The function returns two lists: one for the timestamps and one for the metric values.
    7. If an error occurs during the API call, the exception is caught, an error message is printed,
       and two empty lists are returned.

    Parameters:
        instance_id: The ID of the EC2 instance to retrieve the metrics for.
        metric_name: The name of the CloudWatch metric to fetch (e.g., 'CPUUtilization').

    Returns:
        Two lists: one for timestamps and one for metric values. If an error occurs, empty lists are returned.

    Raises:
        Exception: Any errors during the API call are caught and handled.
    '''

    try:
        # Fetch metrics for the EC2 instance from CloudWatch
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/EC2',  # Specify the EC2 namespace for metrics
            MetricName=metric_name,  # The name of the metric to retrieve
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],  # Filter by EC2 instance ID
            StartTime=datetime.utcnow() - timedelta(hours=1),  # Last 1 hour
            EndTime=datetime.utcnow(),  # Current time
            Period=300,  # 5-minute intervals
            Statistics=['Average']  # Fetch the average of the metric over the period
        )

        # Extract timestamps and values from the response
        timestamps = [datapoint['Timestamp'] for datapoint in response['Datapoints']]
        values = [datapoint['Average'] for datapoint in response['Datapoints']]

        # Sort the timestamps and values for chronological order
        if timestamps and values:
            sorted_data = sorted(zip(timestamps, values), key=lambda x: x[0])
            timestamps, values = zip(*sorted_data)

        # Return the sorted timestamps and values
        return timestamps, values

    # Handle any exceptions during the API call
    except Exception as e:
        print(f"Error retrieving metrics for {instance_id}: {e}")
        return [], []


# Function to plot metrics for comparison between two target groups
def plot_comparison_metrics(aggregated_data, metric_name):
    '''
    This function plots a comparison of CloudWatch metrics across multiple target groups.
    It visualizes the metric data for each target group over time and saves the plot as a PNG file.

    Steps:
    1. The function accepts two parameters: `aggregated_data`, which contains the metric data (timestamps and values)
       for each target group, and `metric_name`, the name of the metric being plotted.
    2. If `aggregated_data` is empty, a message is printed and the function returns without plotting.
    3. A line plot is created for each target group, with timestamps on the x-axis and metric values on the y-axis.
    4. The plot includes a title, labels, and a legend to differentiate the target groups.
    5. The x-axis labels are rotated for better readability, and the layout is adjusted for clarity.
    6. The plot is saved as a PNG file in the 'images' directory with the metric name in the filename.
    7. The plot is then displayed using `plt.show()`.

    Parameters:
        aggregated_data: A dictionary where the keys are target group names and the values are tuples containing
                         timestamps and corresponding metric values for each target group.
        metric_name: The name of the metric being plotted (e.g., 'CPUUtilization').

    Returns:
        None.

    Raises:
        If there is an issue during plotting, an exception may occur (e.g., missing data or file saving issues).
    '''

  # Set the relative or absolute path for the images directory
    image_dir = 'images'

    # Verify if the 'images' directory exists, and if not, create it
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)

    # Check if there is data to plot, if not, return early
    if not aggregated_data:
        print(f"No data to plot for {metric_name}.")
        return

    # Plot the metric data for each target group
    plt.figure(figsize=(10, 6))  # Create a figure for the plot with a defined size

    # Loop through the aggregated data and plot each target group's metrics
    for target_group_name, (timestamps, values) in aggregated_data.items():
        plt.plot(timestamps, values, marker='o', label=f'{target_group_name} - {metric_name}')

    # Add labels and a title to the plot
    plt.xlabel('Time')  # X-axis label
    plt.ylabel(metric_name)  # Y-axis label with the metric name
    plt.title(f'{metric_name} Comparison Between Target Groups')  # Plot title

    # Rotate the x-axis labels for better readability
    plt.xticks(rotation=45)

    # Add a legend to the plot to differentiate between target groups
    plt.legend()

    # Adjust the layout to prevent overlapping elements
    plt.tight_layout()

    # Save the plot as a PNG file in the 'images' directory
    plot_file_path = os.path.join(image_dir, f'{metric_name}_comparison.png')
    plt.savefig(plot_file_path)

    # Display the plot on the screen
    plt.show()

    print(f"Plot saved at {plot_file_path}")
