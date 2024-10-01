# LOG8415 - Lab 1: Load Balancer and Benchmarking with AWS

## Description
This Lab implements a custom **Load Balancer** using AWS services (EC2, ELB, etc.) to manage two clusters of EC2 instances. The **FastAPI** application is deployed on each instance to handle incoming requests. The project also includes a benchmarking script to test the performance of the Load Balancer.

### Objectives:
1. Create EC2 instances in two clusters: `t2.micro` and `t2.large`.
2. Deploy a **FastAPI** application on each instance.
3. Create an **Application Load Balancer (ALB)** to route requests to both clusters.
4. Configure routing rules based on paths for each cluster.
5. Perform performance tests via a benchmarking script.

## Project Steps

### 1. **Create EC2 Clusters**
The project requires two clusters:
- **Cluster 1**: 1 EC2 instance of type `t2.micro`.
- **Cluster 2**: 1 EC2 instance of type `t2.large`.

### 2. **Deploy the FastAPI Application**
The **FastAPI** application will be deployed on each EC2 instance. Each instance will respond with its ID and the cluster it belongs to (Cluster 1 or Cluster 2).

#### Steps:
1. **Transfer and install FastAPI on EC2 instances**:
   - The FastAPI application is deployed on each instance via SSH using **Paramiko**.
   - Dependencies are installed, and the application is launched on port 8000.

### 3. **Create and Configure the Load Balancer**
An **Application Load Balancer (ALB)** is created to route requests to the two clusters. Each cluster is associated with a **Target Group**.

#### Steps:
1. **Create two Target Groups**: One for each cluster (Cluster 1 and Cluster 2).
2. **Create an Application Load Balancer (ALB)**: A Load Balancer that routes HTTP requests to the instances based on paths `/cluster1` and `/cluster2`.
3. **Create routing rules**:
   - Requests to `/cluster1` -> Instances in Cluster 1 (t2.micro).
   - Requests to `/cluster2` -> Instances in Cluster 2 (t2.large).

### 4. **Performance Tests and Benchmarking**
A **benchmarking** script sends multiple requests to the Load Balancer and measures the response time of the clusters.

#### Steps:
1. **Wait for the instances to be healthy**: The system waits for all instances in both clusters to be marked as "healthy" before proceeding with the tests.
2. **Run the benchmarking script**: The script sends requests to the Load Balancer and measures the average response time.

### 5. **Automation**
The script includes functions to automate the creation of instances, deployment of the application, configuration of the Load Balancer, and the execution of tests.

#### Command to run:
```bash
python main.py
