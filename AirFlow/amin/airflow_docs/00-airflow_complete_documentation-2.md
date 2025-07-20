# Airflow Complete CLI Documentation

Generated on: 2025-06-11 08:37:07

Airflow version: 2.9.0

---

## airflow

```
Usage: airflow [-h] GROUP_OR_COMMAND ...

Positional Arguments:
  GROUP_OR_COMMAND

    Groups
      celery         Celery components
      config         View configuration
      connections    Manage connections
      dags           Manage DAGs
      db             Database operations
      jobs           Manage jobs
      pools          Manage pools
      providers      Display providers
      roles          Manage roles
      tasks          Manage tasks
      users          Manage users
      variables      Manage variables

    Commands:
      cheat-sheet    Display cheat sheet
      dag-processor  Start a standalone Dag Processor instance
      info           Show information about current Airflow and environment
      kerberos       Start a kerberos ticket renewer
      plugins        Dump information about loaded plugins
      rotate-fernet-key
                     Rotate encrypted connection credentials and variables
      scheduler      Start a scheduler instance
      standalone     Run an all-in-one copy of Airflow
      sync-perm      Update permissions for existing roles and optionally DAGs
      triggerer      Start a triggerer instance
      version        Show the version
      webserver      Start a Airflow webserver instance

Optional Arguments:
  -h, --help         show this help message and exit
```

## airflow celery

```
Usage: airflow celery [-h] COMMAND ...

Start celery components. Works only when using CeleryExecutor. For more information, see https://airflow.apache.org/docs/apache-airflow/stable/executor/celery.html

Positional Arguments:
  COMMAND
    flower    Start a Celery Flower
    stop      Stop the Celery worker gracefully
    worker    Start a Celery worker node

Optional Arguments:
  -h, --help  show this help message and exit
```

### airflow celery flower

```
Usage: airflow celery flower [-h] [-A BASIC_AUTH] [-a BROKER_API] [-D]
                             [-c FLOWER_CONF] [-H HOSTNAME] [-l LOG_FILE]
                             [--pid [PID]] [-p PORT] [--stderr STDERR]
                             [--stdout STDOUT] [-u URL_PREFIX] [-v]

Start a Celery Flower

Optional Arguments:
  -h, --help            show this help message and exit
  -A, --basic-auth BASIC_AUTH
                        Securing Flower with Basic Authentication. Accepts user:password pairs separated by a comma. Example: flower_basic_auth = user1:password1,user2:password2
  -a, --broker-api BROKER_API
                        Broker API
  -D, --daemon          Daemonize instead of running in the foreground
  -c, --flower-conf FLOWER_CONF
                        Configuration file for flower
  -H, --hostname HOSTNAME
                        Set the hostname on which to run the server
  -l, --log-file LOG_FILE
                        Location of the log file
  --pid [PID]           PID file location
  -p, --port PORT       The port on which to run the server
  --stderr STDERR       Redirect stderr to this file
  --stdout STDOUT       Redirect stdout to this file
  -u, --url-prefix URL_PREFIX
                        URL prefix for Flower
  -v, --verbose         Make logging output more verbose
```

### airflow celery worker

```
Usage: airflow celery worker [-h] [-a AUTOSCALE] [-H CELERY_HOSTNAME]
                             [-c CONCURRENCY] [-D] [-l LOG_FILE] [--pid [PID]]
                             [-q QUEUES] [-s] [--stderr STDERR]
                             [--stdout STDOUT] [-u UMASK] [-v]
                             [--without-gossip] [--without-mingle]

Start a Celery worker node

Optional Arguments:
  -h, --help            show this help message and exit
  -a, --autoscale AUTOSCALE
                        Minimum and Maximum number of worker to autoscale
  -H, --celery-hostname CELERY_HOSTNAME
                        Set the hostname of celery worker if you have multiple workers on a single machine
  -c, --concurrency CONCURRENCY
                        The number of worker processes
  -D, --daemon          Daemonize instead of running in the foreground
  -l, --log-file LOG_FILE
                        Location of the log file
  --pid [PID]           PID file location
  -q, --queues QUEUES   Comma delimited list of queues to serve
  -s, --skip-serve-logs
                        Don't start the serve logs process along with the workers
  --stderr STDERR       Redirect stderr to this file
  --stdout STDOUT       Redirect stdout to this file
  -u, --umask UMASK     Set the umask of celery worker in daemon mode
  -v, --verbose         Make logging output more verbose
  --without-gossip      Don't subscribe to other workers events
  --without-mingle      Don't synchronize with other workers at start-up
```

## airflow config

```
Usage: airflow config [-h] COMMAND ...

View configuration

Positional Arguments:
  COMMAND
    get-value
              Print the value of the configuration
    list      List options for the configuration

Optional Arguments:
  -h, --help  show this help message and exit
```

### airflow config get

```
Usage: airflow config [-h] COMMAND ...

View configuration

Positional Arguments:
  COMMAND
    get-value
              Print the value of the configuration
    list      List options for the configuration

Optional Arguments:
  -h, --help  show this help message and exit

airflow config command error: argument COMMAND: invalid choice: 'get' (choose from 'get-value', 'list'), see help above.
```

### airflow config list

```
Usage: airflow config list [-h] [--color {auto,on,off}] [-c] [-a] [-p] [-d]
                           [-V] [-e] [-s] [--section SECTION] [-v]

List options for the configuration

Optional Arguments:
  -h, --help            show this help message and exit
  --color {auto,on,off}
                        Do emit colored output (default: auto)
  -c, --comment-out-everything
                        Comment out all configuration options. Useful as starting point for new installation
  -a, --defaults        Show only defaults - do not include local configuration, sources, includes descriptions, examples, variables. Comment out everything.
  -p, --exclude-providers
                        Exclude provider configuration (they are included by default)
  -d, --include-descriptions
                        Show descriptions for the configuration variables
  -V, --include-env-vars
                        Show environment variable for each option
  -e, --include-examples
                        Show examples for the configuration variables
  -s, --include-sources
                        Show source of the configuration variable
  --section SECTION     The section name
  -v, --verbose         Make logging output more verbose
```

## airflow connections

```
Usage: airflow connections [-h] COMMAND ...

Manage connections

Positional Arguments:
  COMMAND
    add                 Add a connection
    create-default-connections
                        Creates all the default connections from all the providers
    delete              Delete a connection
    export              Export all connections
    get                 Get a connection
    import              Import connections from a file
    list                List connections
    test                Test a connection

Optional Arguments:
  -h, --help            show this help message and exit
```

### airflow connections add

```
Usage: airflow connections add [-h] [--conn-description CONN_DESCRIPTION]
                               [--conn-extra CONN_EXTRA]
                               [--conn-host CONN_HOST] [--conn-json CONN_JSON]
                               [--conn-login CONN_LOGIN]
                               [--conn-password CONN_PASSWORD]
                               [--conn-port CONN_PORT]
                               [--conn-schema CONN_SCHEMA]
                               [--conn-type CONN_TYPE] [--conn-uri CONN_URI]
                               conn_id

Add a connection

Positional Arguments:
  conn_id               Connection id, required to get/add/delete/test a connection

Optional Arguments:
  -h, --help            show this help message and exit
  --conn-description CONN_DESCRIPTION
                        Connection description, optional when adding a connection
  --conn-extra CONN_EXTRA
                        Connection `Extra` field, optional when adding a connection
  --conn-host CONN_HOST
                        Connection host, optional when adding a connection
  --conn-json CONN_JSON
                        Connection JSON, required to add a connection using JSON representation
  --conn-login CONN_LOGIN
                        Connection login, optional when adding a connection
  --conn-password CONN_PASSWORD
                        Connection password, optional when adding a connection
  --conn-port CONN_PORT
                        Connection port, optional when adding a connection
  --conn-schema CONN_SCHEMA
                        Connection schema, optional when adding a connection
  --conn-type CONN_TYPE
                        Connection type, required to add a connection without conn_uri
  --conn-uri CONN_URI   Connection URI, required to add a connection without conn_type
```

