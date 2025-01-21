from flask import Flask, request, jsonify
import gradio as gr
import subprocess
import threading
import os
import signal
import requests
from pyngrok import ngrok
from dotenv import load_dotenv
# --- Colab Authentication Simulation ---
def authenticate_with_colab():
    """Simulates authentication with Google Colab."""
    try:
        return "Authenticated with Google Colab successfully."
    except Exception as e:
        return f"Failed to authenticate with Google Colab: {str(e)}"
# --- Function to Load ngrok Token ---
def load_ngrok_token():
    """Loads the ngrok authentication token, prioritizing Google Colab Secrets."""
    try:
        from google.colab import userdata
        return userdata.get('NGROK_TOKEN')
    except ImportError:
        load_dotenv()
        return os.getenv("NGROK_TOKEN")

# --- Set the ngrok Authentication Token ---
ngrok_token = load_ngrok_token()
if ngrok_token:
    ngrok.set_auth_token(ngrok_token)
else:
    raise ValueError("ngrok token not found. Please set it in .env or Google Colab Secrets.")

# --- Flask Application Initialization ---
app = Flask(__name__)

# --- Home Route ---
@app.route("/")
def home():
    """The main route, returns a simple greeting message."""
    return "Hello, World! This chatbot is running in Flask on Google Colab."

# --- Chatbot Endpoint ---
@app.route("/chatbot", methods=["POST"])
def chatbot():
    """Handles chatbot logic, providing responses based on user input."""
    try:
        user_message = request.json["message"]
        if "hello" in user_message.lower():
            response = "Hi there!"
        elif "how are you" in user_message.lower():
            response = "I'm doing well, thank you!"
        else:
            response = "I didn't understand that."
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Session Termination Endpoint ---
@app.route("/end-session", methods=["POST"])
def end_session():
    """Terminates the Colab environment session."""
    try:
        os.kill(os.getpid(), signal.SIGTERM)
        return "Session ended successfully."
    except Exception as e:
        return f"Failed to end session: {str(e)}"

# --- Server Stopping Endpoint ---
@app.route("/stop-server", methods=["POST"])
def stop_server():
    """Stops the Flask server."""
    try:
        ngrok.disconnect(ngrok.get_tunnels()[0].public_url)
        return "Server stopped successfully."
    except Exception as e:
        return f"Failed to stop server: {str(e)}"

# --- Dependency Installation Function ---
def install_dependencies():
    """Installs required dependencies in the Colab environment."""
    try:
        subprocess.check_call(["pip", "install", "flask", "pyngrok", "python-dotenv", "gradio"])
        return "Dependencies installed successfully."
    except Exception as e:
        return f"Error installing dependencies: {str(e)}"

# --- Flask Server Management ---
server_url = None
server_thread = None

# --- Flask Server Starting Function ---
def start_flask_server():
    """Starts the Flask server and exposes it via ngrok."""
    global server_url, server_thread
    try:
        if not server_url:
            def run_server():
                app.run(host="0.0.0.0", port=5000)
            server_thread = threading.Thread(target=run_server, daemon=True)
            server_thread.start()
            server_url = ngrok.connect(5000)
            return f"Server started at {server_url}"
        else:
            return f"Server is already running at {server_url}"
    except Exception as e:
        return f"Error starting server: {str(e)}"

# --- Flask Server Stopping Function ---
def stop_flask_server():
    """Stops the Flask server."""
    global server_url, server_thread
    try:
        if server_url:
            ngrok.disconnect(server_url)
            server_url = None
            if server_thread:
                requests.post("http://localhost:5000/stop-server")
                server_thread = None
            return "Server stopped successfully."
        else:
            return "Server is not running."
    except Exception as e:
        return f"Error stopping server: {str(e)}"

# --- Gradio Interface Creation Function ---
def create_gradio_interface():
    """Creates a Gradio interface for user interaction."""
    def get_server_status():
        """Fetches the current server status."""
        if server_url:
            return f"Server is running at {server_url}"
        else:
            return "Server is not running."

    with gr.Blocks() as interface:
        gr.Markdown("# Flask on Google Colab Connector")
        with gr.Tabs():
            with gr.Tab("Server Status"):
                gr.Markdown("## Manage Server")
                status_output = gr.Textbox(label="Server Status", value=get_server_status(), interactive=False)

                def toggle_server():
                    if server_url:
                        return stop_flask_server(), get_server_status()
                    else:
                        return start_flask_server(), get_server_status()

                toggle_button = gr.Button("Start" if not server_url else "End")
                toggle_button.click(fn=toggle_server, inputs=[], outputs=[status_output, status_output])

            with gr.Tab("Actions"):
                gr.Markdown("## Additional Actions")
                install_btn = gr.Button("Install Dependencies")
                colab_auth_btn = gr.Button("Authenticate with Google Colab")
                end_session_btn = gr.Button("End Session")

                install_output = gr.Textbox(label="Output", interactive=False)
                colab_auth_output = gr.Textbox(label="Output", interactive=False)
                end_session_output = gr.Textbox(label="Output", interactive=False)

                install_btn.click(fn=install_dependencies, inputs=[], outputs=install_output)
                colab_auth_btn.click(fn=authenticate_with_colab, inputs=[], outputs=colab_auth_output)

                def end_session():
                    stop_flask_server()
                    return requests.post("http://localhost:5000/end-session").text

                end_session_btn.click(fn=end_session, inputs=[], outputs=end_session_output)

    return interface

# --- Main Execution Block ---
if __name__ == "__main__":
    create_gradio_interface().launch()
