import time
#for SCP transfer
import paramiko
import os





#SSH Connection 
def wait_for_ssh(ip_address, username, private_key_path, retries=10, delay=30):
    """
    Tries to establish an SSH connection to a given EC2 instance multiple times until successful or retries run out.

    Args:
    ip_address (str): The public IP address of the EC2 instance.
    username (str): The SSH username (usually 'ubuntu').
    private_key_path (str): Path to the private key (.pem) used to authenticate the SSH connection.
    retries (int): Number of retries before failing (default is 10).
    delay (int): Delay between retries in seconds (default is 30 seconds).

    Returns:
    bool: True if SSH connection is successful, False if all retries fail.
    """
    key = paramiko.RSAKey.from_private_key_file(private_key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for attempt in range(retries):
        try:
            print(f"Attempting SSH connection to {ip_address} (Attempt {attempt+1}/{retries})...")
            client.connect(hostname=ip_address, username=username, pkey=key, timeout=10)
            client.close()
            print(f"SSH connection to {ip_address} successful!")
            return True
        except paramiko.ssh_exception.NoValidConnectionsError as e:
            print(f"SSH connection failed: {e}")
        except paramiko.AuthenticationException as e:
            print(f"SSH Authentication failed: {e}")
        except paramiko.SSHException as e:
            print(f"General SSH error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        
        print(f"Waiting {delay} seconds before retrying...")
        time.sleep(delay)
    
    print(f"Unable to establish SSH connection to {ip_address} after {retries} attempts.")
    return False


# Function to execute SSH commands via Paramiko
def ssh_exec_command(ip_address, username, private_key_path, commands):
    """
    Executes a list of commands over SSH on the specified EC2 instance.

    Args:
    ip_address (str): The public IP address of the EC2 instance.
    username (str): The SSH username (usually 'ubuntu').
    private_key_path (str): Path to the private key (.pem) used to authenticate the SSH connection.
    commands (list): A list of shell commands (str) to be executed on the remote EC2 instance.

    Returns:
    None: Outputs the result of the executed commands to the console.
    """
    key = paramiko.RSAKey.from_private_key_file(private_key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip_address, username=username, pkey=key)
    
    for command in commands:
        stdin, stdout, stderr = client.exec_command(command, get_pty=True)
        stdout.channel.recv_exit_status()
        print(stdout.read().decode())
        print(stderr.read().decode())
    
    client.close()


# Function to create the FastAPI app Python file with the instance ID and cluster
def create_fastapi_app_file(instance_id, cluster_name):
    """
    Generates a FastAPI Python file with routes that respond based on the EC2 instance ID and cluster name.

    Args:
    instance_id (str): The EC2 instance ID to include in the response.
    cluster_name (str): The name of the cluster to create a route for (e.g., 'cluster1', 'cluster2').

    Returns:
    str: The local file path to the generated FastAPI app Python file.
    """
    app_content = f"""
from fastapi import FastAPI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

INSTANCE_ID = "{instance_id}"
CLUSTER_NAME = "{cluster_name}"

@app.get("/{cluster_name}")
async def cluster_route():
    message = f"Instance {{INSTANCE_ID}} is responding from {{CLUSTER_NAME}}"
    logger.info(message)
    return {{"message": message, "instance_id": INSTANCE_ID, "cluster": CLUSTER_NAME}}

@app.get("/")
async def root():
    message = f"Instance {{INSTANCE_ID}} has received the request"
    logger.info(message)
    return {{"message": message, "instance_id": INSTANCE_ID}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""
    #Save locally
    # Ensure the deployment directory exists
    os.makedirs('deployment', exist_ok=True)

    filename = f"deployment/main_{instance_id}.py"
    with open(filename, 'w') as f:
        f.write(app_content)
    return filename


# Function to transfer files via SCP (Paramiko)
def transfer_file(ip_address, username, private_key_path, local_filepath, remote_filepath):
    """
    Transfers a file from the local machine to the specified EC2 instance using SCP (via Paramiko).

    Args:
    ip_address (str): The public IP address of the EC2 instance.
    username (str): The SSH username (usually 'ubuntu').
    private_key_path (str): Path to the private key (.pem) used to authenticate the SCP connection.
    local_filepath (str): The local path to the file that needs to be transferred.
    remote_filepath (str): The destination path on the EC2 instance where the file should be transferred.

    Returns:
    None: Transfers the file and closes the connection.
    """
    key = paramiko.RSAKey.from_private_key_file(private_key_path)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip_address, username=username, pkey=key)
    scp = client.open_sftp()
    scp.put(local_filepath, remote_filepath)
    scp.close()
    client.close()



# Function to set up FastAPI app on the EC2 instance
def setup_fastapi_app(ip_address, username, private_key_path, instance_id, cluster_name):
    """
    Sets up a FastAPI application on the EC2 instance, including installing necessary packages and transferring app files.

    Args:
    ip_address (str): The public IP address of the EC2 instance.
    username (str): The SSH username (usually 'ubuntu').
    private_key_path (str): Path to the private key (.pem) used for SSH.
    instance_id (str): The ID of the EC2 instance, used to identify it in the app.
    cluster_name (str): The name of the cluster ('cluster1' or 'cluster2'), used to route requests accordingly.

    Returns:
    None: Executes the setup commands and deploys the FastAPI app on the EC2 instance.
    """
    if not wait_for_ssh(ip_address, username, private_key_path):
        print(f"Failed to establish SSH connection to {ip_address}")
        return
    
    # Commands to install Python, FastAPI, and tmux
    commands = [
        'sudo apt-get update -y',
        'sudo apt-get install python3-pip python3-venv tmux -y',
        'python3 -m venv fastapi_env',
        'bash -c "source fastapi_env/bin/activate && pip install fastapi uvicorn"'
    ]
    ssh_exec_command(ip_address, username, private_key_path, commands)

    # Transfer FastAPI app to the instance
    local_filepath = create_fastapi_app_file(instance_id, cluster_name)
    remote_filepath = '/home/ubuntu/main.py'
    transfer_file(ip_address, username, private_key_path, local_filepath, remote_filepath)

    # Run FastAPI in a tmux session to keep it alive
    tmux_command = 'tmux new-session -d -s fastapi_session "cd /home/ubuntu && source fastapi_env/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000"'
    ssh_exec_command(ip_address, username, private_key_path, [tmux_command])