### airflow connections delete

```
Usage: airflow connections delete [-h] [--color {auto,off,on}] [-v] conn_id

Delete a connection

Positional Arguments:
  conn_id               Connection id, required to get/add/delete/test a connection

Optional Arguments:
  -h, --help            show this help message and exit
  --color {auto,off,on}
                        Do emit colored output (default: auto)
  -v, --verbose         Make logging output more verbose
```

### airflow connections export

```
Usage: airflow connections export [-h] [--file-format {json,yaml,env}]
                                  [--format {json,yaml,env}]
                                  [--serialization-format {json,uri}] [-v]
                                  file

All connections can be exported in STDOUT using the following command:
airflow connections export -
The file format can be determined by the provided file extension. E.g., The following command will export the connections in JSON format:
airflow connections export /tmp/connections.json
The --file-format parameter can be used to control the file format. E.g., the default format is JSON in STDOUT mode, which can be overridden using:
airflow connections export - --file-format yaml
The --file-format parameter can also be used for the files, for example:
airflow connections export /tmp/connections --file-format json.
When exporting in `env` file format, you control whether URI format or JSON format is used to serialize the connection by passing `uri` or `json` with option `--serialization-format`.

Positional Arguments:
  file                  Output file path for exporting the connections

Optional Arguments:
  -h, --help            show this help message and exit
  --file-format {json,yaml,env}
                        File format for the export
  --format {json,yaml,env}
                        Deprecated -- use `--file-format` instead. File format to use for the export.
  --serialization-format {json,uri}
                        When exporting as `.env` format, defines how connections should be serialized. Default is `uri`.
  -v, --verbose         Make logging output more verbose
```

### airflow connections get

```
Usage: airflow connections get [-h] [--color {auto,on,off}]
                               [-o table, json, yaml, plain] [-v]
                               conn_id

Get a connection

Positional Arguments:
  conn_id               Connection id, required to get/add/delete/test a connection

Optional Arguments:
  -h, --help            show this help message and exit
  --color {auto,on,off}
                        Do emit colored output (default: auto)
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

### airflow connections import

```
Usage: airflow connections import [-h] [--overwrite] [-v] file

Connections can be imported from the output of the export command.
The filetype must by json, yaml or env and will be automatically inferred.

Positional Arguments:
  file           Import connections from a file

Optional Arguments:
  -h, --help     show this help message and exit
  --overwrite    Overwrite existing entries if a conflict occurs
  -v, --verbose  Make logging output more verbose
```

### airflow connections list

```
Usage: airflow connections list [-h] [--conn-id CONN_ID]
                                [-o table, json, yaml, plain] [-v]

List connections

Optional Arguments:
  -h, --help            show this help message and exit
  --conn-id CONN_ID     If passed, only items with the specified connection ID will be displayed
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

## airflow dags

```
Usage: airflow dags [-h] COMMAND ...

Manage DAGs

Positional Arguments:
  COMMAND
    backfill          Run subsections of a DAG for a specified date range
    delete            Delete all DB records related to the specified DAG
    details           Get DAG details given a DAG id
    list              List all the DAGs
    list-import-errors
                      List all the DAGs that have import errors
    list-jobs         List the jobs
    list-runs         List DAG runs given a DAG id
    next-execution    Get the next execution datetimes of a DAG
    pause             Pause DAG(s)
    report            Show DagBag loading report
    reserialize       Reserialize all DAGs by parsing the DagBag files
    show              Displays DAG's tasks with their dependencies
    show-dependencies
                      Displays DAGs with their dependencies
    state             Get the status of a dag run
    test              Execute one single DagRun
    trigger           Trigger a new DAG run. If DAG is paused then dagrun state will remain queued, and the task won't run.
    unpause           Resume paused DAG(s)

Optional Arguments:
  -h, --help          show this help message and exit
```

### airflow dags backfill

```
Usage: airflow dags backfill [-h] [-c CONF] [--continue-on-failures]
                             [--delay-on-limit DELAY_ON_LIMIT]
                             [--disable-retry] [-x] [-n] [-e END_DATE] [-i]
                             [-I] [-l] [-m] [--pool POOL]
                             [--rerun-failed-tasks] [--reset-dagruns] [-B]
                             [-s START_DATE] [-S SUBDIR] [-t TASK_REGEX]
                             [--treat-dag-as-regex] [--treat-dag-id-as-regex]
                             [-v] [-y]
                             dag_id

Run subsections of a DAG for a specified date range. If reset_dag_run option is used, backfill will first prompt users whether airflow should clear all the previous dag_run and task_instances within the backfill date range. If rerun_failed_tasks is used, backfill will auto re-run the previous failed task instances  within the backfill date range

Positional Arguments:
  dag_id                The id of the dag

Optional Arguments:
  -h, --help            show this help message and exit
  -c, --conf CONF       JSON string that gets pickled into the DagRun's conf attribute
  --continue-on-failures
                        if set, the backfill will keep going even if some of the tasks failed
  --delay-on-limit DELAY_ON_LIMIT
                        Amount of time in seconds to wait when the limit on maximum active dag runs (max_active_runs) has been reached before trying to execute a dag run again
  --disable-retry       if set, the backfill will set tasks as failed without retrying.
  -x, --donot-pickle    Do not attempt to pickle the DAG object to send over to the workers, just tell the workers to run their version of the code
  -n, --dry-run         Perform a dry run for each task. Only renders Template Fields for each task, nothing else
  -e, --end-date END_DATE
                        Override end_date YYYY-MM-DD
  -i, --ignore-dependencies
                        Skip upstream tasks, run only the tasks matching the regexp. Only works in conjunction with task_regex
  -I, --ignore-first-depends-on-past
                        Ignores depends_on_past dependencies for the first set of tasks only (subsequent executions in the backfill DO respect depends_on_past)
  -l, --local           Run the task using the LocalExecutor
  -m, --mark-success    Mark jobs as succeeded without running them
  --pool POOL           Resource pool to use
  --rerun-failed-tasks  if set, the backfill will auto-rerun all the failed tasks for the backfill date range instead of throwing exceptions
  --reset-dagruns       if set, the backfill will delete existing backfill-related DAG runs and start anew with fresh, running DAG runs
  -B, --run-backwards   if set, the backfill will run tasks from the most recent day first.  if there are tasks that depend_on_past this option will throw an exception
  -s, --start-date START_DATE
                        Override start_date YYYY-MM-DD
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -t, --task-regex TASK_REGEX
                        The regex to filter specific task_ids (optional)
  --treat-dag-as-regex  Deprecated -- use `--treat-dag-id-as-regex` instead
  --treat-dag-id-as-regex
                        if set, dag_id will be treated as regex instead of an exact string
  -v, --verbose         Make logging output more verbose
  -y, --yes             Do not prompt to confirm. Use with care!
```

