# Airflow Queue Management: Key Concepts

## Understanding Airflow Queues

Queues in Airflow provide a mechanism for directing tasks to specific workers and controlling parallel execution. Here's what you need to know:

## Assigning Tasks to Queues

```python
@task(queue='high_priority')
def important_task():
    # Task logic here
```

Tasks without a specified queue go to the `default` queue automatically.

## Queue Creation and Management

- **Automatic Creation**: Queues are created automatically in RabbitMQ when first used
- **No Manual Setup**: You don't need to pre-create queues in RabbitMQ's interface
- **Monitoring**: View queue status in Flower UI (`http://server:5555`) or RabbitMQ UI (`http://server:15672`)

## Worker Configuration

Workers must be configured to listen to specific queues:

```bash
# Listen to multiple queues (comma-separated)
airflow celery worker --queues high_priority,default

# Listen to a single queue
airflow celery worker --queues data_processing
```

## SystemD Service Configuration

If using systemd, ensure your service definition includes queue configuration:

```ini
# /etc/systemd/system/airflow-celery-worker.service
ExecStart=/path/to/airflow celery worker --queues high_priority,default
```

After modification:
```bash
sudo systemctl daemon-reload
sudo systemctl restart airflow-celery-worker
```

## Queue Strategy Best Practices

1. **Task Categorization**: Group similar tasks into dedicated queues (ETL, API, reporting)
2. **Resource Allocation**: Assign resource-intensive tasks to specialized queues
3. **Priority Management**: Critical tasks can go to priority queues with dedicated workers
4. **Horizontal Scaling**: Add more workers listening to busy queues to increase throughput

## Common Pitfalls

- Tasks will remain queued if no worker is listening to their assigned queue
- Queue names (like `high_priority`) don't automatically set priority - worker configuration does
- Setting too many specialized queues can lead to idle workers and inefficient resource usage

Remember: The queue system is only as effective as your worker configuration. Always ensure workers are properly configured to listen to all active queues in your DAGs.
