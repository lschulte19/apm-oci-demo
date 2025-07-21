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