### airflow dags delete

```
Usage: airflow dags delete [-h] [-v] [-y] dag_id

Delete all DB records related to the specified DAG

Positional Arguments:
  dag_id         The id of the dag

Optional Arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Make logging output more verbose
  -y, --yes      Do not prompt to confirm. Use with care!
```

### airflow dags details

```
Usage: airflow dags details [-h] [-o table, json, yaml, plain] [-v] dag_id

Get DAG details given a DAG id

Positional Arguments:
  dag_id                The id of the dag

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

### airflow dags list

```
Usage: airflow dags list [-h] [--columns COLUMNS]
                         [-o table, json, yaml, plain] [-S SUBDIR] [-v]

List all the DAGs

Optional Arguments:
  -h, --help            show this help message and exit
  --columns COLUMNS     List of columns to render. (default: ['dag_id', 'fileloc', 'owner', 'is_paused'])
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -v, --verbose         Make logging output more verbose
```

### airflow dags list-import-errors

```
Usage: airflow dags list-import-errors [-h] [-o table, json, yaml, plain]
                                       [-S SUBDIR] [-v]

List all the DAGs that have import errors

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -v, --verbose         Make logging output more verbose
```

### airflow dags list-jobs

```
Usage: airflow dags list-jobs [-h] [-d DAG_ID] [--limit LIMIT]
                              [-o table, json, yaml, plain]
                              [--state running, success, restarting, failed]
                              [-v]

List the jobs

Optional Arguments:
  -h, --help            show this help message and exit
  -d, --dag-id DAG_ID   The id of the dag
  --limit LIMIT         Return a limited number of records
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  --state running, success, restarting, failed
                        Only list the jobs corresponding to the state
  -v, --verbose         Make logging output more verbose
```

### airflow dags list-runs

```
Usage: airflow dags list-runs [-h] -d DAG_ID [-e END_DATE] [--no-backfill]
                              [-o table, json, yaml, plain] [-s START_DATE]
                              [--state queued, running, success, failed] [-v]

List DAG runs given a DAG id. If state option is given, it will only search for all the dagruns with the given state. If no_backfill option is given, it will filter out all backfill dagruns for given dag id. If start_date is given, it will filter out all the dagruns that were executed before this date. If end_date is given, it will filter out all the dagruns that were executed after this date.

Optional Arguments:
  -h, --help            show this help message and exit
  -d, --dag-id DAG_ID   The id of the dag
  -e, --end-date END_DATE
                        Override end_date YYYY-MM-DD
  --no-backfill         filter all the backfill dagruns given the dag id
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -s, --start-date START_DATE
                        Override start_date YYYY-MM-DD
  --state queued, running, success, failed
                        Only list the DAG runs corresponding to the state
  -v, --verbose         Make logging output more verbose
```

### airflow dags next-execution

```
Usage: airflow dags next-execution [-h] [-n NUM_EXECUTIONS] [-S SUBDIR] [-v]
                                   dag_id

Get the next execution datetimes of a DAG. It returns one execution unless the num-executions option is given

Positional Arguments:
  dag_id                The id of the dag

Optional Arguments:
  -h, --help            show this help message and exit
  -n, --num-executions NUM_EXECUTIONS
                        The number of next execution datetimes to show
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -v, --verbose         Make logging output more verbose
```

### airflow dags pause

```
Usage: airflow dags pause [-h] [-o table, json, yaml, plain] [-S SUBDIR]
                          [--treat-dag-id-as-regex] [-v] [-y]
                          dag_id

Pause one or more DAGs. This command allows to halt the execution of specified DAGs, disabling further task scheduling. Use `--treat-dag-id-as-regex` to target multiple DAGs by treating the `--dag-id` as a regex pattern.

Positional Arguments:
  dag_id                The id of the dag

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  --treat-dag-id-as-regex
                        if set, dag_id will be treated as regex instead of an exact string
  -v, --verbose         Make logging output more verbose
  -y, --yes             Do not prompt to confirm. Use with care!
```

### airflow dags report

```
Usage: airflow dags report [-h] [-o table, json, yaml, plain] [-S SUBDIR] [-v]

Show DagBag loading report

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -v, --verbose         Make logging output more verbose
```

### airflow dags reserialize

```
Usage: airflow dags reserialize [-h] [--clear-only] [-S SUBDIR] [-v]

Drop all serialized dags from the metadata DB. This will cause all DAGs to be reserialized from the DagBag folder. This can be helpful if your serialized DAGs get out of sync with the version of Airflow that you are running.

Optional Arguments:
  -h, --help            show this help message and exit
  --clear-only          If passed, serialized DAGs will be cleared but not reserialized.
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -v, --verbose         Make logging output more verbose
```

### airflow dags show

```
Usage: airflow dags show [-h] [--imgcat] [-s SAVE] [-S SUBDIR] [-v] dag_id

The --imgcat option only works in iTerm.

For more information, see: https://www.iterm2.com/documentation-images.html

The --save option saves the result to the indicated file.

The file format is determined by the file extension. For more information about supported format, see: https://www.graphviz.org/doc/info/output.html

If you want to create a PNG file then you should execute the following command:
airflow dags show <DAG_ID> --save output.png

If you want to create a DOT file then you should execute the following command:
airflow dags show <DAG_ID> --save output.dot

Positional Arguments:
  dag_id                The id of the dag

Optional Arguments:
  -h, --help            show this help message and exit
  --imgcat              Displays graph using the imgcat tool.
  -s, --save SAVE       Saves the result to the indicated file.
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -v, --verbose         Make logging output more verbose
```

### airflow dags show-dependencies

```
Usage: airflow dags show-dependencies [-h] [--imgcat] [-s SAVE] [-S SUBDIR]
                                      [-v]

The --imgcat option only works in iTerm.

For more information, see: https://www.iterm2.com/documentation-images.html

The --save option saves the result to the indicated file.

The file format is determined by the file extension. For more information about supported format, see: https://www.graphviz.org/doc/info/output.html

If you want to create a PNG file then you should execute the following command:
airflow dags show-dependencies --save output.png

If you want to create a DOT file then you should execute the following command:
airflow dags show-dependencies --save output.dot

Optional Arguments:
  -h, --help            show this help message and exit
  --imgcat              Displays graph using the imgcat tool.
  -s, --save SAVE       Saves the result to the indicated file.
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -v, --verbose         Make logging output more verbose
```

### airflow dags state

```
Usage: airflow dags state [-h] [-S SUBDIR] [-v] dag_id execution_date

Get the status of a dag run

Positional Arguments:
  dag_id                The id of the dag
  execution_date        The execution date of the DAG

Optional Arguments:
  -h, --help            show this help message and exit
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -v, --verbose         Make logging output more verbose
```

### airflow dags test

```
Usage: airflow dags test [-h] [-c CONF] [--imgcat-dagrun]
                         [--save-dagrun SAVE_DAGRUN] [--show-dagrun]
                         [-S SUBDIR] [-v]
                         dag_id [execution_date]

Execute one single DagRun for a given DAG and execution date.

The --imgcat-dagrun option only works in iTerm.

For more information, see: https://www.iterm2.com/documentation-images.html

If --save-dagrun is used, then, after completing the backfill, saves the diagram for current DAG Run to the indicated file.
The file format is determined by the file extension. For more information about supported format, see: https://www.graphviz.org/doc/info/output.html

