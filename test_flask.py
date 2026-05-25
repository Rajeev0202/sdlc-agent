from flask import Flask, render_template_string

app = Flask(__name__)

@app.get("/")
def index():
    return render_template_string("""
    <html>
    <body>
    <h1 style="background:lime;padding:50px;">MINIMAL TEST - Flask Works!</h1>
    <p>If you see this green box, Flask CAN serve updated content.</p>
    </body>
    </html>
    """)

if __name__ == "__main__":
    app.run(port=5001)
