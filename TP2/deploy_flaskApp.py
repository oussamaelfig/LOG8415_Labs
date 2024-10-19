import time
#for SCP transfer
import paramiko
import os
from scp import SCPClient



def progress(filename, size, sent):
    """
    Displays the progress of the file transfer in MB.
    
    Args:
    filename (str): The name of the file being transferred.
    size (int): The total size of the file in bytes.
    sent (int): The number of bytes sent so far.
    
    Returns:
    None
    """
    size_mb = size / (1024 * 1024)  # Convert bytes to megabytes
    sent_mb = sent / (1024 * 1024)  # Convert bytes to megabytes
    percentage = (sent / size) * 100
    print(f"{filename}: {sent_mb:.2f}/{size_mb:.2f} MB transferred ({percentage:.2f}%)")




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
        print("Command is ",command)
        stdin, stdout, stderr = client.exec_command(command, get_pty=True)
        stdout.channel.recv_exit_status()
        print(stdout.read().decode())
        print(stderr.read().decode())
    
    client.close()



# Function to transfer files via SCP (Paramiko)
def transfer_file(ip_address, username, private_key_path, local_filepath, remote_filepath):
    """
    Transfers a file from the local machine to the specified EC2 instance using SCP (via Paramiko),
    with progress reporting.

    Args:
    ip_address (str): The public IP address of the EC2 instance.
    username (str): The SSH username (usually 'ubuntu').
    private_key_path (str): Path to the private key (.pem) used to authenticate the SCP connection.
    local_filepath (str): The local path to the file that needs to be transferred.
    remote_filepath (str): The destination path on the EC2 instance where the file should be transferred.

    Returns:
    None: Transfers the file and displays the progress.
    """
    # Check if local file exists
    if not os.path.exists(local_filepath):
        print(f"Local file {local_filepath} does not exist")
        return
    
    # Load the private key
    key = paramiko.RSAKey.from_private_key_file(private_key_path)
    
    # Establish SSH connection
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ip_address, username=username, pkey=key)

    # Use SCPClient to transfer the file with progress callback
    print(f"Transferring {local_filepath} to {remote_filepath} on {ip_address}")
    try:
        with SCPClient(client.get_transport(), progress=progress) as scp:
            scp.put(local_filepath, remote_filepath)
            print("File transfer completed successfully.")
    except Exception as e:
        print(f"Failed to transfer file: {e}")
    
    # Close SSH connection
    client.close()



# Function to set up FastAPI app on the EC2 instance
def setup_ml_app(ip_address, username, private_key_path,container_start_port):
    """
    Sets up Docker containers on a worker, dynamically based on the number of containers per worker.
    Installs necessary packages, runs the containers, and returns their statuses, IP, and port information.

    Args:
        ip_address (str): The public IP address of the EC2 instance.
        username (str): The SSH username (usually 'ubuntu').
        private_key_path (str): Path to the private key (.pem) used for SSH.
        container_start_port (int): The starting port number for the first container on this worker.
        num_containers (int): The number of containers to run on this worker.

    Returns:
        dict: Information about the worker instance's IP, ports, and statuses for each container.
    """
    if not wait_for_ssh(ip_address, username, private_key_path):
        print(f"Failed to establish SSH connection to {ip_address}")
        return
   # Commands to format, mount the volume, and check disk usage
    

    commands = [
        "lsblk",#Seeing all disk
        "sudo mkdir /mnt/ebs",  # Create a mount point
        "sudo mkfs -t ext4 /dev/xvdf",  # Format it
        "sudo mount /dev/xvdf /mnt/ebs",  # Now mount volume to newly created directory
        "sudo chown -R ubuntu:ubuntu /mnt/ebs", #Give permission to Ubuntu use
        "ls -ld /mnt/ebs", #Verification
        "df -h"  # Check disk usage to verify the volume is mounted
    ]
    ssh_exec_command(ip_address, username, private_key_path, commands)
    # Installing docker
    commands = [
        'sudo apt-get update -y',
        # 'sudo apt-get install -y python3-pip python3-venv',
        #Install prerequisite packages for Docker
        'sudo apt-get install -y ca-certificates curl',
        #Add Docker’s GPG key
        'sudo install -m 0755 -d /etc/apt/keyrings',
        'sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc',
        'sudo chmod a+r /etc/apt/keyrings/docker.asc',
        # Add the Docker repository
        'echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null',
        # Update the apt package index again to include Docker’s repo
        'sudo apt-get update -y',
        # Install Docker Engine, CLI, and required plugins
        'sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin',
        'sudo docker run hello-world',
    ]
    ssh_exec_command(ip_address, username, private_key_path, commands)

    # Transfer tar images
    transfer_file(ip_address, username, private_key_path, './container1.tar.gz', '/mnt/ebs/container1.tar.gz')
    #Verifying installation
    commands=["df -h"]
    ssh_exec_command(ip_address, username, private_key_path, commands)

    # # Load the Docker image from the tar file
    
    commands = ['gzip -dc /mnt/ebs/container1.tar.gz | sudo docker load']
    ssh_exec_command(ip_address, username, private_key_path, commands)

    # Verify if the Docker image is loaded correctly
    commands = ['sudo docker images']
    ssh_exec_command(ip_address, username, private_key_path, commands)

    # Create a dictionary to store container information
    container_info = {}

    # Run container1 on port `container_start_port`
    container1_port = container_start_port
    print(f"Running container1 on port {container1_port}...")
    commands = [f'sudo docker run -d -p {container1_port}:{container1_port} container1:latest']
    ssh_exec_command(ip_address, username, private_key_path, commands)

    # Add container1 info to the dictionary
    container_info['container1'] = {
        "ip": ip_address,
        "port": str(container1_port),
        "status": "free"
    }

    # Run container2 on port `container_start_port + 1`
    # Run container2 on port `container_start_port + 1`
    container2_port = container_start_port + 1
    print(f"Running container2 on port {container2_port}...")
    commands = [f'sudo docker run -d --name container2 -p {container2_port}:{container2_port} container1:latest']
    ssh_exec_command(ip_address, username, private_key_path, commands)

    # Verify if we have 2 containers
    commands = ['sudo docker ps -a']
    ssh_exec_command(ip_address, username, private_key_path, commands)
    # Add container2 info to the dictionary
    container_info['container2'] = {
        "ip": ip_address,
        "port": str(container2_port),
        "status": "free"
    }

    # Return the container information for this worker
    print("Containers successfully started.")

    return container_info


