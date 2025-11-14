from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests


def create_app():
    app = Flask("llm-proxy")
    CORS(app)

    @app.route('/api/llm/chat', methods=['POST'])
    def llm_chat():
        try:
            data = request.get_json(force=True, silent=False) or {}
        except Exception:
            return jsonify({"error": "Invalid JSON body"}), 400

        prompt = (data.get('prompt') or '').strip()
        model = os.getenv("MODEL", "deepseek-r1:8b")
        if not prompt:
            return jsonify({"error": "Missing prompt"}), 400

        upstream = os.getenv("API_URL", "http://labserver.sense-campus.gr:7080/chat")
        api_key = os.getenv("API_KEY", "studentpassword")

        headers = {
            "Content-Type": "application/json",
            "X-API-Key": api_key,
            }
       

        payload = {"prompt": prompt, "model": model}

        try:
            resp = requests.post(upstream, headers=headers, json=payload, timeout=60)
        except requests.RequestException as e:
            return jsonify({"error": f"upstream network error: {e}"}), 502

        text = resp.text
        try:
            body = resp.json()
        except ValueError:
            body = {"raw": text}

        if resp.status_code >= 400:
            return jsonify({"error": body.get('error') or body.get('message') or body}), resp.status_code

        output = body.get('output') or body.get('text') or body.get('answer') or text
        return jsonify({"output": output, "model": model})

    return app


if __name__ == '__main__':
    # Configure host/port via env if desired
    host = os.getenv('LLM_BIND_HOST', '0.0.0.0')
    port = int(os.getenv('LLM_BIND_PORT', '9090'))
    create_app().run(host=host, port=port)

