import paramiko
import os

# Paramiko SSH and SFTP function to transfer and execute scripts
def execute_benchmark_script_on_instance(instance_ip, load_balancer_url, pem_key_path, user='ubuntu'):
    '''
    This function connects to an EC2 instance via SSH, transfers a benchmarking script, 
    and executes it remotely. The script performs a high-volume request load 
    on a specified load balancer URL and logs performance metrics.

    Steps:
    1. The function accepts four parameters: the EC2 instance IP, load balancer URL, 
       the path to the PEM key for SSH authentication, and the username (default: 'ubuntu').
    2. It generates a benchmarking Python script locally that sends 10,000 requests to the load balancer.
    3. The script is transferred to the EC2 instance via SFTP using Paramiko.
    4. Several commands are executed on the remote instance to install necessary dependencies 
       (aiohttp) and run the benchmarking script within the Python virtual environment.
    5. Output from the executed commands is printed for monitoring purposes.
    6. Finally, the SSH connection is closed.

    Parameters:
        instance_ip: The public IP address of the EC2 instance.
        load_balancer_url: The URL of the load balancer to test.
        pem_key_path: The path to the PEM key file for SSH authentication.
        user: The username for the SSH connection (default is 'ubuntu').

    Returns:
        None.

    Raises:
        Any exceptions raised during the SSH connection, SFTP transfer, or command execution 
        will be printed and handled accordingly.
    '''

    # Prepare the benchmarking script with the load balancer URL
    benchmark_script = f"""
import asyncio
import aiohttp
import time

async def call_endpoint_http(session, request_num):
    url = "{load_balancer_url}:8000"  # Load balancer URL here
    headers = {{'content-type': 'application/json'}}
    try:
        async with session.get(url, headers=headers) as response:
            status_code = response.status
            # Check content type before parsing as JSON
            if response.headers.get('content-type') == 'application/json':
                response_data = await response.json()
            else:
                response_data = await response.text()
            
            print(f"Request {{request_num}}: Status Code: {{status_code}}, Response: {{response_data}}")
            return status_code, response_data
    except Exception as e:
        print(f"Request {{request_num}}: Failed - {{str(e)}}")
        return None, str(e)

async def main():
    num_requests = 1000
    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        tasks = [call_endpoint_http(session, i) for i in range(num_requests)]
        await asyncio.gather(*tasks)

    end_time = time.time()
    total_time = end_time - start_time
    average_time = total_time / num_requests
    print(f"\\nTotal time taken: {{total_time:.2f}} seconds")
    print(f"Average time per request: {{average_time:.2f}} seconds")

if __name__ == "__main__":
    asyncio.run(main())
"""

    # Save the benchmark script to a file called 'benchmark.py'
    with open('benchmark.py', 'w') as f:
        f.write(benchmark_script)

    # Connect to the EC2 instance via SSH using Paramiko
    key = paramiko.RSAKey.from_private_key_file(pem_key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Automatically add the host key
    client.connect(hostname=instance_ip, username=user, pkey=key)

    # Transfer the 'benchmark.py' script to the EC2 instance using SFTP
    sftp = client.open_sftp()
    sftp.put('benchmark.py', '/home/ubuntu/benchmark.py')  # Place the script in the home directory
    sftp.close()

    # Commands to install aiohttp in the virtual environment and execute the benchmark script
    commands = [
        'bash -c "source /home/ubuntu/fastapi_env/bin/activate && pip install aiohttp"',  # Install aiohttp in the virtual environment
        'bash -c "source /home/ubuntu/fastapi_env/bin/activate && pip freeze | grep aiohttp"',  # Verify aiohttp installation
        'bash -c "source /home/ubuntu/fastapi_env/bin/activate && python3 /home/ubuntu/benchmark.py"'  # Run the benchmark script
    ]

    # Execute the commands on the remote EC2 instance
    for command in commands:
        stdin, stdout, stderr = client.exec_command(command)
        print(stdout.read().decode())  # Output from the command
        print(stderr.read().decode())  # Any error messages from the command

    # Close the SSH connection
    client.close()
