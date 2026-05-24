import threading, logging, os
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

def run_api():
    from api import run_api as start; start()

def run_bot():
    from bot import build_app
    app = build_app()
    logging.info("HanoiBox bot started")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    threading.Thread(target=run_api, daemon=True).start()
    logging.info("API started")
    run_bot()
