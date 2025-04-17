graph TB
    ISO[ISO 8583 Sources] --> LB[HAProxy Load Balancer]
    LB --> K1[Kafka Broker 1]
    LB --> K2[Kafka Broker 2]
    LB --> K3[Kafka Broker 3]
    K1 --> F1[Flink Cluster]
    K2 --> F1
    K3 --> F1
    F1 --> P1[Prometheus]
    F1 --> ES[Elasticsearch]
    P1 --> G[Grafana]
    ES --> G
    F1 --> C[Cassandra]