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


# Function to dynamically retrieve the Load Balancer ARN
def get_load_balancer_arn():
    """
    This function retrieves the Amazon Resource Name (ARN) of the first available load balancer
    from AWS Elastic Load Balancing (ELB). It extracts the resource portion of the ARN using the 
    `extract_lb_resource_from_arn` function.

    Steps:
    1. The function calls the `describe_load_balancers` method to retrieve all load balancers.
    2. It checks if there are any load balancers in the response.
    3. If load balancers are present, it extracts the full ARN of the first load balancer.
    4. The resource portion of the ARN is extracted using the `extract_lb_resource_from_arn` function.
    5. If no load balancers are found, it prints a message and returns `None`.
    6. If an error occurs during the API call, it catches the exception, prints the error message, 
       and returns `None`.

    Returns:
        The resource portion of the load balancer ARN (e.g., 'app/my-load-balancer/...') if successful.
        If no load balancers are found or if an error occurs, the function returns `None`.

    Raises:
        Exception: Any errors during the API call are caught and handled.
    """

    try:
        # Retrieve the list of load balancers from AWS
        response = elb.describe_load_balancers()

        # Check if there are load balancers in the response
        if 'LoadBalancers' in response and len(response['LoadBalancers']) > 0:
            # Assuming we're using the first load balancer in the list
            full_lb_arn = response['LoadBalancers'][0]['LoadBalancerArn']

            # Extract and return the resource part of the ARN
            lb_arn = extract_lb_resource_from_arn(full_lb_arn)
            return lb_arn
        else:
            # If no load balancers are found, print a message and return None
            print("No load balancers found.")
            return None

    # Handle any exceptions during the API call
    except Exception as e:
        print(f"Error retrieving load balancer ARN: {e}")
        return None


# Function to fetch RequestCount metric data for the load balancer
def get_load_balancer_request_count(lb_arn):
    """
    This function retrieves the request count for a specified Application Load Balancer (ALB) 
    from AWS CloudWatch over the last 24 hours. The function fetches the `RequestCount` metric 
    in 5-minute intervals and returns the timestamps and request count values.

    Steps:
    1. The function accepts the ARN of the load balancer as a parameter.
    2. It checks if the `lb_arn` is provided. If not, it prints a message and returns empty lists.
    3. The function calls `get_metric_statistics` from AWS CloudWatch to fetch the `RequestCount` metric
       for the load balancer over the last 24 hours.
    4. It extracts the timestamps and request count values from the response.
    5. If no data is available, a message is printed. Otherwise, the data is sorted by timestamp and printed.
    6. Finally, the function returns two lists: one for the timestamps and one for the request count values.
    7. If an error occurs during the API call, the exception is caught, an error message is printed, and empty lists are returned.

    Parameters:
        lb_arn: The ARN of the load balancer to retrieve the request count for.

    Returns:
        Two lists: one for the timestamps and one for the request count values. If no data is available 
        or an error occurs, empty lists are returned.

    Raises:
        Exception: Any errors during the API call are caught and handled.
    """

    # Check if the load balancer ARN is provided
    if not lb_arn:
        print("Load Balancer ARN is missing.")
        return [], []

    try:
        # Fetch the RequestCount metric for the load balancer from CloudWatch over the last 24 hours
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/ApplicationELB',  # Namespace for ALB metrics
            MetricName='RequestCount',  # Metric to retrieve (RequestCount)
            Dimensions=[{'Name': 'LoadBalancer', 'Value': lb_arn}],  # Filter by load balancer ARN
            StartTime=datetime.utcnow() - timedelta(hours=24),  # Last 24 hours
            EndTime=datetime.utcnow(),  # Current time
            Period=300,  # 5-minute intervals
            Statistics=['Sum']  # Sum the request counts over each interval
        )

        # Extract timestamps and request count values from the response
        timestamps = [datapoint['Timestamp'] for datapoint in response['Datapoints']]
        values = [datapoint['Sum'] for datapoint in response['Datapoints']]

        # If no data is available, print a message
        if not timestamps or not values:
            print("No data available.")
        else:
            # Sort the data by timestamp for chronological ordering
            sorted_data = sorted(zip(timestamps, values), key=lambda x: x[0])
            timestamps, values = zip(*sorted_data)

            # Print out the number of requests at each timestamp
            print("\nRequest Count Data:")
            for time, value in zip(timestamps, values):
                print(f"Time: {time}, Request Count: {value}")

        # Return the timestamps and values
        return timestamps, values

    # Handle any exceptions during the API call
    except Exception as e:
        print(f"Error retrieving metrics: {e}")
        return [], []


# Function to plot the RequestCount over time and save it to a directory
def plot_metrics(timestamps, values, directory="images"):
    """
    This function plots the RequestCount metric over time and saves the plot as a PNG file in the specified directory.
    
    Steps:
    1. The function accepts three parameters: `timestamps` (list of timestamps), `values` (list of request counts), 
       and `directory` (the directory to save the plot, default is 'images').
    2. It first checks if there is data to plot. If either `timestamps` or `values` is empty, a message is printed, 
       and the function returns.
    3. The function checks if the specified directory exists. If not, it creates the directory.
    4. It then generates a line plot of the request counts over time.
    5. The plot includes labeled axes, a title, and a legend. The x-axis labels are rotated for readability.
    6. The plot is saved as a PNG file in the specified directory, and the file path is printed.
    7. Finally, the plot is displayed using `plt.show()`.

    Parameters:
        timestamps: A list of timestamps for the RequestCount metric.
        values: A list of request count values corresponding to the timestamps.
        directory: The directory where the plot will be saved (default is 'images').

    Returns:
        None. The function saves the plot as a file and displays it.

    Raises:
        If there is an issue with file creation or plotting, an exception may occur.
    """

    # Check if there is data to plot
    if not timestamps or not values:
        print("No data to plot.")
        return
    
    # Create the directory if it does not exist
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Plotting the RequestCount data
    plt.figure(figsize=(10, 6))  # Set figure size
    plt.plot(timestamps, values, marker='o', color='blue', label='Request Count')  # Plot with markers
    plt.xlabel('Time')  # Label for the x-axis
    plt.ylabel('Request Count')  # Label for the y-axis
    plt.title('Request Count Over Time for Load Balancer')  # Title of the plot
    plt.xticks(rotation=45)  # Rotate the x-axis labels for better readability
    plt.legend()  # Show the legend
    plt.tight_layout()  # Adjust the layout to prevent overlapping elements

    # Save the plot as a PNG file in the specified directory
    file_path = os.path.join(directory, 'request_count_plot.png')
    plt.savefig(file_path)  # Save the plot as a file
    plt.show()  # Display the plot

    # Print the file path where the plot is saved
    print(f"Plot saved to {file_path}")
