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


## Connection Types Between Components

Different components in Airflow communicate via several connection types:
- **DAG file submission and synchronization** (brown solid lines in diagrams)
- **Package and plugin deployment and access** (blue solid lines)
- **Worker control flow from scheduler via executor** (black dashed lines)
- **UI access for workflow management** (black solid lines)
- **Metadata database access by all components** (red dashed lines)


# Distributed Airflow Architecture

## Distributed Deployment Overview

In a distributed architecture, Airflow components are spread across multiple machines, enabling better scalability, performance, and security. This approach introduces distinct user roles and security perimeters to ensure proper isolation and access control.

## User Roles

A distributed Airflow deployment typically involves several distinct user roles, as defined in the Airflow Security Model:

1. **Deployment Manager**
   - Responsible for installation and configuration
   - Controls installed packages and plugins
   - Manages overall system architecture and security

2. **DAG Author**
   - Writes and submits workflow definitions
   - Creates custom operators and sensors
   - Defines task dependencies and data flows

3. **Operations User**
   - Uses the web interface to monitor workflows
   - Triggers DAGs and tasks
   - Tracks execution status and troubleshoots issues
   - Cannot author or modify DAGs

## Security Considerations

In distributed deployments, security becomes a critical consideration:

- **Webserver Isolation**: The webserver doesn't have direct access to DAG files
  - Code displayed in the UI's "Code" tab is read from the metadata database
  - The webserver cannot execute code submitted by DAG authors
  - It can only execute code installed as packages or plugins by the Deployment Manager

- **Operations User Limitations**: Operations users have restricted permissions
  - Can only trigger and monitor DAGs/tasks through the UI
  - Cannot author or modify DAG definitions

## DAG File Synchronization

DAG files must be synchronized across all components that use them (scheduler, triggerer, and workers). Various synchronization mechanisms are available:

- **Shared Storage**: Network file systems or mounted volumes
- **Git-Sync**: Automatically pull from a Git repository
- **Custom Synchronization**: Scripts or tools to distribute files
- **Container-Based Solutions**: Kubernetes with shared persistent volumes

Detailed synchronization methods are described in the "Manage DAG Files" documentation and in the Airflow Helm Chart documentation for Kubernetes deployments.

## Advanced Architecture: Separate DAG Processing

For environments with heightened security and isolation requirements, Airflow supports a standalone DAG processor component:

- **Isolation Benefits**:
  - Separates the scheduler from direct access to DAG files
  - Ensures DAG author-provided code never executes in the scheduler context
  - Provides additional security boundary

- **Operation**:
  - DAG processor parses DAG files and serializes them into the metadata database
  - Scheduler reads parsed DAG information from the database
  - No direct code execution from DAG files occurs in the scheduler process

> **Note**: When a DAG file changes, the scheduler and workers might temporarily see different versions until both components synchronize. To avoid issues, deactivate DAGs during deployment and reactivate once finished. The synchronization and scan frequency of the DAG folder can be configured, but changing these settings requires careful consideration.

## Airflow Workloads

Airflow workflows (DAGs) consist of a series of Tasks. There are three primary types of tasks:

### 1. Operators

- Predefined, templated tasks
- Ready-to-use building blocks for common operations
- Examples include:
  - `BashOperator` for running shell commands
  - `PythonOperator` for executing Python functions
  - `SqlOperator` for running SQL queries
  - Various provider-specific operators (AWS, GCP, etc.)

### 2. Sensors

- Special subclass of Operators
- Designed to wait for external events
- Examples include:
  - `FileSensor` for waiting for a file to appear
  - `SqlSensor` for waiting for a SQL query to return results
  - `ExternalTaskSensor` for waiting for another task to complete
  - Provider-specific sensors for external services

### 3. TaskFlow-Decorated Tasks

- Custom Python functions wrapped as Tasks using the `@task` decorator
- Part of the TaskFlow API introduced in Airflow 2.0
- Simplifies task creation and data passing between tasks
- Automatically handles XComs for data exchange

Internally, all these task types are subclasses of Airflow's `BaseOperator`. Conceptually, Operators and Sensors serve as templates, while Tasks are their instantiated forms within a specific DAG.

## Control Flow in DAGs

DAGs are designed for repeated execution, with multiple runs potentially happening in parallel. Each DAG run is parameterized with:

- A data interval (the time period the DAG is "running for")
- Optional additional parameters

### Task Dependencies

Tasks have dependencies that determine their execution order. These can be declared using:

#### Bitshift Operators
```python
# These are equivalent
first_task >> [second_task, third_task]
[second_task, third_task] << first_task

# As are these
fourth_task << third_task
third_task >> fourth_task
```

#### Method Calls
```python
# These are equivalent
first_task.set_downstream([second_task, third_task])
[second_task, third_task].set_upstream(first_task)

# As are these
fourth_task.set_upstream(third_task)
third_task.set_downstream(fourth_task)
```

These dependencies form the edges of the directed acyclic graph. By default, a task waits for all its upstream tasks to succeed before running, but this behavior can be customized with:

- **Branching**: Conditional execution paths
- **LatestOnly**: Only running for the most recent interval
- **Trigger Rules**: Custom conditions for task execution

### Data Passing Between Tasks

There are three methods to pass data between tasks:

1. **XComs** (Cross-communications)
   - A system for passing small bits of metadata between tasks
   - Best for small pieces of data (values, small dictionaries, etc.)
   - Stored in the metadata database

2. **External Storage**
   - Upload/download files from external storage services
   - Suitable for larger datasets
   - Can use cloud storage (S3, GCS, etc.) or self-hosted solutions

3. **TaskFlow API**
   - Automatically handles data passing via implicit XComs
   - Provides a more intuitive Python-native interface
   - Simplifies the code needed for inter-task communication

### Task Execution

Airflow dispatches tasks to workers as resources become available. This means:

- No guarantee that all tasks in a DAG will run on the same worker or machine
- Tasks must be designed with distributed execution in mind
- Shared resources should be accessed in a thread-safe manner

## Managing DAG Complexity

As DAGs grow in complexity, Airflow provides mechanisms to manage them:

1. **SubDAGs**
   - Reusable DAG components that can be embedded in other DAGs
   - Enable modular workflow design
   - Help standardize common patterns

2. **TaskGroups**
   - Visual organization of tasks in the UI
   - Group related tasks together for better visualization
   - Simplify complex DAG structures

These techniques help maintain DAG readability and manageability as workflows grow in size and complexity.
