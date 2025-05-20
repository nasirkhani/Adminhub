# Apache Airflow Architecture Overview

## Introduction

Apache Airflow is a powerful platform designed to build and run workflows. At its core, Airflow represents workflows as **Directed Acyclic Graphs (DAGs)**, where individual pieces of work called **Tasks** are arranged with dependencies and data flows taken into consideration.

A DAG defines the relationships and execution order between tasks, while the tasks themselves describe the actual work to be performed - whether that's fetching data, running analysis, triggering external systems, or any other operation.

One of Airflow's key strengths is its agnosticism to the workloads it orchestrates. Airflow can schedule and manage virtually any type of task, either using high-level support from its providers or directly executing commands through shell or Python operators.

## Core Components

Airflow's architecture consists of several components that work together to provide workflow orchestration capabilities. These components can be categorized as either required or optional, depending on your deployment needs.

### Required Components

A minimal Airflow installation must include these four components:

1. **Scheduler**
   - Handles triggering of scheduled workflows
   - Submits tasks to the executor for execution
   - Contains the executor as a configuration property within its process
   - Various executor types are available out-of-the-box, and custom executors can be created

2. **Webserver**
   - Provides a user-friendly interface to:
     - Inspect DAGs and tasks
     - Trigger workflows manually
     - Debug workflow behavior
     - Monitor execution status

3. **DAG Files Repository**
   - A folder containing DAG definition files
   - Read by the scheduler to determine:
     - What tasks to run
     - When to run them
     - How to run them

4. **Metadata Database**
   - Used by all Airflow components to store state information
   - Tracks workflow and task execution status
   - Required for Airflow functionality
   - Setup is described in the "Set up a Database Backend" documentation

### Optional Components

To enhance extensibility, scalability, and performance, Airflow supports these optional components:

1. **Worker**
   - Executes tasks assigned by the scheduler
   - In basic installations, may be part of the scheduler rather than a separate component
   - Can run as:
     - A long-running process in the CeleryExecutor
     - A pod in the KubernetesExecutor

2. **Triggerer**
   - Executes deferred tasks in an asyncio event loop
   - Only necessary when using deferrable tasks
   - Enables more efficient resource utilization through task deferral
   - More information available in "Deferrable Operators & Triggers" documentation

3. **DAG Processor**
   - Parses DAG files and serializes them into the metadata database
   - By default, runs as part of the scheduler
   - Can be separated for improved:
     - Scalability
     - Security (isolating DAG parsing from execution)
   - When present, the scheduler doesn't need direct access to DAG files
   - More details in "DAG File Processing" documentation

4. **Plugins Folder**
   - Contains extensions to Airflow's functionality
   - Similar to installed packages
   - Read by the scheduler, DAG processor, triggerer, and webserver
   - Further information available in "Plugins" documentation

## Deployment Configurations

All Airflow components are Python applications that can be deployed using various mechanisms. They can be extended with additional Python packages to install custom operators, sensors, or plugins.

While Airflow can run on a single machine with a simple installation (scheduler and webserver only), it's designed to be scalable and secure in distributed environments. In distributed deployments:

- Various components can run on different machines
- Different security perimeters can be established
- Components can be scaled by running multiple instances

The separation of components enhances security by isolating them from each other and limiting their capabilities. For example, separating the DAG processor from the scheduler ensures that the scheduler doesn't have direct access to DAG files and cannot execute arbitrary code provided by DAG authors.

## User Roles in Airflow

In complex Airflow deployments, different users can interact with different parts of the system. The Airflow Security Model defines several key roles:

1. **Deployment Manager**
   - Installs and configures Airflow
   - Manages the overall deployment

2. **DAG Author**
   - Writes DAG definitions
   - Submits them to Airflow

3. **Operations User**
   - Triggers DAGs and tasks
   - Monitors execution

## Deployment Architectures

Airflow can be deployed in various configurations, from simple single-machine setups to complex distributed architectures with isolated security perimeters.

### Basic Airflow Deployment

The simplest deployment typically includes:
- Single machine operation
- LocalExecutor (scheduler and workers in the same Python process)
- DAG files read directly from the local filesystem
- Webserver on the same machine as the scheduler
- No triggerer component (task deferral not possible)
- No separation of user roles or security perimeters

This type of installation is ideal for:
- Development environments
- Small-scale production environments
- Single-user scenarios
- Learning and experimentation

For more complex deployment architectures, including distributed setups, multi-user environments, and enhanced security configurations, please refer to the complete Airflow documentation.

## Connection Types Between Components

Different components in Airflow communicate via several connection types:
- **DAG file submission and synchronization** (brown solid lines in diagrams)
- **Package and plugin deployment and access** (blue solid lines)
- **Worker control flow from scheduler via executor** (black dashed lines)
- **UI access for workflow management** (black solid lines)
- **Metadata database access by all components** (red dashed lines)