If you want to create a PNG file then you should execute the following command:
airflow dags test <DAG_ID> <EXECUTION_DATE> --save-dagrun output.png

If you want to create a DOT file then you should execute the following command:
airflow dags test <DAG_ID> <EXECUTION_DATE> --save-dagrun output.dot

Positional Arguments:
  dag_id                The id of the dag
  execution_date        The execution date of the DAG (optional)

Optional Arguments:
  -h, --help            show this help message and exit
  -c, --conf CONF       JSON string that gets pickled into the DagRun's conf attribute
  --imgcat-dagrun       After completing the dag run, prints a diagram on the screen for the current DAG Run using the imgcat tool.
  --save-dagrun SAVE_DAGRUN
                        After completing the backfill, saves the diagram for current DAG Run to the indicated file.

  --show-dagrun         After completing the backfill, shows the diagram for current DAG Run.

                        The diagram is in DOT language
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -v, --verbose         Make logging output more verbose
```

### airflow dags trigger

```
Usage: airflow dags trigger [-h] [-c CONF] [-e EXEC_DATE]
                            [--no-replace-microseconds]
                            [-o table, json, yaml, plain] [-r RUN_ID]
                            [-S SUBDIR] [-v]
                            dag_id

Trigger a new DAG run. If DAG is paused then dagrun state will remain queued, and the task won't run.

Positional Arguments:
  dag_id                The id of the dag

Optional Arguments:
  -h, --help            show this help message and exit
  -c, --conf CONF       JSON string that gets pickled into the DagRun's conf attribute
  -e, --exec-date EXEC_DATE
                        The execution date of the DAG
  --no-replace-microseconds
                        whether microseconds should be zeroed
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -r, --run-id RUN_ID   Helps to identify this run
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -v, --verbose         Make logging output more verbose
```

### airflow dags unpause

```
Usage: airflow dags unpause [-h] [-o table, json, yaml, plain] [-S SUBDIR]
                            [--treat-dag-id-as-regex] [-v] [-y]
                            dag_id

Resume one or more DAGs. This command allows to restore the execution of specified DAGs, enabling further task scheduling. Use `--treat-dag-id-as-regex` to target multiple DAGs treating the `--dag-id` as a regex pattern.

Positional Arguments:
  dag_id                The id of the dag

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  --treat-dag-id-as-regex
                        if set, dag_id will be treated as regex instead of an exact string
  -v, --verbose         Make logging output more verbose
  -y, --yes             Do not prompt to confirm. Use with care!
```

## airflow db

```
Usage: airflow db [-h] COMMAND ...

Database operations

Positional Arguments:
  COMMAND
    check           Check if the database can be reached
    check-migrations
                    Check if migration have finished
    clean           Purge old records in metastore tables
    downgrade       Downgrade the schema of the metadata database.
    drop-archived   Drop archived tables created through the db clean command
    export-archived
                    Export archived data from the archive tables
    migrate         Migrates the metadata database to the latest version
    reset           Burn down and rebuild the metadata database
    shell           Runs a shell to access the database

Optional Arguments:
  -h, --help        show this help message and exit
```

### airflow db check

```
Usage: airflow db check [-h] [--retry RETRY] [--retry-delay RETRY_DELAY] [-v]

Check if the database can be reached

Optional Arguments:
  -h, --help            show this help message and exit
  --retry RETRY         Retry database check upon failure
  --retry-delay RETRY_DELAY
                        Wait time between retries in seconds
  -v, --verbose         Make logging output more verbose
```

### airflow db clean

```
Usage: airflow db clean [-h] --clean-before-timestamp CLEAN_BEFORE_TIMESTAMP
                        [--dry-run] [--skip-archive] [-t TABLES] [-v] [-y]

Purge old records in metastore tables

Optional Arguments:
  -h, --help            show this help message and exit
  --clean-before-timestamp CLEAN_BEFORE_TIMESTAMP
                        The date or timestamp before which data should be purged.
                        If no timezone info is supplied then dates are assumed to be in airflow default timezone.
                        Example: '2022-01-01 00:00:00+01:00'
  --dry-run             Perform a dry run
  --skip-archive        Don't preserve purged records in an archive table.
  -t, --tables TABLES   Table names to perform maintenance on (use comma-separated list).
                        Options: ['callback_request', 'celery_taskmeta', 'celery_tasksetmeta', 'dag', 'dag_run', 'dataset_event', 'import_error', 'job', 'log', 'session', 'sla_miss', 'task_fail', 'task_instance', 'task_reschedule', 'trigger', 'xcom']
  -v, --verbose         Make logging output more verbose
  -y, --yes             Do not prompt to confirm. Use with care!
```

### airflow db downgrade

```
Usage: airflow db downgrade [-h] [--from-revision FROM_REVISION]
                            [--from-version FROM_VERSION] [-s]
                            [-r TO_REVISION] [-n TO_VERSION] [-v] [-y]

Downgrade the schema of the metadata database. You must provide either `--to-revision` or `--to-version`. To print but not execute commands, use option `--show-sql-only`. If using options `--from-revision` or `--from-version`, you must also use `--show-sql-only`, because if actually *running* migrations, we should only migrate from the *current* Alembic revision.

Optional Arguments:
  -h, --help            show this help message and exit
  --from-revision FROM_REVISION
                        (Optional) If generating sql, may supply a *from* Alembic revision
  --from-version FROM_VERSION
                        (Optional) If generating sql, may supply a *from* version
  -s, --show-sql-only   Don't actually run migrations; just print out sql scripts for offline migration. Required if using either `--from-revision` or `--from-version`.
  -r, --to-revision TO_REVISION
                        The Alembic revision to downgrade to. Note: must provide either `--to-revision` or `--to-version`.
  -n, --to-version TO_VERSION
                        (Optional) If provided, only run migrations up to this version.
  -v, --verbose         Make logging output more verbose
  -y, --yes             Do not prompt to confirm. Use with care!
```

#### airflow db downgrade --to-revision

This command requires additional parameters. Example usage:

```
airflow db downgrade --to-revision [VALUE]
```

#### airflow db downgrade --from-revision

This command requires additional parameters. Example usage:

```
airflow db downgrade --from-revision [VALUE]
```

#### airflow db downgrade --show-sql-only

This command requires additional parameters. Example usage:

```
airflow db downgrade --show-sql-only [VALUE]
```

### airflow db init

```
Usage: airflow db init [-h] [-v]

Optional Arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Make logging output more verbose
```

### airflow db reset

```
Usage: airflow db reset [-h] [-s] [-v] [-y]

Burn down and rebuild the metadata database

Optional Arguments:
  -h, --help       show this help message and exit
  -s, --skip-init  Only remove tables; do not perform db init.
  -v, --verbose    Make logging output more verbose
  -y, --yes        Do not prompt to confirm. Use with care!
```

#### airflow db reset --skip-init

This command requires additional parameters. Example usage:

```
airflow db reset --skip-init [VALUE]
```

### airflow db upgrade

```
Usage: airflow db upgrade [-h] [--from-revision FROM_REVISION]
                          [--from-version FROM_VERSION] [-s] [-r TO_REVISION]
                          [-n TO_VERSION] [-v]

