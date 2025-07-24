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