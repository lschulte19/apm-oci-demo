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

### Cenário 3.1 - Instrumentação direta no código (sem libs)

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

### Cenário 3.1b - Instrumentação direta com OpenTelemetry SDK (envio para Collector)

#### Código instrumentado com OpenTelemetry
`app_otlp.py`
```python
from flask import Flask
import time
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor

# Configuração do tracer e exportador OTLP
trace.set_tracer_provider(TracerProvider())
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
tracer = trace.get_tracer("apm-lab-instrumented")

@app.route("/tracing")
def apm_tracing():
    with tracer.start_as_current_span("service1-storefront"):
        time.sleep(2)
        with tracer.start_as_current_span("service2-catalogue"):
            time.sleep(5)
    with tracer.start_as_current_span("service3-orders"):
        with tracer.start_as_current_span("service4-payment"):
            pass
    return "OpenTelemetry traces enviados para o Collector"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
```

#### Requisitos
```text
flask
opentelemetry-sdk
opentelemetry-exporter-otlp
opentelemetry-instrumentation-flask
```

#### Dockerfile para app_otlp.py
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "app_otlp.py"]
```

#### Build e Push para OCI Registry (idêntico)
```bash
# Variáveis de ambiente iguais
# Build da imagem modificada
IMAGE_NAME=apm-lab-app-otel

docker build -t ${REGION}.ocir.io/${TENANCY_NS}/${REPO_NAME}/${IMAGE_NAME}:v1 .
docker push ${REGION}.ocir.io/${TENANCY_NS}/${REPO_NAME}/${IMAGE_NAME}:v1
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
      otlp:
        protocols:
          http:
    exporters:
      otlphttp:
        endpoint: "<oci-apm-endpoint>"
        headers:
          Authorization: "<oci-apm-key>"
    service:
      pipelines:
        traces:
          receivers: [otlp]
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