Optional Arguments:
  -h, --help            show this help message and exit
  --from-revision FROM_REVISION
                        (Optional) If generating sql, may supply a *from* Alembic revision
  --from-version FROM_VERSION
                        (Optional) If generating sql, may supply a *from* version
  -s, --show-sql-only   Don't actually run migrations; just print out sql scripts for offline migration. Required if using either `--from-revision` or `--from-version`.
  -r, --to-revision TO_REVISION
                        (Optional) If provided, only run migrations up to and including this Alembic revision.
  -n, --to-version TO_VERSION
                        (Optional) The airflow version to upgrade to. Note: must provide either `--to-revision` or `--to-version`.
  -v, --verbose         Make logging output more verbose
```

#### airflow db upgrade --to-revision

This command requires additional parameters. Example usage:

```
airflow db upgrade --to-revision [VALUE]
```

#### airflow db upgrade --from-revision

This command requires additional parameters. Example usage:

```
airflow db upgrade --from-revision [VALUE]
```

#### airflow db upgrade --show-sql-only

This command requires additional parameters. Example usage:

```
airflow db upgrade --show-sql-only [VALUE]
```

## airflow jobs

```
Usage: airflow jobs [-h] COMMAND ...

Manage jobs

Positional Arguments:
  COMMAND
    check     Checks if job(s) are still alive

Optional Arguments:
  -h, --help  show this help message and exit
```

### airflow jobs check

```
Usage: airflow jobs check [-h] [--allow-multiple] [--hostname HOSTNAME]
                          [--job-type {BackfillJob,LocalTaskJob,SchedulerJob,TriggererJob,DagProcessorJob}]
                          [--limit LIMIT] [--local] [-v]

Checks if job(s) are still alive

Optional Arguments:
  -h, --help            show this help message and exit
  --allow-multiple      If passed, this command will be successful even if multiple matching alive jobs are found.
  --hostname HOSTNAME   The hostname of job(s) that will be checked.
  --job-type {BackfillJob,LocalTaskJob,SchedulerJob,TriggererJob,DagProcessorJob}
                        The type of job(s) that will be checked.
  --limit LIMIT         The number of recent jobs that will be checked. To disable limit, set 0.
  --local               If passed, this command will only show jobs from the local host (those with a hostname matching what `hostname_callable` returns).
  -v, --verbose         Make logging output more verbose

examples:
To check if the local scheduler is still working properly, run:

    $ airflow jobs check --job-type SchedulerJob --local"

To check if any scheduler is running when you are using high availability, run:

    $ airflow jobs check --job-type SchedulerJob --allow-multiple --limit 100
```

### airflow jobs list

```
Usage: airflow jobs [-h] COMMAND ...

Manage jobs

Positional Arguments:
  COMMAND
    check     Checks if job(s) are still alive

Optional Arguments:
  -h, --help  show this help message and exit

airflow jobs command error: argument COMMAND: invalid choice: 'list' (choose from 'check'), see help above.
```

## airflow pools

```
Usage: airflow pools [-h] COMMAND ...

Manage pools

Positional Arguments:
  COMMAND
    delete    Delete pool
    export    Export all pools
    get       Get pool size
    import    Import pools
    list      List pools
    set       Configure pool

Optional Arguments:
  -h, --help  show this help message and exit
```

### airflow pools delete

```
Usage: airflow pools delete [-h] [-o table, json, yaml, plain] [-v] NAME

Delete pool

Positional Arguments:
  NAME                  Pool name

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

### airflow pools export

```
Usage: airflow pools export [-h] [-v] FILEPATH

Export all pools

Positional Arguments:
  FILEPATH       Export all pools to JSON file

Optional Arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Make logging output more verbose
```

### airflow pools get

```
Usage: airflow pools get [-h] [-o table, json, yaml, plain] [-v] NAME

Get pool size

Positional Arguments:
  NAME                  Pool name

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

### airflow pools import

```
Usage: airflow pools import [-h] [-v] FILEPATH

Import pools

Positional Arguments:
  FILEPATH       Import pools from JSON file. Example format::

                     {
                         "pool_1": {"slots": 5, "description": "", "include_deferred": true},
                         "pool_2": {"slots": 10, "description": "test", "include_deferred": false}
                     }

Optional Arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Make logging output more verbose
```

### airflow pools list

```
Usage: airflow pools list [-h] [-o table, json, yaml, plain] [-v]

List pools

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

### airflow pools set

```
Usage: airflow pools set [-h] [--include-deferred]
                         [-o table, json, yaml, plain] [-v]
                         NAME slots description

Configure pool

Positional Arguments:
  NAME                  Pool name
  slots                 Pool slots
  description           Pool description

Optional Arguments:
  -h, --help            show this help message and exit
  --include-deferred    Include deferred tasks in calculations for Pool
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

## airflow providers

```
Usage: airflow providers [-h] COMMAND ...

Display providers

Positional Arguments:
  COMMAND
    auth         Get information about API auth backends provided
    auth-managers
                 Get information about auth managers provided
    behaviours   Get information about registered connection types with custom behaviours
    configs      Get information about provider configuration
    executors    Get information about executors provided
    get          Get detailed information about a provider
    hooks        List registered provider hooks
    lazy-loaded  Checks that provider configuration is lazy loaded
    links        List extra links registered by the providers
    list         List installed providers
    logging      Get information about task logging handlers provided
    notifications
                 Get information about notifications provided
    secrets      Get information about secrets backends provided
    triggers     List registered provider triggers
    widgets      Get information about registered connection form widgets

Optional Arguments:
  -h, --help     show this help message and exit
```

### airflow providers behaviors

```
Usage: airflow providers [-h] COMMAND ...

Display providers

Positional Arguments:
  COMMAND
    auth         Get information about API auth backends provided
    auth-managers
                 Get information about auth managers provided
    behaviours   Get information about registered connection types with custom behaviours
    configs      Get information about provider configuration
    executors    Get information about executors provided
    get          Get detailed information about a provider
    hooks        List registered provider hooks
    lazy-loaded  Checks that provider configuration is lazy loaded
    links        List extra links registered by the providers
    list         List installed providers
    logging      Get information about task logging handlers provided
    notifications
                 Get information about notifications provided
    secrets      Get information about secrets backends provided
    triggers     List registered provider triggers
    widgets      Get information about registered connection form widgets

Optional Arguments:
  -h, --help     show this help message and exit

airflow providers command error: argument COMMAND: invalid choice: 'behaviors' (choose from 'auth', 'auth-managers', 'behaviours', 'configs', 'executors', 'get', 'hooks', 'lazy-loaded', 'links', 'list', 'logging', 'notifications', 'secrets', 'triggers', 'widgets'), see help above.
```

### airflow providers get

```
Usage: airflow providers get [-h] [--color {on,auto,off}] [-f]
                             [-o table, json, yaml, plain] [-v]
                             provider_name

Get detailed information about a provider

Positional Arguments:
  provider_name         Provider name, required to get provider information

Optional Arguments:
  -h, --help            show this help message and exit
  --color {on,auto,off}
                        Do emit colored output (default: auto)
  -f, --full            Full information about the provider, including documentation information.
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

### airflow providers hooks

```
Usage: airflow providers hooks [-h] [-o table, json, yaml, plain] [-v]

List registered provider hooks

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

### airflow providers links

```
Usage: airflow providers links [-h] [-o table, json, yaml, plain] [-v]

List extra links registered by the providers

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

### airflow providers list

```
Usage: airflow providers list [-h] [-o table, json, yaml, plain] [-v]

List installed providers

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

### airflow providers widgets

```
Usage: airflow providers widgets [-h] [-o table, json, yaml, plain] [-v]

