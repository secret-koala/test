import datetime

def touch_streamlit_app():
    with open("streamlit_app.py", "a") as f:
        f.write(f"\n# Auto-refresh triggered at {datetime.datetime.utcnow().isoformat()} UTC\n")

if __name__ == "__main__":
    touch_streamlit_app()