def set_up_orchestrator(ip_address, username, private_key_path):
    #Verifying ssh connection
    if not wait_for_ssh(ip_address, username, private_key_path):
        print(f"Failed to establish SSH connection to {ip_address}")
        return
    

    commands = [
        "lsblk",#Seeing all disk
        "sudo mkdir /mnt/ebs",  # Create a mount point
        "sudo mkfs -t ext4 /dev/xvdf",  # Format it
        "sudo mount /dev/xvdf /mnt/ebs",  # Now mount volume to newly created directory
        "sudo chown -R ubuntu:ubuntu /mnt/ebs", #Give permission to Ubuntu use
        "ls -ld /mnt/ebs", #Verification
        "df -h"  # Check disk usage to verify the volume is mounted
    ]
    ssh_exec_command(ip_address, username, private_key_path, commands)
    # Installing docker
    commands = [
        'sudo apt-get update -y',
        # 'sudo apt-get install -y python3-pip python3-venv',
        #Install prerequisite packages for Docker
        'sudo apt-get install -y ca-certificates curl',
        #Add Docker’s GPG key
        'sudo install -m 0755 -d /etc/apt/keyrings',
        'sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc',
        'sudo chmod a+r /etc/apt/keyrings/docker.asc',
        # Add the Docker repository
        'echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null',
        # Update the apt package index again to include Docker’s repo
        'sudo apt-get update -y',
        # Install Docker Engine, CLI, and required plugins
        'sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin',
        'sudo docker run hello-world',
    ]
    ssh_exec_command(ip_address, username, private_key_path, commands)

    # Transfer tar images
    
    transfer_file(ip_address, username, private_key_path, './orchestrator.tar.gz', '/mnt/ebs/orchestrator.tar.gz')
    #Verifying installation
    commands=["df -h"]
    ssh_exec_command(ip_address, username, private_key_path, commands)

    # # Load the Docker image from the tar file
    commands = ['gzip -dc /mnt/ebs/orchestrator.tar.gz | sudo docker load']
    ssh_exec_command(ip_address, username, private_key_path, commands)

    # Verify if the Docker image is loaded correctly
    commands = ['sudo docker images']
    ssh_exec_command(ip_address, username, private_key_path, commands)
    
    #run container of orchestrator
    commands=['sudo docker run -d --name orchestrator_container -p 80:80 orchestrator']
    ssh_exec_command(ip_address, username, private_key_path, commands)

    # Verify if we have 2 containers
    commands = ['sudo docker ps -a']
    ssh_exec_command(ip_address, username, private_key_path, commands)


    