Get information about registered connection form widgets

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

## airflow roles

```
Usage: airflow roles [-h] COMMAND ...

Manage roles

Positional Arguments:
  COMMAND
    add-perms
              Add roles permissions
    create    Create role
    del-perms
              Delete roles permissions
    delete    Delete role
    export    Export roles (without permissions) from db to JSON file
    import    Import roles (without permissions) from JSON file to db
    list      List roles

Optional Arguments:
  -h, --help  show this help message and exit
```

### airflow roles create

```
Usage: airflow roles create [-h] [-v] [role ...]

Create role

Positional Arguments:
  role           The name of a role

Optional Arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Make logging output more verbose
```

### airflow roles delete

```
Usage: airflow roles delete [-h] [-v] [role ...]

Delete role

Positional Arguments:
  role           The name of a role

Optional Arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Make logging output more verbose
```

### airflow roles export

```
Usage: airflow roles export [-h] [-p] [-v] file

Export roles (without permissions) from db to JSON file

Positional Arguments:
  file           Export all roles to JSON file

Optional Arguments:
  -h, --help     show this help message and exit
  -p, --pretty   Format output JSON file by sorting role names and indenting by 4 spaces
  -v, --verbose  Make logging output more verbose
```

### airflow roles import

```
Usage: airflow roles import [-h] [-v] file

Import roles (without permissions) from JSON file to db

Positional Arguments:
  file           Import roles from JSON file

Optional Arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Make logging output more verbose
```

### airflow roles list

```
Usage: airflow roles list [-h] [-o table, json, yaml, plain] [-p] [-v]

List roles

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -p, --permission      Show role permissions
  -v, --verbose         Make logging output more verbose
```

## airflow tasks

```
Usage: airflow tasks [-h] COMMAND ...

Manage tasks

Positional Arguments:
  COMMAND
    clear             Clear a set of task instance, as if they never ran
    failed-deps       Returns the unmet dependencies for a task instance
    list              List the tasks within a DAG
    render            Render a task instance's template(s)
    run               Run a single task instance
    state             Get the status of a task instance
    states-for-dag-run
                      Get the status of all task instances in a dag run
    test              Test a task instance

Optional Arguments:
  -h, --help          show this help message and exit
```

### airflow tasks clear

```
Usage: airflow tasks clear [-h] [-R] [-d] [-e END_DATE] [-X] [-x] [-f] [-r]
                           [-s START_DATE] [-S SUBDIR] [-t TASK_REGEX] [-u]
                           [-v] [-y]
                           dag_id

Clear a set of task instance, as if they never ran

Positional Arguments:
  dag_id                The id of the dag

Optional Arguments:
  -h, --help            show this help message and exit
  -R, --dag-regex       Search dag_id as regex instead of exact string
  -d, --downstream      Include downstream tasks
  -e, --end-date END_DATE
                        Override end_date YYYY-MM-DD
  -X, --exclude-parentdag
                        Exclude ParentDAGS if the task cleared is a part of a SubDAG
  -x, --exclude-subdags
                        Exclude subdags
  -f, --only-failed     Only failed jobs
  -r, --only-running    Only running jobs
  -s, --start-date START_DATE
                        Override start_date YYYY-MM-DD
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -t, --task-regex TASK_REGEX
                        The regex to filter specific task_ids (optional)
  -u, --upstream        Include upstream tasks
  -v, --verbose         Make logging output more verbose
  -y, --yes             Do not prompt to confirm. Use with care!
```

### airflow tasks failed-deps

```
Usage: airflow tasks failed-deps [-h] [--map-index MAP_INDEX] [-S SUBDIR] [-v]
                                 dag_id task_id execution_date_or_run_id

Returns the unmet dependencies for a task instance from the perspective of the scheduler. In other words, why a task instance doesn't get scheduled and then queued by the scheduler, and then run by an executor.

Positional Arguments:
  dag_id                The id of the dag
  task_id               The id of the task
  execution_date_or_run_id
                        The execution_date of the DAG or run_id of the DAGRun

Optional Arguments:
  -h, --help            show this help message and exit
  --map-index MAP_INDEX
                        Mapped task index
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -v, --verbose         Make logging output more verbose
```

### airflow tasks list

```
Usage: airflow tasks list [-h] [-S SUBDIR] [-t] [-v] dag_id

List the tasks within a DAG

Positional Arguments:
  dag_id                The id of the dag

Optional Arguments:
  -h, --help            show this help message and exit
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -t, --tree            Tree view
  -v, --verbose         Make logging output more verbose
```

### airflow tasks render

```
Usage: airflow tasks render [-h] [--map-index MAP_INDEX] [-S SUBDIR] [-v]
                            dag_id task_id execution_date_or_run_id

Render a task instance's template(s)

Positional Arguments:
  dag_id                The id of the dag
  task_id               The id of the task
  execution_date_or_run_id
                        The execution_date of the DAG or run_id of the DAGRun

Optional Arguments:
  -h, --help            show this help message and exit
  --map-index MAP_INDEX
                        Mapped task index
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -v, --verbose         Make logging output more verbose
```

### airflow tasks run

```
Usage: airflow tasks run [-h] [--cfg-path CFG_PATH] [-d {check,ignore,wait}]
                         [-f] [-A] [-i] [-I] [-N] [-l] [--map-index MAP_INDEX]
                         [-m] [-p PICKLE] [--pool POOL] [--read-from-db]
                         [--ship-dag] [-S SUBDIR] [-v]
                         dag_id task_id execution_date_or_run_id

Run a single task instance

Positional Arguments:
  dag_id                The id of the dag
  task_id               The id of the task
  execution_date_or_run_id
                        The execution_date of the DAG or run_id of the DAGRun

Optional Arguments:
  -h, --help            show this help message and exit
  --cfg-path CFG_PATH   Path to config file to use instead of airflow.cfg
  -d, --depends-on-past {check,ignore,wait}
                        Determine how Airflow should deal with past dependencies. The default action is `check`, Airflow will check if the past dependencies are met for the tasks having `depends_on_past=True` before run them, if `ignore` is provided, the past dependencies will be ignored, if `wait` is provided and `depends_on_past=True`, Airflow will wait the past dependencies until they are met before running or skipping the task
  -f, --force           Ignore previous task instance state, rerun regardless if task already succeeded/failed
  -A, --ignore-all-dependencies
                        Ignores all non-critical dependencies, including ignore_ti_state and ignore_task_deps
  -i, --ignore-dependencies
                        Ignore task-specific dependencies, e.g. upstream, depends_on_past, and retry delay dependencies
  -I, --ignore-depends-on-past
                        Deprecated -- use `--depends-on-past ignore` instead. Ignore depends_on_past dependencies (but respect upstream dependencies)
  -N, --interactive     Do not capture standard output and error streams (useful for interactive debugging)
  -l, --local           Run the task using the LocalExecutor
  --map-index MAP_INDEX
                        Mapped task index
  -m, --mark-success    Mark jobs as succeeded without running them
  -p, --pickle PICKLE   Serialized pickle object of the entire dag (used internally)
  --pool POOL           Resource pool to use
  --read-from-db        Read dag from DB instead of dag file
  --ship-dag            Pickles (serializes) the DAG and ships it to the worker
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -v, --verbose         Make logging output more verbose
```

### airflow tasks state

