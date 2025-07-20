# Flask-Based Telegram Alert System Documentation

## Summary

This Flask application acts as a webhook receiver for Grafana alerts and sends notifications to a Telegram group based on predefined topics. The application classifies alerts and directs them to appropriate Telegram threads, handling rate limits to prevent spamming.

## Goal

Our goal with this code is to send alerts to the webhook via Grafana and then forward those alerts to Telegram from the webhook. To achieve this, we need to create contact points in Grafana and set the IP address of the virtual machine on which the webhook is located.

## Features

- Receives and processes alerts from Grafana
- Maps alert keywords to Telegram topic thread IDs
- Sends alerts to Telegram groups via a bot
- Handles rate limiting to prevent excessive messages

## Configuration

### Variables That Can Be Modified by the User

- **BOT_TOKEN**: Replace with your Telegram bot token
- **CHAT_ID**: Replace with the actual Telegram group ID
- **TOPIC_THREAD_IDS**: Modify thread IDs associated with specific alert keywords
- **DEFAULT_THREAD_ID**: Set a fallback thread ID if no keyword match is found
- **GENERAL_THREAD_ID**: Define a general thread for rate-limit alerts

## Function Descriptions

### `get_topic_for_alert(labels)`

- **Input**: Dictionary of alert labels
- **Output**: Corresponding thread ID or default ID if no match is found

### `send_telegram_message(message, thread_id=None)`

- **Input**: Alert message and optional thread ID
- **Handles**: 
  - Rate-limit errors by delaying messages
  - Preventing duplicate alerts

#### Rate Limit Considerations

Each bot on Telegram has a rate restriction of 30 messages per second, and our messages may exceed that limit. We have an alert to help identify rate limit issues:

> The message rate on Telegram has surpassed! More than 30 messages per second were found.

### `webhook()`

Processes incoming POST requests from Grafana, formats alerts, and forwards them to Telegram.

#### Checks for:
- Missing or invalid payloads
- Alert status (FIRING or RESOLVED)
- Alerts to be ignored (e.g., datasource errors)

#### Sends:
- FIRING alerts with summary text
- RESOLVED alerts with description text

**Note**: The message can be written in either firing or resolved form:
- Summary form sends a FIRING alert
- Description form sends a RESOLVED alert

## Creating Contact Points in Grafana

To send alerts from Grafana to the webhook:

1. Navigate to Grafana Settings and open Alerting
2. Click on Contact points and select New contact point
3. Choose Webhook as the notification method
4. Enter the webhook URL: `http://185.204.170.28:5000/webhook`
5. Save the contact point and associate it with your alert rules

## Running the Application

Start the Flask app with:

```bash
$ sudo systemctl enable and start cry_webhook.service
```

- Runs on 0.0.0.0:5000, allowing external connections
- Main code path: `~/cry_webhook/cry_webhook.py`

## Notes

- Ensure Flask and requests are installed
- Modify topic thread IDs in TOPIC_THREAD_IDS as needed
- Be aware of Telegram's rate limits affecting message delivery frequency

## Potential Enhancements

- Implement authentication for webhook endpoint security
- Add logging for better debugging
- Introduce a retry mechanism for failed Telegram requests

## General Explanation

### What is a Webhook?

A webhook is a lightweight, event-driven communication that automatically sends data between applications via HTTP. Triggered by specific events, webhooks automate communication between application programming interfaces (APIs) and can be used to activate workflows, such as in GitOps environments.

### Webhook Architecture

The Publish-Subscribe (Pub/Sub) architectural pattern is highly recommended for building a scalable and efficient webhook system. In this pattern, your application serves as the publisher, sending events to a central message broker that delivers these events to subscribed consumers.
