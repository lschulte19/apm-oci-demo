# Estrutura do laboratório hands-on com OCI APM + Kubernetes + OpenTelemetry

## 1. Criar o APM Domain na OCI

Acesse o OCI Console > Observability & Management > Application Performance Monitoring > APM Domains > **Create APM Domain**

- Nome: `apm-hands-on`
- Compartimento: `labs`
- Retenção: 30 dias (default)
- Clique em "Create"

Copie:
- **Endpoint de ingestão** (Zipkin ou OTLP)
- **Public Data Key**

## 2. Instalar o OpenTelemetry Operator no cluster Kubernetes

```bash
kubectl apply -f https://github.com/open-telemetry/opentelemetry-operator/releases/download/v0.98.0/opentelemetry-operator.yaml
```

Crie o namespace:
```bash
kubectl create ns apm-lab
```

## 3. Criar os três cenários

### Cenário 3.1 - Instrumentação direta no código (Zipkin)

#### Código (sem OpenTelemetry)
`app.py`
```python
from flask import Flask
import time

app = Flask(__name__)

@app.route("/tracing")
def apm_tracing():
    print("[storefront] calling service1")
    time.sleep(2)

    print("[catalogue] calling service2")
    time.sleep(5)

    print("[orders] calling service3")
    print("[payment] calling service4")

    return "Traces geradas! Verifique no OCI APM."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

#### Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install flask
EXPOSE 5000
CMD ["python", "app.py"]
```

#### Build e Push para OCI Registry
```bash
export REGION=sa-saopaulo-1
export TENANCY_NS=yourtenancynamespace
export IMAGE_NAME=apm-lab-app
export REPO_NAME=apm-lab-repo

oci artifacts container repository create \
  --compartment-id <OCID> \
  --display-name $REPO_NAME \
  --is-public true

docker login ${REGION}.ocir.io \
  -u '${TENANCY_NS}/youruser' \
  -p 'your_auth_token'

docker build -t ${REGION}.ocir.io/${TENANCY_NS}/${REPO_NAME}/${IMAGE_NAME}:v1 .
docker push ${REGION}.ocir.io/${TENANCY_NS}/${REPO_NAME}/${IMAGE_NAME}:v1
```

#### Manifestos Kubernetes
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apm-lab-app
  namespace: apm-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: apm-lab-app
  template:
    metadata:
      labels:
        app: apm-lab-app
    spec:
      containers:
      - name: app
        image: <image-url-from-above>
        ports:
        - containerPort: 5000
---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: apm-lab-service
  namespace: apm-lab
spec:
  selector:
    app: apm-lab-app
  ports:
    - protocol: TCP
      port: 80
      targetPort: 5000
```

### Cenário 3.2 - Sem libs, usando sidecar do OpenTelemetry Collector

#### Manifesto com sidecar collector (apm-sidecar.yaml)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apm-sidecar
  namespace: apm-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: apm-sidecar
  template:
    metadata:
      labels:
        app: apm-sidecar
    spec:
      containers:
      - name: app
        image: <same-image-as-before>
        ports:
        - containerPort: 5000
      - name: otel-sidecar
        image: otel/opentelemetry-collector:latest
        args: ["--config=/etc/otel/config.yaml"]
        volumeMounts:
        - name: config-volume
          mountPath: /etc/otel
      volumes:
      - name: config-volume
        configMap:
          name: otel-config
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-config
  namespace: apm-lab
  labels:
    app: apm-sidecar
  annotations:
    managed-by: user

data:
  config.yaml: |
    receivers:
      zipkin:
    exporters:
      otlphttp:
        endpoint: "<oci-apm-endpoint>"
        headers:
          Authorization: "<oci-apm-key>"
    service:
      pipelines:
        traces:
          receivers: [zipkin]
          exporters: [otlphttp]
```

### Cenário 3.3 - OpenTelemetry Operator com sidecar Collector por Pod

#### Instrumentação automática via OpenTelemetry Operator
```yaml
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: python-instrumentation
  namespace: apm-lab
spec:
  exporter:
    endpoint: "<oci-apm-endpoint>"
  propagators:
    - tracecontext
    - baggage
  sampler:
    type: parentbased_always_on
  python:
    image: ghcr.io/open-telemetry/opentelemetry-operator/autoinstrumentation-python:latest
```

#### Deployment com annotations para injeção automática
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auto-instrumented
  namespace: apm-lab
spec:
  replicas: 1
  selector:
    matchLabels:
      app: auto-instrumented
  template:
    metadata:
      annotations:
        instrumentation.opentelemetry.io/inject-python: "python-instrumentation"
      labels:
        app: auto-instrumented
    spec:
      containers:
      - name: app
        image: <image-url-from-above>
        ports:
        - containerPort: 5000
```

## 4. Testes e Validação na Console

- Acesse o endpoint do serviço exposto:
```bash
kubectl port-forward svc/apm-lab-service 8080:80 -n apm-lab
curl http://localhost:8080/tracing
```
- Vá até OCI Console > APM > Trace Explorer
  - Filtro por Service Name ou span
  - Observe a timeline com serviços encadeados

## 5. Referências
- [OCI APM Docs](https://docs.oracle.com/en-us/iaas/application-performance-monitoring/index.html)
- [OpenTelemetry Operator](https://opentelemetry.io/docs/kubernetes/operator/)
- [py-zipkin GitHub](https://github.com/openzipkin/py_zipkin)