```
Usage: airflow tasks state [-h] [--map-index MAP_INDEX] [-S SUBDIR] [-v]
                           dag_id task_id execution_date_or_run_id

Get the status of a task instance

Positional Arguments:
  dag_id                The id of the dag
  task_id               The id of the task
  execution_date_or_run_id
                        The execution_date of the DAG or run_id of the DAGRun

Optional Arguments:
  -h, --help            show this help message and exit
  --map-index MAP_INDEX
                        Mapped task index
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -v, --verbose         Make logging output more verbose
```

### airflow tasks states-for-dag-run

```
Usage: airflow tasks states-for-dag-run [-h] [-o table, json, yaml, plain]
                                        [-v]
                                        dag_id execution_date_or_run_id

Get the status of all task instances in a dag run

Positional Arguments:
  dag_id                The id of the dag
  execution_date_or_run_id
                        The execution_date of the DAG or run_id of the DAGRun

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

### airflow tasks test

```
Usage: airflow tasks test [-h] [-n] [--env-vars ENV_VARS]
                          [--map-index MAP_INDEX] [-m] [-S SUBDIR]
                          [-t TASK_PARAMS] [-v]
                          dag_id task_id [execution_date_or_run_id]

Test a task instance. This will run a task without checking for dependencies or recording its state in the database

Positional Arguments:
  dag_id                The id of the dag
  task_id               The id of the task
  execution_date_or_run_id
                        The execution_date of the DAG or run_id of the DAGRun (optional)

Optional Arguments:
  -h, --help            show this help message and exit
  -n, --dry-run         Perform a dry run for each task. Only renders Template Fields for each task, nothing else
  --env-vars ENV_VARS   Set env var in both parsing time and runtime for each of entry supplied in a JSON dict
  --map-index MAP_INDEX
                        Mapped task index
  -m, --post-mortem     Open debugger on uncaught exception
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -t, --task-params TASK_PARAMS
                        Sends a JSON params dict to the task
  -v, --verbose         Make logging output more verbose
```

## airflow users

```
Usage: airflow users [-h] COMMAND ...

Manage users

Positional Arguments:
  COMMAND
    add-role      Add role to a user
    create        Create a user
    delete        Delete a user
    export        Export all users
    import        Import users
    list          List users
    remove-role   Remove role from a user
    reset-password
                  Reset a user's password

Optional Arguments:
  -h, --help      show this help message and exit
```

### airflow users add

```
Usage: airflow users [-h] COMMAND ...

Manage users

Positional Arguments:
  COMMAND
    add-role      Add role to a user
    create        Create a user
    delete        Delete a user
    export        Export all users
    import        Import users
    list          List users
    remove-role   Remove role from a user
    reset-password
                  Reset a user's password

Optional Arguments:
  -h, --help      show this help message and exit

airflow users command error: argument COMMAND: invalid choice: 'add' (choose from 'add-role', 'create', 'delete', 'export', 'import', 'list', 'remove-role', 'reset-password'), see help above.
```

### airflow users create

```
Usage: airflow users create [-h] -e EMAIL -f FIRSTNAME -l LASTNAME
                            [-p PASSWORD] -r ROLE [--use-random-password] -u
                            USERNAME [-v]

Create a user

Optional Arguments:
  -h, --help            show this help message and exit
  -e, --email EMAIL     Email of the user
  -f, --firstname FIRSTNAME
                        First name of the user
  -l, --lastname LASTNAME
                        Last name of the user
  -p, --password PASSWORD
                        Password of the user, required to create a user without --use-random-password
  -r, --role ROLE       Role of the user. Existing roles include Admin, User, Op, Viewer, and Public
  --use-random-password
                        Do not prompt for password. Use random string instead. Required to create a user without --password
  -u, --username USERNAME
                        Username of the user
  -v, --verbose         Make logging output more verbose

examples:
To create an user with "Admin" role and username equals to "admin", run:

    $ airflow users create \
          --username admin \
          --firstname FIRST_NAME \
          --lastname LAST_NAME \
          --role Admin \
          --email admin@example.org
```

### airflow users delete

```
Usage: airflow users delete [-h] [-e EMAIL] [-u USERNAME] [-v]

Delete a user

Optional Arguments:
  -h, --help            show this help message and exit
  -e, --email EMAIL     Email of the user
  -u, --username USERNAME
                        Username of the user
  -v, --verbose         Make logging output more verbose
```

### airflow users export

```
Usage: airflow users export [-h] [-v] FILEPATH

Export all users

Positional Arguments:
  FILEPATH       Export all users to JSON file

Optional Arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Make logging output more verbose
```

### airflow users import

```
Usage: airflow users import [-h] [-v] FILEPATH

Import users

Positional Arguments:
  FILEPATH       Import users from JSON file. Example format::

                     [
                         {
                             "email": "foo@bar.org",
                             "firstname": "Jon",
                             "lastname": "Doe",
                             "roles": ["Public"],
                             "username": "jondoe"
                         }
                     ]

Optional Arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Make logging output more verbose
```

### airflow users list

```
Usage: airflow users list [-h] [-o table, json, yaml, plain] [-v]

List users

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

## airflow variables

```
Usage: airflow variables [-h] COMMAND ...

Manage variables

Positional Arguments:
  COMMAND
    delete    Delete variable
    export    Export all variables
    get       Get variable
    import    Import variables
    list      List variables
    set       Set variable

Optional Arguments:
  -h, --help  show this help message and exit
```

### airflow variables delete

```
Usage: airflow variables delete [-h] [-v] key

Delete variable

Positional Arguments:
  key            Variable key

Optional Arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Make logging output more verbose
```

### airflow variables export

```
Usage: airflow variables export [-h] [-v] file

All variables can be exported in STDOUT using the following command:
airflow variables export -

Positional Arguments:
  file           Export all variables to JSON file

Optional Arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Make logging output more verbose
```

### airflow variables get

```
Usage: airflow variables get [-h] [-d VAL] [-j] [-v] key

Get variable

Positional Arguments:
  key                   Variable key

Optional Arguments:
  -h, --help            show this help message and exit
  -d, --default VAL     Default value returned if variable does not exist
  -j, --json            Deserialize JSON variable
  -v, --verbose         Make logging output more verbose
```

### airflow variables import

```
Usage: airflow variables import [-h] [-a {overwrite,fail,skip}] [-v] file

Import variables

Positional Arguments:
  file                  Import variables from JSON file

Optional Arguments:
  -h, --help            show this help message and exit
  -a, --action-on-existing-key {overwrite,fail,skip}
                        Action to take if we encounter a variable key that already exists.
  -v, --verbose         Make logging output more verbose
```

### airflow variables list

```
Usage: airflow variables list [-h] [-o table, json, yaml, plain] [-v]

List variables

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

### airflow variables set

```
Usage: airflow variables set [-h] [--description DESCRIPTION] [-j] [-v]
                             key VALUE

Set variable

Positional Arguments:
  key                   Variable key
  VALUE                 Variable value

Optional Arguments:
  -h, --help            show this help message and exit
  --description DESCRIPTION
                        Variable description, optional when setting a variable
  -j, --json            Serialize JSON variable
  -v, --verbose         Make logging output more verbose
```

## airflow cheat-sheet

```
Usage: airflow cheat-sheet [-h] [-v]

Display cheat sheet

Optional Arguments:
  -h, --help     show this help message and exit
  -v, --verbose  Make logging output more verbose
