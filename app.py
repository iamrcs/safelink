from flask import Flask, render_template, request, redirect, url_for
import base64, urllib.parse

app = Flask(__name__)

def encode_url(url):
    return base64.urlsafe_b64encode(url.encode()).decode()

def decode_url(token):
    return base64.urlsafe_b64decode(token.encode()).decode()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    original_url = request.form.get('url')
    if not original_url:
        return redirect(url_for('index'))
    encoded = encode_url(original_url)
    return redirect(url_for('page2', token=encoded))

@app.route('/step/<token>')
def page2(token):
    return render_template('page2.html', token=token)

@app.route('/final/<token>')
def final(token):
    try:
        decoded_url = decode_url(token)
        decoded_url = urllib.parse.quote(decoded_url, safe="")
        # Wrap inside Google-style safe redirect
        google_safe = f"https://www.google.com/url?q={decoded_url}&sa=D&source=hangouts"
    except Exception as e:
        return "Invalid SafeLink Token!"
    return render_template('final.html', url=google_safe)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