```

## airflow dag-processor

```
Usage: airflow dag-processor [-h] [-D] [-p] [-l LOG_FILE] [-n NUM_RUNS]
                             [--pid [PID]] [--stderr STDERR] [--stdout STDOUT]
                             [-S SUBDIR] [-v]

Start a standalone Dag Processor instance

Optional Arguments:
  -h, --help            show this help message and exit
  -D, --daemon          Daemonize instead of running in the foreground
  -p, --do-pickle       Attempt to pickle the DAG object to send over to the workers, instead of letting workers run their version of the code
  -l, --log-file LOG_FILE
                        Location of the log file
  -n, --num-runs NUM_RUNS
                        Set the number of runs to execute before exiting
  --pid [PID]           PID file location
  --stderr STDERR       Redirect stderr to this file
  --stdout STDOUT       Redirect stdout to this file
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -v, --verbose         Make logging output more verbose
```

## airflow info

```
Usage: airflow info [-h] [--anonymize] [--file-io]
                    [-o table, json, yaml, plain] [-v]

Show information about current Airflow and environment

Optional Arguments:
  -h, --help            show this help message and exit
  --anonymize           Minimize any personal identifiable information. Use it when sharing output with others.
  --file-io             Send output to file.io service and returns link.
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

## airflow kerberos

```
Usage: airflow kerberos [-h] [-D] [-k [KEYTAB]] [-l LOG_FILE] [-o]
                        [--pid [PID]] [--stderr STDERR] [--stdout STDOUT] [-v]
                        [principal]

Start a kerberos ticket renewer

Positional Arguments:
  principal             kerberos principal

Optional Arguments:
  -h, --help            show this help message and exit
  -D, --daemon          Daemonize instead of running in the foreground
  -k, --keytab [KEYTAB]
                        keytab
  -l, --log-file LOG_FILE
                        Location of the log file
  -o, --one-time        Run airflow kerberos one time instead of forever
  --pid [PID]           PID file location
  --stderr STDERR       Redirect stderr to this file
  --stdout STDOUT       Redirect stdout to this file
  -v, --verbose         Make logging output more verbose
```

## airflow plugins

```
Usage: airflow plugins [-h] [-o table, json, yaml, plain] [-v]

Dump information about loaded plugins

Optional Arguments:
  -h, --help            show this help message and exit
  -o, --output (table, json, yaml, plain)
                        Output format. Allowed values: json, yaml, plain, table (default: table)
  -v, --verbose         Make logging output more verbose
```

## airflow rotate-fernet-key

```
Usage: airflow rotate-fernet-key [-h]

Rotate all encrypted connection credentials and variables; see https://airflow.apache.org/docs/apache-airflow/stable/howto/secure-connections.html#rotating-encryption-keys

Optional Arguments:
  -h, --help  show this help message and exit
```

## airflow scheduler

```
Usage: airflow scheduler [-h] [-D] [-p] [-l LOG_FILE] [-n NUM_RUNS]
                         [--pid [PID]] [-s] [--stderr STDERR]
                         [--stdout STDOUT] [-S SUBDIR] [-v]

Start a scheduler instance

Optional Arguments:
  -h, --help            show this help message and exit
  -D, --daemon          Daemonize instead of running in the foreground
  -p, --do-pickle       Attempt to pickle the DAG object to send over to the workers, instead of letting workers run their version of the code
  -l, --log-file LOG_FILE
                        Location of the log file
  -n, --num-runs NUM_RUNS
                        Set the number of runs to execute before exiting
  --pid [PID]           PID file location
  -s, --skip-serve-logs
                        Don't start the serve logs process along with the workers
  --stderr STDERR       Redirect stderr to this file
  --stdout STDOUT       Redirect stdout to this file
  -S, --subdir SUBDIR   File location or directory from which to look for the dag. Defaults to '[AIRFLOW_HOME]/dags' where [AIRFLOW_HOME] is the value you set for 'AIRFLOW_HOME' config you set in 'airflow.cfg'
  -v, --verbose         Make logging output more verbose

Signals:

  - SIGUSR2: Dump a snapshot of task state being tracked by the executor.

    Example:
        pkill -f -USR2 "airflow scheduler"
```

## airflow standalone

```
Usage: airflow standalone [-h]

Run an all-in-one copy of Airflow

Optional Arguments:
  -h, --help  show this help message and exit
```

## airflow sync-perm

```
Usage: airflow sync-perm [-h] [--include-dags] [-v]

Update permissions for existing roles and optionally DAGs

Optional Arguments:
  -h, --help      show this help message and exit
  --include-dags  If passed, DAG specific permissions will also be synced.
  -v, --verbose   Make logging output more verbose
```

## airflow triggerer

```
Usage: airflow triggerer [-h] [--capacity CAPACITY] [-D] [-l LOG_FILE]
                         [--pid [PID]] [-s] [--stderr STDERR]
                         [--stdout STDOUT] [-v]

Start a triggerer instance

Optional Arguments:
  -h, --help            show this help message and exit
  --capacity CAPACITY   The maximum number of triggers that a Triggerer will run at one time.
  -D, --daemon          Daemonize instead of running in the foreground
  -l, --log-file LOG_FILE
                        Location of the log file
  --pid [PID]           PID file location
  -s, --skip-serve-logs
                        Don't start the serve logs process along with the workers
  --stderr STDERR       Redirect stderr to this file
  --stdout STDOUT       Redirect stdout to this file
  -v, --verbose         Make logging output more verbose
```

## airflow version

```
Usage: airflow version [-h]

Show the version

Optional Arguments:
  -h, --help  show this help message and exit
```

## airflow webserver

```
Usage: airflow webserver [-h] [-A ACCESS_LOGFILE] [-L ACCESS_LOGFORMAT] [-D]
                         [-d] [-E ERROR_LOGFILE] [-H HOSTNAME] [-l LOG_FILE]
                         [--pid [PID]] [-p PORT] [--ssl-cert SSL_CERT]
                         [--ssl-key SSL_KEY] [--stderr STDERR]
                         [--stdout STDOUT] [-t WORKER_TIMEOUT]
                         [-k {sync,eventlet,gevent,tornado}] [-w WORKERS]

Start a Airflow webserver instance

Optional Arguments:
  -h, --help            show this help message and exit
  -A, --access-logfile ACCESS_LOGFILE
                        The logfile to store the webserver access log. Use '-' to print to stdout
  -L, --access-logformat ACCESS_LOGFORMAT
                        The access log format for gunicorn logs
  -D, --daemon          Daemonize instead of running in the foreground
  -d, --debug           Use the server that ships with Flask in debug mode
  -E, --error-logfile ERROR_LOGFILE
                        The logfile to store the webserver error log. Use '-' to print to stderr
  -H, --hostname HOSTNAME
                        Set the hostname on which to run the web server
  -l, --log-file LOG_FILE
                        Location of the log file
  --pid [PID]           PID file location
  -p, --port PORT       The port on which to run the server
  --ssl-cert SSL_CERT   Path to the SSL certificate for the webserver
  --ssl-key SSL_KEY     Path to the key to use with the SSL certificate
  --stderr STDERR       Redirect stderr to this file
  --stdout STDOUT       Redirect stdout to this file
  -t, --worker-timeout WORKER_TIMEOUT
                        The timeout for waiting on webserver workers
  -k, --workerclass {sync,eventlet,gevent,tornado}
                        The worker class to use for Gunicorn
  -w, --workers WORKERS
                        Number of workers to run the webserver on
```

